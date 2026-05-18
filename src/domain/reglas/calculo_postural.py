from __future__ import annotations
import math
import time
from ..entities.postura import EstadoAlerta, EstadoFisico, LecturaHibrida
from ..entities.trabajador import SesionTrabajador, UMBRAL_OJOS_CERRADOS_SEGUNDOS, UMBRAL_CABECEO_SEGUNDOS, MAX_BOSTEZOS_PERMITIDOS

UMBRAL_EAR_CERRADO = 0.18
UMBRAL_MAR_BOSTEZO = 0.38
UMBRAL_INCLINACION_LATERAL = 7.5
UMBRAL_POSTURA_SOSTENIDA_SEGUNDOS = 2.5
UMBRAL_CERCANIA_MONITOR = 0.72


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
    dz = lectura.hombro_derecho.z - lectura.hombro_izquierdo.z
    ancho_hombros = math.sqrt(dx**2 + dy**2 + dz**2)
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
        if diferencia_ratio > 0:
            cuello = diferencia_ratio * 320.0
    if lectura.oreja_izquierda.es_confiable() and lectura.oreja_derecha.es_confiable() and lectura.hombro_izquierdo.es_confiable() and lectura.hombro_derecho.es_confiable():
        angulo_hombros = calcular_angulo_horizontal(lectura.hombro_izquierdo, lectura.hombro_derecho)
        angulo_orejas = calcular_angulo_horizontal(lectura.oreja_izquierda, lectura.oreja_derecha)
        lateral = abs(angulo_orejas - angulo_hombros)
        if lateral > 90:
            lateral = 180 - lateral
        centro_hombros_x = (lectura.hombro_izquierdo.x + lectura.hombro_derecho.x) / 2.0
        desviacion_nariz = abs(lectura.nariz.x - centro_hombros_x)
        lateral = max(lateral, desviacion_nariz * 90.0)
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
        return EstadoFisico(0.0, 0.0, 0.0, 0.0, 0.0, EstadoAlerta.AUSENTE)

    clase = lectura.yolo_clase.lower()
    
    alpha = 0.30
    raw_ear = lectura.ear if lectura.rostro_detectado else 0.0
    raw_mar = lectura.mar if lectura.rostro_detectado else 0.0
    
    if sesion.ultimo_ear_filtrado == 0.0:
        sesion.ultimo_ear_filtrado = raw_ear
    else:
        sesion.ultimo_ear_filtrado = alpha * raw_ear + (1.0 - alpha) * sesion.ultimo_ear_filtrado
        
    if sesion.ultimo_mar_filtrado == 0.0:
        sesion.ultimo_mar_filtrado = raw_mar
    else:
        sesion.ultimo_mar_filtrado = alpha * raw_mar + (1.0 - alpha) * sesion.ultimo_mar_filtrado

    umbral_ear = sesion.base_ear * 0.72 if sesion.base_ear > 0 else UMBRAL_EAR_CERRADO
    umbral_mar = sesion.base_mar * 1.65 if sesion.base_mar > 0 else UMBRAL_MAR_BOSTEZO

    if clase in ["bostezo", "yawn"]:
        sesion.racha_yolo_bostezo += 1
        sesion.racha_yolo_sueno = 0
        sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.12)
        if sesion.racha_yolo_bostezo >= 2:
            sesion.iniciar_bostezo()
    elif clase in ["ojos cerrados", "closed_eyes", "drowsy"]:
        sesion.racha_yolo_sueno += 1
        sesion.racha_yolo_bostezo = 0
        sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.22)
        sesion.registrar_ojos_cerrados()
    else:
        sesion.racha_yolo_sueno = max(0, sesion.racha_yolo_sueno - 1)
        sesion.racha_yolo_bostezo = max(0, sesion.racha_yolo_bostezo - 1)
        if lectura.rostro_detectado:
            sesion.registrar_mar_lectura(sesion.ultimo_mar_filtrado)
            
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
                sesion.inicio_bostezo_actual = None
                sesion.bostezo_actual_activo = False
                sesion.finalizar_bostezo()
                sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.03)
            else:
                if sesion.ultimo_mar_filtrado >= umbral_mar:
                    if sesion.inicio_bostezo_actual is None:
                        sesion.inicio_bostezo_actual = time.time()
                        sesion.bostezo_actual_activo = True
                    sesion.indice_fatiga = min(2.5, sesion.indice_fatiga + 0.06)
                
                if sesion.bostezo_actual_activo:
                    if sesion.ultimo_mar_filtrado < max(0.20, umbral_mar * 0.60):
                        duracion = time.time() - sesion.inicio_bostezo_actual
                        min_duracion = max(1.0, sesion.promedio_duracion_bostezo * 0.50)
                        if min_duracion <= duracion <= 6.0:
                            if es_curva_bostezo_gaussiana(sesion.historial_mar, umbral_mar * 0.85):
                                sesion.promedio_duracion_bostezo = 0.8 * sesion.promedio_duracion_bostezo + 0.2 * duracion
                                sesion.iniciar_bostezo()
                        sesion.inicio_bostezo_actual = None
                        sesion.bostezo_actual_activo = False
                        sesion.finalizar_bostezo()
                    elif (time.time() - sesion.inicio_bostezo_actual) > 6.0:
                        sesion.inicio_bostezo_actual = None
                        sesion.bostezo_actual_activo = False
                        sesion.finalizar_bostezo()
                else:
                    sesion.indice_fatiga = max(0.0, sesion.indice_fatiga - 0.03)

    angulo_cuello_raw, angulo_lateral_raw = calcular_postura(lectura, sesion)
    proximidad_monitor = calcular_proximidad_monitor(lectura, sesion)
    if sesion.ultimo_cuello_filtrado == 0.0:
        sesion.ultimo_cuello_filtrado = angulo_cuello_raw
    else:
        sesion.ultimo_cuello_filtrado = alpha * angulo_cuello_raw + (1.0 - alpha) * sesion.ultimo_cuello_filtrado
        
    if sesion.ultimo_lateral_filtrado == 0.0:
        sesion.ultimo_lateral_filtrado = angulo_lateral_raw
    else:
        sesion.ultimo_lateral_filtrado = alpha * angulo_lateral_raw + (1.0 - alpha) * sesion.ultimo_lateral_filtrado
        
    angulo_cuello = sesion.ultimo_cuello_filtrado
    angulo_lateral = sesion.ultimo_lateral_filtrado

    oclusion_consciente = _existe_oclusion_consciente(
        lectura,
        clase,
        sesion.ultimo_ear_filtrado,
        umbral_ear,
        sesion.indice_fatiga,
    )
    if oclusion_consciente:
        angulo_cuello = min(12.0, angulo_cuello * 0.22)
        angulo_lateral = angulo_lateral * 0.45
        proximidad_monitor = proximidad_monitor * 0.55

    evidencia_somnolencia = (
        clase in ["ojos cerrados", "closed_eyes", "drowsy"]
        or sesion.racha_yolo_sueno >= 2
        or sesion.indice_fatiga >= 0.95
        or lectura.mirando_abajo
        or sesion.ultimo_ear_filtrado <= umbral_ear * 1.03
    )

    if angulo_cuello >= 28.0 and evidencia_somnolencia and not oclusion_consciente:
        sesion.racha_cabeceo_riesgo += 1
        sesion.registrar_cabeceo_iniciado()
    else:
        sesion.racha_cabeceo_riesgo = max(0, sesion.racha_cabeceo_riesgo - 1)
        sesion.registrar_cabeza_erguida()
        
    mala_postura = (14.0 <= angulo_cuello < 28.0) or angulo_lateral >= UMBRAL_INCLINACION_LATERAL
    if mala_postura:
        sesion.racha_postura_riesgo += 1
        sesion.registrar_mala_postura()
    else:
        sesion.racha_postura_riesgo = max(0, sesion.racha_postura_riesgo - 1)
        sesion.registrar_buena_postura()

    riesgo_cercania = (
        proximidad_monitor >= UMBRAL_CERCANIA_MONITOR
        and angulo_cuello < 18.0
        and angulo_lateral < UMBRAL_INCLINACION_LATERAL
        and not oclusion_consciente
    )
    if riesgo_cercania:
        sesion.racha_cercania_monitor += 1
    else:
        sesion.racha_cercania_monitor = max(0, sesion.racha_cercania_monitor - 1)

    if not riesgo_cercania and not mala_postura and not evidencia_somnolencia:
        sesion.racha_estable = min(240, sesion.racha_estable + 1)
    else:
        sesion.racha_estable = max(0, sesion.racha_estable - 2)
        
    estado = EstadoAlerta.OPTIMO
    if (
        sesion.segundos_ojos_cerrados() >= UMBRAL_OJOS_CERRADOS_SEGUNDOS
        or sesion.indice_fatiga >= 1.65
        or sesion.racha_yolo_sueno >= 3
    ):
        estado = EstadoAlerta.FATIGA_EXTREMA
    elif sesion.segundos_cabeceo() >= 2.5 or sesion.racha_cabeceo_riesgo >= 4:
        estado = EstadoAlerta.CABECEO
    elif sesion.racha_cercania_monitor >= 3:
        estado = EstadoAlerta.CERCANIA_MONITOR
    elif sesion.segundos_mala_postura() >= UMBRAL_POSTURA_SOSTENIDA_SEGUNDOS or sesion.racha_postura_riesgo >= 4:
        estado = EstadoAlerta.MALA_POSTURA
    elif sesion.cantidad_bostezos_recientes() >= MAX_BOSTEZOS_PERMITIDOS or sesion.indice_fatiga >= 0.85:
        estado = EstadoAlerta.ADVERTENCIA_SUENO
        
    return EstadoFisico(
        sesion.ultimo_ear_filtrado,
        sesion.ultimo_mar_filtrado,
        angulo_cuello,
        angulo_lateral,
        proximidad_monitor,
        estado,
    )
