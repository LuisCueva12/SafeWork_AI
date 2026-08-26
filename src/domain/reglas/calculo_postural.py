from __future__ import annotations
import math
import time
from ..entities.postura import EstadoAlerta, EstadoFisico, LecturaHibrida, NivelRiesgo
from ..entities.trabajador import SesionTrabajador, UMBRAL_OJOS_CERRADOS_SEGUNDOS, UMBRAL_CABECEO_SEGUNDOS, MAX_BOSTEZOS_PERMITIDOS
from .normalizacion_yolo import es_clase_bostezo, es_clase_fatiga, es_clase_sueno_o_bostezo, normalizar_clase_yolo

UMBRAL_EAR_CERRADO = 0.18
UMBRAL_MAR_BOSTEZO = 0.38
UMBRAL_INCLINACION_LATERAL = 15.0
UMBRAL_POSTURA_SOSTENIDA_SEGUNDOS = 2.5
UMBRAL_CERCANIA_MONITOR = 0.72
RIESGO_OBSERVACION_SEGUNDOS = 3.0
RIESGO_LEVE_SEGUNDOS = 10.0
RIESGO_CRITICO_SEGUNDOS = 20.0
CALIDAD_MINIMA_LECTURA = 55.0
RACHA_CERCANIA_CONFIRMADA = 6
RACHA_POSTURA_CONFIRMADA = 22
UMBRAL_CABECEO_TIEMPO_SEGUNDOS = 2.5

# Cada señal reacciona distinto: ojos/boca necesitan respuesta rápida (la
# protección anti-parpadeo real es la duración sostenida, no el suavizado),
# mientras que cuello/lateral/proximidad son más ruidosas por jitter de
# landmarks y se benefician de más suavizado para evitar falsos positivos.
EMA_ALPHA_OJOS = 0.65
EMA_ALPHA_BOCA = 0.65
EMA_ALPHA_CUELLO = 0.45
EMA_ALPHA_LATERAL = 0.45
EMA_ALPHA_PROXIMIDAD = 0.45

# Histéresis de doble umbral: una vez dentro del estado de riesgo, hace falta
# bajar por debajo de (umbral_entrada * RATIO_HISTERESIS_SALIDA) para salir,
# evitando parpadeo de estados cuando el valor ronda el umbral de entrada.
RATIO_HISTERESIS_SALIDA = 0.80


def _existe_oclusion_consciente(
    lectura: LecturaHibrida,
    clase: str,
    ear_filtrado: float,
    umbral_ear: float,
    indice_fatiga: float,
) -> bool:
    return (
        lectura.mano_sobre_rostro
        and clase == "normal"
        and ear_filtrado >= umbral_ear * 1.10
        and not lectura.mirando_abajo
        and indice_fatiga < 0.85
    )


def _mirada_abajo_neutra(lectura: LecturaHibrida, clase: str, indice_fatiga: float) -> bool:
    return (
        lectura.mirando_abajo
        and clase == "normal"
        and lectura.yolo_confianza < 0.75
        and indice_fatiga < 1.10
    )

def _nivel_por_duracion(duracion: float) -> NivelRiesgo:
    if duracion >= RIESGO_CRITICO_SEGUNDOS:
        return NivelRiesgo.RIESGO_CRITICO
    if duracion >= RIESGO_LEVE_SEGUNDOS:
        return NivelRiesgo.RIESGO_LEVE
    return NivelRiesgo.OBSERVACION

