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
    CALIBRANDO = "CALIBRANDO"
    AUSENTE = "AUSENTE"


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
    timestamp: datetime = field(default_factory=datetime.now)

    def requiere_bloqueo(self) -> bool:
        return self.estado in {
            EstadoAlerta.FATIGA_EXTREMA,
            EstadoAlerta.CABECEO,
            EstadoAlerta.CERCANIA_MONITOR,
            EstadoAlerta.MALA_POSTURA,
            EstadoAlerta.ADVERTENCIA_SUENO,
        }
