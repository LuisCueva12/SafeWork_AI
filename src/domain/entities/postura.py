from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class EstadoPostural(Enum):
    OPTIMO = "OPTIMO"
    ADVERTENCIA = "ADVERTENCIA"
    CRITICO = "CRITICO"
    CALIBRANDO = "CALIBRANDO"
    AUSENTE = "AUSENTE"

@dataclass
class CoordenadaCorporal:
    x: float
    y: float
    z: float
    visibilidad: float = 1.0

    def es_confiable(self) -> bool:
        return self.visibilidad >= 0.6

@dataclass
class LecturaCorporal:
    nariz: CoordenadaCorporal
    hombro_izquierdo: CoordenadaCorporal
    hombro_derecho: CoordenadaCorporal
    oreja_izquierda: CoordenadaCorporal
    oreja_derecha: CoordenadaCorporal
    cadera_izquierda: CoordenadaCorporal
    cadera_derecha: CoordenadaCorporal
    timestamp: datetime = field(default_factory=datetime.now)

    def tiene_lecturas_confiables(self) -> bool:
        return all([
            self.nariz.es_confiable(),
            self.hombro_izquierdo.es_confiable(),
            self.hombro_derecho.es_confiable(),
        ])

@dataclass
class Postura:
    angulo_inclinacion_cuello: float
    angulo_inclinacion_lateral: float
    estado: EstadoPostural
    timestamp: datetime = field(default_factory=datetime.now)
    segundos_en_estado_actual: float = 0.0

    def requiere_intervencion_inmediata(self) -> bool:
        return self.estado == EstadoPostural.CRITICO