def _limitar(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return min(maximo, max(minimo, valor))

def _actualizar_estado_histeresis(
    valor: float,
    umbral_entrada: float,
    en_riesgo_previo: bool,
    ratio_salida: float = RATIO_HISTERESIS_SALIDA,
) -> bool:
    if en_riesgo_previo:
        return valor >= umbral_entrada * ratio_salida
    return valor >= umbral_entrada

def _punto_en_borde_o_fuera(punto, margen: float = 0.035) -> bool:
    if not punto.es_confiable():
        return False
    return punto.x <= margen or punto.x >= 1.0 - margen or punto.y <= margen or punto.y >= 1.0 - margen

def evaluar_calidad_lectura(lectura: LecturaHibrida) -> tuple[float, list[str]]:
    calidad = 100.0
    evidencias = []

    if not lectura.rostro_detectado:
        calidad -= 55.0
        evidencias.append("rostro_no_visible")
    if not lectura.cuerpo_detectado:
        calidad -= 30.0
        evidencias.append("hombros_no_visibles")

    if lectura.rostro_detectado:
        if lectura.ear <= 0:
            calidad -= 18.0
            evidencias.append("ojos_no_medibles")
        if lectura.mar <= 0:
            calidad -= 12.0
            evidencias.append("boca_no_medible")
        if 0 < lectura.ancho_cara < 0.06:
            calidad -= 15.0
            evidencias.append("rostro_muy_lejano")

    if lectura.cuerpo_detectado:
        puntos_corporales = (
            ("nariz_pose_no_confiable", lectura.nariz),
            ("hombro_izquierdo_no_confiable", lectura.hombro_izquierdo),
            ("hombro_derecho_no_confiable", lectura.hombro_derecho),
        )
        for evidencia, punto in puntos_corporales:
            if not punto.es_confiable():
                calidad -= 12.0
                evidencias.append(evidencia)

        if any(
            _punto_en_borde_o_fuera(punto)
            for punto in (lectura.nariz, lectura.hombro_izquierdo, lectura.hombro_derecho)
        ):
            calidad -= 50.0
            evidencias.append("encuadre_incompleto")

    if lectura.mano_sobre_rostro:
        calidad -= 18.0
        evidencias.append("rostro_parcialmente_ocluido")

    return _limitar(calidad), evidencias

def _construir_puntajes(
    calidad: float,
    proximidad_monitor: float,
    angulo_cuello: float,
    angulo_lateral: float,
    indice_fatiga: float,
    segundos_ojos_cerrados: float,
    yolo_confianza: float,
    clase: str,
    umbral_cercania: float,
    umbral_lateral: float,
    umbral_ear_segundos: float,
) -> dict[str, int]:
    puntaje_cercania = _limitar((proximidad_monitor / max(0.01, umbral_cercania)) * 100.0)
    puntaje_postura = max(
        _limitar((angulo_cuello / 28.0) * 100.0),
        _limitar((angulo_lateral / max(0.1, umbral_lateral * 2.0)) * 100.0),
    )
    puntaje_fatiga = max(
        _limitar((indice_fatiga / 1.65) * 100.0),
        _limitar((segundos_ojos_cerrados / max(0.1, umbral_ear_segundos)) * 100.0),
        _limitar(yolo_confianza * 100.0) if es_clase_sueno_o_bostezo(clase) else 0.0,
    )
    return {
        "calidad": int(round(calidad)),
        "cercania": int(round(puntaje_cercania)),
        "postura": int(round(puntaje_postura)),
        "fatiga": int(round(puntaje_fatiga)),
    }

def _accion_recomendada(estado: EstadoAlerta) -> str:
    acciones = {
        EstadoAlerta.OPTIMO: "Continua trabajando con pausas preventivas.",
        EstadoAlerta.LECTURA_INESTABLE: "Ajusta tu posicion frente a la camara y mejora la iluminacion.",
        EstadoAlerta.CERCANIA_MONITOR: "Alejate un poco del monitor y manten el cuello recto.",
        EstadoAlerta.MALA_POSTURA: "Alinea espalda, cuello y hombros durante unos segundos.",
        EstadoAlerta.CABECEO: "Detente y realiza una pausa de recuperacion visual y respiratoria.",
        EstadoAlerta.FATIGA_EXTREMA: "Toma una pausa inmediata y evita continuar con somnolencia.",
        EstadoAlerta.ADVERTENCIA_SUENO: "Realiza una pausa activa breve para recuperar enfoque.",
        EstadoAlerta.AUSENTE: "Ubicate nuevamente frente a la camara.",
        EstadoAlerta.CALIBRANDO: "Mantente en una postura natural durante la calibracion.",
    }
    return acciones.get(estado, "")

def calcular_angulo_horizontal(p1, p2) -> float:
    return math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))

