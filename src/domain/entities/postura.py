from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class EstadoAlerta(Enum):
    OPTIMO = "OPTIMO"
    ADVERTENCIA_SUEÑO = "ADVERTENCIA (Bostezos)"
    FATIGA_EXTREMA = "FATIGA EXTREMA (Ojos Cerrados)"
    CABECEO = "CABECEO (Caída de Cabeza)"
    MALA_POSTURA = "MALA POSTURA (Inclinación)"
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
    
    nariz: Coordenada = field(default_factory=lambda: Coordenada(0,0,0,0))
    hombro_izquierdo: Coordenada = field(default_factory=lambda: Coordenada(0,0,0,0))
    hombro_derecho: Coordenada = field(default_factory=lambda: Coordenada(0,0,0,0))
    oreja_izquierda: Coordenada = field(default_factory=lambda: Coordenada(0,0,0,0))
    oreja_derecha: Coordenada = field(default_factory=lambda: Coordenada(0,0,0,0))
    cuerpo_detectado: bool = False

    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EstadoFisico:
    ear: float
    mar: float
    angulo_cuello: float
    angulo_lateral: float
    estado: EstadoAlerta
    timestamp: datetime = field(default_factory=datetime.now)

    def requiere_bloqueo(self) -> bool:
        return self.estado in (EstadoAlerta.FATIGA_EXTREMA, EstadoAlerta.CABECEO, EstadoAlerta.MALA_POSTURA, EstadoAlerta.ADVERTENCIA_SUEÑO)
