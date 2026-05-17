from __future__ import annotations
import math
from ..entities.postura import EstadoAlerta, EstadoFisico, LecturaHibrida
from ..entities.trabajador import SesionTrabajador, UMBRAL_OJOS_CERRADOS_SEGUNDOS, UMBRAL_CABECEO_SEGUNDOS, MAX_BOSTEZOS_PERMITIDOS

UMBRAL_EAR_CERRADO = 0.15
UMBRAL_MAR_BOSTEZO = 0.40
UMBRAL_NARIZ_Y_CABECEO = 0.70
UMBRAL_INCLINACION_CUELLO = 20.0
UMBRAL_INCLINACION_LATERAL = 10.0

def calcular_angulo(p1, p2) -> float:
    return math.degrees(math.atan2(abs(p2.y - p1.y), abs(p2.x - p1.x)))

def calcular_angulo_z(p1, p2) -> float:
    return math.degrees(math.atan2(abs(p2.z - p1.z), abs(p2.y - p1.y)))

def calcular_angulo_horizontal(p1, p2) -> float:
    dy = p2.y - p1.y
    dx = p2.x - p1.x
    return math.degrees(math.atan2(dy, dx))

def calcular_postura(lectura: LecturaHibrida, sesion: SesionTrabajador) -> tuple[float, float]:
    if not lectura.cuerpo_detectado:
        return 0.0, 0.0
        
    cuello = 0.0
    lateral = 0.0
    
    if lectura.nariz.es_confiable() and lectura.hombro_izquierdo.es_confiable() and lectura.hombro_derecho.es_confiable():
        hombro_medio_y = (lectura.hombro_izquierdo.y + lectura.hombro_derecho.y) / 2
        ancho_hombros = abs(lectura.hombro_izquierdo.x - lectura.hombro_derecho.x)
        
        if ancho_hombros > 0 and sesion.base_ratio_y > 0:
            ratio_y = (hombro_medio_y - lectura.nariz.y) / ancho_hombros
            
            diferencia_ratio = sesion.base_ratio_y - ratio_y
            if diferencia_ratio > 0:
                cuello = diferencia_ratio * 200.0
            
            if sesion.base_ancho_cara > 0 and lectura.ancho_cara > 0:
                crecimiento_cara = lectura.ancho_cara / sesion.base_ancho_cara
                if crecimiento_cara > 1.30:
                    cuello = max(cuello, 25.0) 
            
        if lectura.oreja_izquierda.es_confiable() and lectura.oreja_derecha.es_confiable():
            angulo_hombros = calcular_angulo_horizontal(lectura.hombro_izquierdo, lectura.hombro_derecho)
            angulo_orejas = calcular_angulo_horizontal(lectura.oreja_izquierda, lectura.oreja_derecha)
            lateral = abs(angulo_orejas - angulo_hombros)
            if lateral > 90:
                lateral = 180 - lateral
            
    return cuello, lateral

def analizar_lectura_hibrida(lectura: LecturaHibrida, sesion: SesionTrabajador) -> EstadoFisico:
    if not lectura.rostro_detectado and not lectura.cuerpo_detectado:
        return EstadoFisico(0, 0, 0, 0, EstadoAlerta.AUSENTE)

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

    if lectura.rostro_detectado:
        umbral_ear = sesion.base_ear * 0.55 if sesion.base_ear > 0 else UMBRAL_EAR_CERRADO
        umbral_mar = sesion.base_mar * 2.20 if sesion.base_mar > 0 else UMBRAL_MAR_BOSTEZO

        if sesion.ultimo_ear_filtrado <= umbral_ear:
            sesion.registrar_ojos_cerrados()
        else:
            sesion.registrar_ojos_abiertos()

        if sesion.ultimo_mar_filtrado >= umbral_mar:
            sesion.iniciar_bostezo()
        else:
            sesion.finalizar_bostezo()

    angulo_cuello_raw, angulo_lateral_raw = calcular_postura(lectura, sesion)

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

    if angulo_cuello >= 35.0:
        sesion.registrar_cabeceo_iniciado()
    else:
        sesion.registrar_cabeza_erguida()

    mala_postura = (20.0 <= angulo_cuello < 35.0) or angulo_lateral >= UMBRAL_INCLINACION_LATERAL
    
    if mala_postura:
        sesion.registrar_mala_postura()
    else:
        sesion.registrar_buena_postura()

    estado = EstadoAlerta.OPTIMO

    if sesion.segundos_ojos_cerrados() >= UMBRAL_OJOS_CERRADOS_SEGUNDOS:
        estado = EstadoAlerta.FATIGA_EXTREMA
    elif sesion.segundos_cabeceo() >= UMBRAL_CABECEO_SEGUNDOS:
        estado = EstadoAlerta.CABECEO
    elif sesion.segundos_mala_postura() >= 5.0:
        estado = EstadoAlerta.MALA_POSTURA
    elif sesion.cantidad_bostezos_recientes() >= MAX_BOSTEZOS_PERMITIDOS:
        estado = EstadoAlerta.ADVERTENCIA_SUEÑO

    return EstadoFisico(
        ear=sesion.ultimo_ear_filtrado,
        mar=sesion.ultimo_mar_filtrado,
        angulo_cuello=angulo_cuello,
        angulo_lateral=angulo_lateral,
        estado=estado
    )
