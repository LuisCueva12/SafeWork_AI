from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EstadoAlerta(Enum):
    OPTIMO = "OPTIMO"
    ADVERTENCIA_SUENO = "ADVERTENCIA (Bostezos)"
    FATIGA_EXTREMA = "FATIGA EXTREMA (Ojos Cerrados)"
    CABECEO = "CABECEO (Caida de Cabeza)"
    CERCANIA_MONITOR = "CERCANIA AL MONITOR"
    MALA_POSTURA = "MALA POSTURA (Inclinacion)"
    LECTURA_INESTABLE = "LECTURA INESTABLE"
    CALIBRANDO = "CALIBRANDO"
    AUSENTE = "AUSENTE"


class NivelRiesgo(Enum):
    OBSERVACION = "OBSERVACION"
    RIESGO_LEVE = "RIESGO_LEVE"
    RIESGO_CONFIRMADO = "RIESGO_CONFIRMADO"
    RIESGO_CRITICO = "RIESGO_CRITICO"


@dataclass
class Coordenada:
    x: float
    y: float
    z: float
    visibilidad: float = 1.0

    def es_confiable(self) -> bool:
        return self.visibilidad >= 0.6


@dataclass
class LecturaHibrida:
    ear: float
    mar: float
    nariz_y: float
    ancho_cara: float
    rostro_detectado: bool = False
    mirando_abajo: bool = False
    mano_sobre_rostro: bool = False
    yolo_clase: str = "normal"
    yolo_confianza: float = 0.0
    fusion_nivel: NivelRiesgo | None = None
    fusion_motivo: str = ""
    nariz: Coordenada = field(default_factory=lambda: Coordenada(0.0, 0.0, 0.0, 0.0))
    hombro_izquierdo: Coordenada = field(default_factory=lambda: Coordenada(0.0, 0.0, 0.0, 0.0))
    hombro_derecho: Coordenada = field(default_factory=lambda: Coordenada(0.0, 0.0, 0.0, 0.0))
    oreja_izquierda: Coordenada = field(default_factory=lambda: Coordenada(0.0, 0.0, 0.0, 0.0))
    oreja_derecha: Coordenada = field(default_factory=lambda: Coordenada(0.0, 0.0, 0.0, 0.0))
    cuerpo_detectado: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EstadoFisico:
    ear: float
    mar: float
    angulo_cuello: float
    angulo_lateral: float
    proximidad_monitor: float
    estado: EstadoAlerta
    nivel_riesgo: NivelRiesgo = NivelRiesgo.OBSERVACION
    duracion_riesgo_segundos: float = 0.0
    calidad_deteccion: float = 100.0
    puntajes_riesgo: dict[str, int] = field(default_factory=dict)
    evidencias: tuple[str, ...] = field(default_factory=tuple)
    accion_recomendada: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def requiere_alerta_voz(self) -> bool:
        return self.nivel_riesgo in {
            NivelRiesgo.RIESGO_LEVE,
            NivelRiesgo.RIESGO_CONFIRMADO,
            NivelRiesgo.RIESGO_CRITICO,
        }

    def requiere_bloqueo(self) -> bool:
        return self.nivel_riesgo == NivelRiesgo.RIESGO_CRITICO
