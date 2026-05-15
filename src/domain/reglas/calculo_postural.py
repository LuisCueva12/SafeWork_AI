"""
Reglas matemáticas puras del negocio.
Transforma una LecturaCorporal en una Postura con su estado evaluado.
"""
import math
from ..entities.postura import (
    LecturaCorporal,
    CoordenadaCorporal,
    Postura,
    EstadoPostural,
)
from ..entities.trabajador import UMBRAL_DESVIACION_GRADOS


def calcular_angulo_entre_tres_puntos(
    punto_a: CoordenadaCorporal,
    punto_vertice: CoordenadaCorporal,
    punto_b: CoordenadaCorporal,
) -> float:
    vector_va = (punto_a.x - punto_vertice.x, punto_a.y - punto_vertice.y)
    vector_vb = (punto_b.x - punto_vertice.x, punto_b.y - punto_vertice.y)

    producto_punto = vector_va[0] * vector_vb[0] + vector_va[1] * vector_vb[1]
    magnitud_va = math.sqrt(vector_va[0] ** 2 + vector_va[1] ** 2)
    magnitud_vb = math.sqrt(vector_vb[0] ** 2 + vector_vb[1] ** 2)

    if magnitud_va * magnitud_vb == 0:
        return 0.0

    coseno = max(-1.0, min(1.0, producto_punto / (magnitud_va * magnitud_vb)))
    return math.degrees(math.acos(coseno))


def calcular_punto_medio(
    punto_a: CoordenadaCorporal,
    punto_b: CoordenadaCorporal,
) -> CoordenadaCorporal:
    return CoordenadaCorporal(
        x=(punto_a.x + punto_b.x) / 2,
        y=(punto_a.y + punto_b.y) / 2,
        z=(punto_a.z + punto_b.z) / 2,
        visibilidad=min(punto_a.visibilidad, punto_b.visibilidad),
    )


def evaluar_estado_desde_angulo(angulo_inclinacion: float, segundos_en_estado: float) -> EstadoPostural:
    if angulo_inclinacion > UMBRAL_DESVIACION_GRADOS and segundos_en_estado >= 180:
        return EstadoPostural.CRITICO
    if angulo_inclinacion > UMBRAL_DESVIACION_GRADOS:
        return EstadoPostural.ADVERTENCIA
    return EstadoPostural.OPTIMO


def transformar_lectura_en_postura(
    lectura: LecturaCorporal,
    segundos_en_estado_actual: float = 0.0,
) -> Postura:
    punto_medio_hombros = calcular_punto_medio(
        lectura.hombro_izquierdo,
        lectura.hombro_derecho,
    )
    punto_medio_orejas = calcular_punto_medio(
        lectura.oreja_izquierda,
        lectura.oreja_derecha,
    )

    angulo_inclinacion_cuello = calcular_angulo_entre_tres_puntos(
        punto_medio_orejas,
        punto_medio_hombros,
        CoordenadaCorporal(
            x=punto_medio_hombros.x,
            y=punto_medio_hombros.y - 1.0,
            z=punto_medio_hombros.z,
        ),
    )

    angulo_lateral = abs(
        lectura.hombro_izquierdo.y - lectura.hombro_derecho.y
    ) * 100

    estado = evaluar_estado_desde_angulo(angulo_inclinacion_cuello, segundos_en_estado_actual)

    return Postura(
        angulo_inclinacion_cuello=angulo_inclinacion_cuello,
        angulo_inclinacion_lateral=angulo_lateral,
        estado=estado,
        segundos_en_estado_actual=segundos_en_estado_actual,
    )