def es_curva_bostezo_gaussiana(historial: list[float], umbral_bostezo: float) -> bool:
    if len(historial) < 12:
        return False
    max_mar = max(historial)
    if max_mar < umbral_bostezo:
        return False
    diffs = [historial[i] - historial[i-1] for i in range(1, len(historial))]
    diffs_suaves = []
    for i in range(len(diffs)):
        inicio = max(0, i - 1)
        fin = min(len(diffs), i + 2)
        diffs_suaves.append(sum(diffs[inicio:fin]) / (fin - inicio))
    cambios_signo = 0
    estado_actual = None
    for d in diffs_suaves:
        if d > 0.01:
            nuevo_estado = True
        elif d < -0.01:
            nuevo_estado = False
        else:
            continue
        if estado_actual is not None and nuevo_estado != estado_actual:
            cambios_signo += 1
        estado_actual = nuevo_estado
    return cambios_signo <= 2

def calcular_ratio_postural(lectura: LecturaHibrida) -> tuple[float, float]:
    if not (lectura.nariz.es_confiable() and lectura.hombro_izquierdo.es_confiable() and lectura.hombro_derecho.es_confiable()):
        return 0.0, 0.0
    dx = lectura.hombro_derecho.x - lectura.hombro_izquierdo.x
    dy = lectura.hombro_derecho.y - lectura.hombro_izquierdo.y
    ancho_hombros = math.sqrt(dx**2 + dy**2)
    if ancho_hombros <= 0:
        return 0.0, 0.0
    hombro_medio_y = (lectura.hombro_izquierdo.y + lectura.hombro_derecho.y) / 2.0
    ratio_y = (hombro_medio_y - lectura.nariz.y) / ancho_hombros
    return ancho_hombros, ratio_y

def calcular_postura(lectura: LecturaHibrida, sesion: SesionTrabajador) -> tuple[float, float]:
    if not lectura.cuerpo_detectado:
        return 0.0, 0.0
    cuello = 0.0
    lateral = 0.0
    ancho_hombros, ratio_y = calcular_ratio_postural(lectura)
    if ancho_hombros > 0 and sesion.base_ratio_y > 0:
        diferencia_ratio = sesion.base_ratio_y - ratio_y
        if diferencia_ratio > 0.04:
            cuello = (diferencia_ratio - 0.04) * 350.0
    if lectura.oreja_izquierda.es_confiable() and lectura.oreja_derecha.es_confiable() and lectura.hombro_izquierdo.es_confiable() and lectura.hombro_derecho.es_confiable():
        angulo_hombros = calcular_angulo_horizontal(lectura.hombro_izquierdo, lectura.hombro_derecho)
        angulo_orejas = calcular_angulo_horizontal(lectura.oreja_izquierda, lectura.oreja_derecha)
        lateral = abs(angulo_orejas - angulo_hombros)
        if lateral > 90:
            lateral = 180 - lateral
    return cuello, lateral

def calcular_proximidad_monitor(lectura: LecturaHibrida, sesion: SesionTrabajador) -> float:
    if not lectura.rostro_detectado or not lectura.cuerpo_detectado:
        return 0.0
    if not (
        lectura.nariz.es_confiable()
        and lectura.hombro_izquierdo.es_confiable()
        and lectura.hombro_derecho.es_confiable()
    ):
        return 0.0

    puntaje = 0.0

    if sesion.base_z_nariz_rel != 0.0:
        z_hombro_medio = (lectura.hombro_izquierdo.z + lectura.hombro_derecho.z) / 2.0
        z_rel = lectura.nariz.z - z_hombro_medio
        delta_z = sesion.base_z_nariz_rel - z_rel
        if delta_z > 0.02:
            puntaje += min(0.55, max(0.0, (delta_z - 0.02) * 4.4))

    if sesion.base_ancho_cara > 0 and lectura.ancho_cara > 0:
        ratio_cercania = lectura.ancho_cara / sesion.base_ancho_cara
        if ratio_cercania > 1.04:
            puntaje += min(0.55, max(0.0, (ratio_cercania - 1.04) * 2.7))

    return min(1.5, puntaje)

