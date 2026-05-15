from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

UMBRAL_INACTIVIDAD_MINUTOS = 45
UMBRAL_DESVIACION_GRADOS = 15
UMBRAL_INCLINACION_LATERAL_MAXIMA = 10
UMBRAL_DESVIACION_SEGUNDOS_CONTINUOS = 180

@dataclass
class SesionTrabajador:
    inicio_sesion: datetime = field(default_factory=datetime.now)
    ultimo_movimiento_detectado: datetime = field(default_factory=datetime.now)
    ultima_deteccion_exitosa: datetime = field(default_factory=datetime.now)
    inicio_desviacion_postural: datetime | None = None
    total_alertas_emitidas: int = 0
    esta_en_pausa_activa: bool = False

    def registrar_movimiento(self) -> None:
        self.ultimo_movimiento_detectado = datetime.now()

    def registrar_deteccion(self) -> None:
        self.ultima_deteccion_exitosa = datetime.now()

    def registrar_inicio_desviacion(self) -> None:
        if self.inicio_desviacion_postural is None:
            self.inicio_desviacion_postural = datetime.now()

    def registrar_correccion_postural(self) -> None:
        self.inicio_desviacion_postural = None

    def segundos_en_desviacion_continua(self) -> float:
        if self.inicio_desviacion_postural is None:
            return 0.0
        return (datetime.now() - self.inicio_desviacion_postural).total_seconds()

    def minutos_sin_movimiento(self) -> float:
        return (datetime.now() - self.ultimo_movimiento_detectado).total_seconds() / 60.0

    def segundos_sin_deteccion(self) -> float:
        return (datetime.now() - self.ultima_deteccion_exitosa).total_seconds()

    def supera_umbral_inactividad(self) -> bool:
        return self.minutos_sin_movimiento() >= UMBRAL_INACTIVIDAD_MINUTOS

    def supera_umbral_desviacion_continua(self) -> bool:
        return self.segundos_en_desviacion_continua() >= UMBRAL_DESVIACION_SEGUNDOS_CONTINUOS

    def incrementar_contador_alertas(self) -> None:
        self.total_alertas_emitidas += 1

    def duracion_sesion(self) -> timedelta:
        return datetime.now() - self.inicio_sesion
