from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

UMBRAL_OJOS_CERRADOS_SEGUNDOS = 2.0
UMBRAL_CABECEO_SEGUNDOS = 5.0
VENTANA_BOSTEZOS_MINUTOS = 5
MAX_BOSTEZOS_PERMITIDOS = 1

@dataclass
class SesionTrabajador:
    inicio_sesion: datetime = field(default_factory=datetime.now)
    ultima_deteccion_exitosa: datetime = field(default_factory=datetime.now)
    
    inicio_ojos_cerrados: datetime | None = None
    inicio_cabeceo: datetime | None = None
    historial_bostezos: list[datetime] = field(default_factory=list)
    bostezo_actual_activo: bool = False
    
    inicio_mala_postura: datetime | None = None
    base_ancho_hombros: float = 0.0
    base_ratio_y: float = 0.0
    base_ancho_cara: float = 0.0
    base_ear: float = 0.0
    base_mar: float = 0.0
    muestras_calibracion: int = 0
    
    ultimo_ear_filtrado: float = 0.0
    ultimo_mar_filtrado: float = 0.0
    ultimo_cuello_filtrado: float = 0.0
    ultimo_lateral_filtrado: float = 0.0
    
    total_alertas_emitidas: int = 0

    def registrar_deteccion(self) -> None:
        self.ultima_deteccion_exitosa = datetime.now()

    def segundos_sin_deteccion(self) -> float:
        return (datetime.now() - self.ultima_deteccion_exitosa).total_seconds()

    def registrar_ojos_cerrados(self) -> None:
        if self.inicio_ojos_cerrados is None:
            self.inicio_ojos_cerrados = datetime.now()

    def registrar_ojos_abiertos(self) -> None:
        self.inicio_ojos_cerrados = None

    def segundos_ojos_cerrados(self) -> float:
        if self.inicio_ojos_cerrados is None: return 0.0
        return (datetime.now() - self.inicio_ojos_cerrados).total_seconds()

    def registrar_cabeceo_iniciado(self) -> None:
        if self.inicio_cabeceo is None:
            self.inicio_cabeceo = datetime.now()

    def registrar_cabeza_erguida(self) -> None:
        self.inicio_cabeceo = None

    def segundos_cabeceo(self) -> float:
        if self.inicio_cabeceo is None: return 0.0
        return (datetime.now() - self.inicio_cabeceo).total_seconds()

    def registrar_mala_postura(self) -> None:
        if self.inicio_mala_postura is None:
            self.inicio_mala_postura = datetime.now()

    def registrar_buena_postura(self) -> None:
        self.inicio_mala_postura = None

    def segundos_mala_postura(self) -> float:
        if self.inicio_mala_postura is None: return 0.0
        return (datetime.now() - self.inicio_mala_postura).total_seconds()

    def iniciar_bostezo(self) -> None:
        if not self.bostezo_actual_activo:
            self.bostezo_actual_activo = True
            self.historial_bostezos.append(datetime.now())

    def finalizar_bostezo(self) -> None:
        self.bostezo_actual_activo = False

    def limpiar_bostezos_antiguos(self) -> None:
        limite = datetime.now() - timedelta(minutes=VENTANA_BOSTEZOS_MINUTOS)
        self.historial_bostezos = [b for b in self.historial_bostezos if b > limite]

    def cantidad_bostezos_recientes(self) -> int:
        self.limpiar_bostezos_antiguos()
        return len(self.historial_bostezos)

    def incrementar_contador_alertas(self) -> None:
        self.total_alertas_emitidas += 1
        self.inicio_ojos_cerrados = None
        self.inicio_cabeceo = None
        self.inicio_mala_postura = None
        self.historial_bostezos.clear()
        self.bostezo_actual_activo = False

    def duracion_sesion(self) -> timedelta:
        return datetime.now() - self.inicio_sesion