def analizar_lectura_hibrida(lectura: LecturaHibrida, sesion: SesionTrabajador) -> EstadoFisico:
    if not lectura.rostro_detectado and not lectura.cuerpo_detectado:
        return EstadoFisico(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            EstadoAlerta.AUSENTE,
            calidad_deteccion=0.0,
            puntajes_riesgo={"calidad": 0, "cercania": 0, "postura": 0, "fatiga": 0},
            evidencias=("rostro_no_visible", "cuerpo_no_visible"),
            accion_recomendada=_accion_recomendada(EstadoAlerta.AUSENTE),
        )

    calidad_deteccion, evidencias = evaluar_calidad_lectura(lectura)

    if not lectura.rostro_detectado:
        return EstadoFisico(
            lectura.ear,
            lectura.mar,
            0.0,
            0.0,
            0.0,
            EstadoAlerta.LECTURA_INESTABLE,
            calidad_deteccion=calidad_deteccion,
            puntajes_riesgo={"calidad": int(round(calidad_deteccion)), "cercania": 0, "postura": 0, "fatiga": 0},
            evidencias=tuple(evidencias + ["rostro_requerido_para_fatiga"]),
            accion_recomendada=_accion_recomendada(EstadoAlerta.LECTURA_INESTABLE),
        )

    if calidad_deteccion < CALIDAD_MINIMA_LECTURA:
        return EstadoFisico(
            lectura.ear,
            lectura.mar,
            0.0,
            0.0,
            0.0,
            EstadoAlerta.LECTURA_INESTABLE,
            calidad_deteccion=calidad_deteccion,
            puntajes_riesgo={"calidad": int(round(calidad_deteccion)), "cercania": 0, "postura": 0, "fatiga": 0},
            evidencias=tuple(evidencias),
            accion_recomendada=_accion_recomendada(EstadoAlerta.LECTURA_INESTABLE),
        )

    clase_original = normalizar_clase_yolo(lectura.yolo_clase)
    clase = clase_original
    observacion_yolo_baja_confianza = (
        es_clase_sueno_o_bostezo(clase_original)
        and lectura.yolo_confianza < 0.85
        and lectura.fusion_nivel != NivelRiesgo.RIESGO_CONFIRMADO
    )
    if observacion_yolo_baja_confianza:
        clase = "normal"
    
    if lectura.rostro_detectado and lectura.ear > 0:
        if sesion.ultimo_ear_filtrado == 0.0:
            sesion.ultimo_ear_filtrado = lectura.ear
        else:
            sesion.ultimo_ear_filtrado = EMA_ALPHA_OJOS * lectura.ear + (1.0 - EMA_ALPHA_OJOS) * sesion.ultimo_ear_filtrado

    if lectura.rostro_detectado and lectura.mar > 0:
        if sesion.ultimo_mar_filtrado == 0.0:
            sesion.ultimo_mar_filtrado = lectura.mar
        else:
            sesion.ultimo_mar_filtrado = EMA_ALPHA_BOCA * lectura.mar + (1.0 - EMA_ALPHA_BOCA) * sesion.ultimo_mar_filtrado
        sesion.registrar_mar_lectura(sesion.ultimo_mar_filtrado)

    factor_sensibilidad = sesion.factor_sensibilidad()
    umbral_ear = sesion.base_ear * (0.72 / factor_sensibilidad) if sesion.base_ear > 0 else UMBRAL_EAR_CERRADO / factor_sensibilidad
    umbral_mar_base = sesion.base_mar * (1.78 * factor_sensibilidad) if sesion.base_mar > 0 else UMBRAL_MAR_BOSTEZO * factor_sensibilidad
    umbral_mar = min(0.52, max(0.34, umbral_mar_base))
    umbral_lateral = UMBRAL_INCLINACION_LATERAL * factor_sensibilidad
    umbral_cercania = UMBRAL_CERCANIA_MONITOR * factor_sensibilidad
    umbral_cuello_postura = 14.0 * factor_sensibilidad
    umbral_cuello_cabeceo = 28.0 * factor_sensibilidad

    if es_clase_bostezo(clase):
        evidencias.append("yolo_bostezo")
        sesion.racha_yolo_bostezo += 1
        sesion.racha_yolo_sueno = 0
        sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.12)
        if lectura.fusion_nivel == NivelRiesgo.RIESGO_CONFIRMADO or (
            sesion.racha_yolo_bostezo >= 2 and sesion.ultimo_mar_filtrado >= umbral_mar * 0.86
        ):
            if sesion.confirmar_bostezo():
                evidencias.append("bostezo_yolo_confirmado")
    elif es_clase_fatiga(clase):
        evidencias.append("yolo_fatiga")
        sesion.racha_yolo_sueno += 1
        sesion.racha_yolo_bostezo = 0
        sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.22)
        sesion.registrar_ojos_cerrados()
    else:
        sesion.racha_yolo_sueno = max(0, sesion.racha_yolo_sueno - 1)
        sesion.racha_yolo_bostezo = max(0, sesion.racha_yolo_bostezo - 1)
        if lectura.rostro_detectado:
            if lectura.mirando_abajo:
                sesion.registrar_ojos_abiertos()
                sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.03)
            else:
                if sesion.ultimo_ear_filtrado <= umbral_ear:
                    sesion.registrar_ojos_cerrados()
                    sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.10)
                else:
                    sesion.registrar_ojos_abiertos()
                    sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.07)
                    
            if lectura.mano_sobre_rostro:
                evidencias.append("mano_sobre_rostro")
                sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.03)

    if lectura.rostro_detectado:
        if lectura.mano_sobre_rostro:
            sesion.inicio_bostezo_actual = None
            sesion.bostezo_actual_activo = False
            sesion.racha_boca_abierta = 0
            sesion.finalizar_bostezo()
        elif sesion.ultimo_mar_filtrado >= umbral_mar:
            ojos_bien_abiertos = sesion.ultimo_ear_filtrado > (umbral_ear * 1.25)
            
            if ojos_bien_abiertos:
                sesion.racha_boca_abierta = max(0, sesion.racha_boca_abierta - 1)
                if sesion.bostezo_actual_activo:
                    sesion.inicio_bostezo_actual = None
                    sesion.bostezo_actual_activo = False
                    sesion.finalizar_bostezo()
            else:
                evidencias.append("apertura_boca_elevada")
                sesion.racha_boca_abierta = min(120, sesion.racha_boca_abierta + 1)
                if sesion.inicio_bostezo_actual is None:
                    sesion.inicio_bostezo_actual = time.time()
                    sesion.bostezo_actual_activo = True
                sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.06)
                if sesion.racha_boca_abierta >= 30:
                    if sesion.confirmar_bostezo():
                        evidencias.append("bostezo_por_apertura_sostenida")
        else:
            sesion.racha_boca_abierta = max(0, sesion.racha_boca_abierta - 2)
            if sesion.bostezo_actual_activo and sesion.inicio_bostezo_actual is not None:
                duracion = time.time() - sesion.inicio_bostezo_actual
                cierre_boca = sesion.ultimo_mar_filtrado < max(0.22, umbral_mar * 0.68)
                if cierre_boca:
                    min_duracion = max(0.55, sesion.promedio_duracion_bostezo * 0.35)
                    patron_curvo = es_curva_bostezo_gaussiana(sesion.historial_mar[-18:], umbral_mar * 0.85)
                    if min_duracion <= duracion <= 6.5 and (patron_curvo or duracion >= 0.85):
                        sesion.promedio_duracion_bostezo = 0.85 * sesion.promedio_duracion_bostezo + 0.15 * duracion
                        if sesion.confirmar_bostezo():
                            evidencias.append("bostezo_por_cierre_natural")
                    sesion.inicio_bostezo_actual = None
                    sesion.bostezo_actual_activo = False
                    sesion.finalizar_bostezo()
                elif duracion > 6.5:
                    sesion.inicio_bostezo_actual = None
                    sesion.bostezo_actual_activo = False
                    sesion.finalizar_bostezo()
            else:
                sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.03)

    angulo_cuello_raw, angulo_lateral_raw = calcular_postura(lectura, sesion)
    proximidad_monitor_raw = calcular_proximidad_monitor(lectura, sesion)

    if lectura.cuerpo_detectado and angulo_cuello_raw > 0:
        if sesion.ultimo_cuello_filtrado == 0.0:
            sesion.ultimo_cuello_filtrado = angulo_cuello_raw
        else:
            sesion.ultimo_cuello_filtrado = EMA_ALPHA_CUELLO * angulo_cuello_raw + (1.0 - EMA_ALPHA_CUELLO) * sesion.ultimo_cuello_filtrado

    if lectura.cuerpo_detectado and angulo_lateral_raw > 0:
        if sesion.ultimo_lateral_filtrado == 0.0:
            sesion.ultimo_lateral_filtrado = angulo_lateral_raw
        else:
            sesion.ultimo_lateral_filtrado = EMA_ALPHA_LATERAL * angulo_lateral_raw + (1.0 - EMA_ALPHA_LATERAL) * sesion.ultimo_lateral_filtrado

    if lectura.cuerpo_detectado and lectura.rostro_detectado:
        if sesion.ultimo_proximidad_filtrada == 0.0:
            sesion.ultimo_proximidad_filtrada = proximidad_monitor_raw
        else:
            sesion.ultimo_proximidad_filtrada = (
                EMA_ALPHA_PROXIMIDAD * proximidad_monitor_raw + (1.0 - EMA_ALPHA_PROXIMIDAD) * sesion.ultimo_proximidad_filtrada
            )

    angulo_cuello = sesion.ultimo_cuello_filtrado
    angulo_lateral = sesion.ultimo_lateral_filtrado
    proximidad_monitor = sesion.ultimo_proximidad_filtrada

    oclusion_consciente = _existe_oclusion_consciente(
        lectura,
        clase,
        sesion.ultimo_ear_filtrado,
        umbral_ear,
        sesion.indice_fatiga,
    )
    mirada_abajo_neutra = _mirada_abajo_neutra(lectura, clase, sesion.indice_fatiga)
    if oclusion_consciente:
        angulo_cuello = min(12.0, angulo_cuello * 0.22)
        angulo_lateral = angulo_lateral * 0.45
        proximidad_monitor = proximidad_monitor * 0.55
    elif mirada_abajo_neutra:
        angulo_cuello = angulo_cuello * 0.40

    sesion.en_riesgo_cabeceo = _actualizar_estado_histeresis(
        angulo_cuello, umbral_cuello_cabeceo, sesion.en_riesgo_cabeceo
    )
    sesion.en_riesgo_postura_cuello = _actualizar_estado_histeresis(
        angulo_cuello, umbral_cuello_postura, sesion.en_riesgo_postura_cuello
    )
    sesion.en_riesgo_lateral = _actualizar_estado_histeresis(
        angulo_lateral, umbral_lateral, sesion.en_riesgo_lateral
    )
    sesion.en_riesgo_cercania = _actualizar_estado_histeresis(
        proximidad_monitor, umbral_cercania, sesion.en_riesgo_cercania
    )

    evidencia_fatiga_ocular = (
        es_clase_fatiga(clase)
        or sesion.racha_yolo_sueno >= 2
        or sesion.indice_fatiga >= 0.95
        or (not lectura.mirando_abajo and sesion.ultimo_ear_filtrado <= umbral_ear * 1.03)
    )
    mirada_abajo_con_fatiga = lectura.mirando_abajo and (
        sesion.indice_fatiga >= 1.20
        or sesion.racha_yolo_sueno >= 2
        or sesion.segundos_ojos_cerrados() >= 0.8
    )
    evidencia_somnolencia = evidencia_fatiga_ocular or mirada_abajo_con_fatiga
    calidad_cabeceo_suficiente = (
        calidad_deteccion >= 72.0
        and lectura.rostro_detectado
        and lectura.cuerpo_detectado
        and lectura.nariz.es_confiable()
        and lectura.hombro_izquierdo.es_confiable()
        and lectura.hombro_derecho.es_confiable()
    )
    somnolencia_cabeceo_confirmada = (
        (es_clase_fatiga(clase) and lectura.fusion_nivel == NivelRiesgo.RIESGO_CONFIRMADO)
        or sesion.racha_yolo_sueno >= 3
        or sesion.indice_fatiga >= 1.45
        or sesion.segundos_ojos_cerrados() >= 1.15
        or sesion.racha_ojos_cerrados >= 4
    )
    evidencia_cabeceo = calidad_cabeceo_suficiente and somnolencia_cabeceo_confirmada
    if lectura.mirando_abajo and not evidencia_cabeceo:
        evidencias.append("mirada_abajo_sin_somnolencia_confirmada")

    permite_cabeceo = (
        calidad_cabeceo_suficiente
        and (
            not lectura.mirando_abajo
            or (es_clase_fatiga(clase) and lectura.fusion_nivel == NivelRiesgo.RIESGO_CONFIRMADO)
            or sesion.racha_yolo_sueno >= 3
            or sesion.indice_fatiga >= 1.55
            or sesion.segundos_ojos_cerrados() >= 1.50
        )
    )

    cabeceo_confirmado = (
        sesion.en_riesgo_cabeceo
        and evidencia_cabeceo
        and permite_cabeceo
        and not oclusion_consciente
    )
    if cabeceo_confirmado:
        evidencias.append("cabeza_inclinada_con_somnolencia")
        sesion.racha_cabeceo_riesgo += 1
        sesion.registrar_cabeceo_iniciado()
    else:
        sesion.racha_cabeceo_riesgo = max(0, sesion.racha_cabeceo_riesgo - 2)
        sesion.registrar_cabeza_erguida()
        if sesion.en_riesgo_cabeceo and not calidad_cabeceo_suficiente:
            evidencias.append("lectura_no_apta_para_cabeceo")

    cercania_dominante = (
        sesion.en_riesgo_cercania
        and angulo_lateral < umbral_lateral * 1.35
        and not oclusion_consciente
    )
    # Una inclinacion fuerte SIN evidencia de somnolencia (ojos abiertos, sin
    # senal YOLO) debe seguir contando como mala postura, no quedar en un
    # limbo esperando una confirmacion de cabeceo que nunca llega.
    mala_postura = (
        not cercania_dominante
        and ((sesion.en_riesgo_postura_cuello and not cabeceo_confirmado) or sesion.en_riesgo_lateral)
    )
    if mala_postura:
        if sesion.en_riesgo_postura_cuello:
            evidencias.append("cuello_inclinado")
        if sesion.en_riesgo_lateral:
            evidencias.append("inclinacion_lateral")
        sesion.racha_postura_riesgo += 1
        sesion.registrar_mala_postura()
    else:
        sesion.racha_postura_riesgo = max(0, sesion.racha_postura_riesgo - 2)
        sesion.registrar_buena_postura()

    riesgo_cercania = (
        cercania_dominante
        and not (evidencia_somnolencia and angulo_cuello >= umbral_cuello_cabeceo)
    )
    if riesgo_cercania:
        evidencias.append("cercania_monitor")
        if lectura.ancho_cara > sesion.base_ancho_cara > 0:
            evidencias.append("rostro_mas_grande")
        if sesion.base_z_nariz_rel != 0.0:
            evidencias.append("nariz_z_cercana")
        sesion.racha_cercania_monitor += 1
        sesion.registrar_cercania_monitor()
    else:
        sesion.racha_cercania_monitor = max(0, sesion.racha_cercania_monitor - 1)
        sesion.registrar_distancia_correcta()

    if not riesgo_cercania and not mala_postura and not evidencia_somnolencia:
        sesion.racha_estable = min(240, sesion.racha_estable + 1)
    else:
        sesion.racha_estable = max(0, sesion.racha_estable - 2)
        
    estado = EstadoAlerta.OPTIMO
    duracion_riesgo = 0.0
    fatiga_por_cierre_ocular_real = (
        sesion.segundos_ojos_cerrados() >= UMBRAL_OJOS_CERRADOS_SEGUNDOS
        or sesion.indice_fatiga >= 1.65
    )
    cabeceo_por_tiempo_sostenido = sesion.segundos_cabeceo() >= UMBRAL_CABECEO_TIEMPO_SEGUNDOS
    if fatiga_por_cierre_ocular_real:
        estado = EstadoAlerta.FATIGA_EXTREMA
        duracion_riesgo = max(sesion.segundos_ojos_cerrados(), UMBRAL_OJOS_CERRADOS_SEGUNDOS)
    elif cabeceo_por_tiempo_sostenido:
        estado = EstadoAlerta.CABECEO
        duracion_riesgo = sesion.segundos_cabeceo()
    elif sesion.racha_yolo_sueno >= 3:
        estado = EstadoAlerta.FATIGA_EXTREMA
        duracion_riesgo = max(sesion.segundos_ojos_cerrados(), UMBRAL_OJOS_CERRADOS_SEGUNDOS)
    elif (
        sesion.segundos_cercania_monitor() >= RIESGO_OBSERVACION_SEGUNDOS
        or sesion.racha_cercania_monitor >= RACHA_CERCANIA_CONFIRMADA
    ):
        estado = EstadoAlerta.CERCANIA_MONITOR
        duracion_riesgo = sesion.segundos_cercania_monitor()
    elif (
        sesion.segundos_mala_postura() >= 4.5
        or sesion.racha_postura_riesgo >= RACHA_POSTURA_CONFIRMADA
    ):
        estado = EstadoAlerta.MALA_POSTURA
        duracion_riesgo = sesion.segundos_mala_postura()
    elif sesion.cantidad_bostezos_recientes() >= MAX_BOSTEZOS_PERMITIDOS or sesion.indice_fatiga >= 0.85:
        estado = EstadoAlerta.ADVERTENCIA_SUENO
        duracion_riesgo = RIESGO_OBSERVACION_SEGUNDOS

    nivel_riesgo = _nivel_por_duracion(duracion_riesgo)

    if estado in {EstadoAlerta.FATIGA_EXTREMA, EstadoAlerta.CABECEO}:
        nivel_riesgo = max(nivel_riesgo, NivelRiesgo.RIESGO_CONFIRMADO, key=lambda nivel: list(NivelRiesgo).index(nivel))

    if lectura.fusion_nivel == NivelRiesgo.RIESGO_CONFIRMADO:
        if estado == EstadoAlerta.OPTIMO:
            estado = EstadoAlerta.ADVERTENCIA_SUENO
        nivel_riesgo = NivelRiesgo.RIESGO_CONFIRMADO
        duracion_riesgo = max(duracion_riesgo, RIESGO_OBSERVACION_SEGUNDOS)
        evidencias.append("yolo_mediapipe_confirmado")
    elif observacion_yolo_baja_confianza and estado == EstadoAlerta.OPTIMO:
        estado = EstadoAlerta.ADVERTENCIA_SUENO
        nivel_riesgo = NivelRiesgo.OBSERVACION
        duracion_riesgo = 0.0
        evidencias.append("yolo_baja_confianza")

    estado_raw = estado
    estado, estado_retenido_por_histeresis = sesion.aplicar_histeresis_estado(estado, salida_segundos=0.5)
    if estado_retenido_por_histeresis and estado_raw == EstadoAlerta.OPTIMO:
        nivel_riesgo = NivelRiesgo.OBSERVACION
        duracion_riesgo = 0.0
        evidencias.append("histeresis_salida")

    puntajes_riesgo = _construir_puntajes(
        calidad_deteccion,
        proximidad_monitor,
        angulo_cuello,
        angulo_lateral,
        sesion.indice_fatiga,
        sesion.segundos_ojos_cerrados(),
        lectura.yolo_confianza,
        clase_original,
        umbral_cercania,
        umbral_lateral,
        UMBRAL_OJOS_CERRADOS_SEGUNDOS,
    )
        
    return EstadoFisico(
        sesion.ultimo_ear_filtrado,
        sesion.ultimo_mar_filtrado,
        angulo_cuello,
        angulo_lateral,
        proximidad_monitor,
        estado,
        nivel_riesgo,
        duracion_riesgo,
        calidad_deteccion,
        puntajes_riesgo,
        tuple(dict.fromkeys(evidencias)),
        _accion_recomendada(estado),
    )
