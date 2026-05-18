from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

UMBRAL_OJOS_CERRADOS_SEGUNDOS = 2.0
UMBRAL_CABECEO_SEGUNDOS = 5.0
VENTANA_BOSTEZOS_MINUTOS = 5
MAX_BOSTEZOS_PERMITIDOS = 1
COOLDOWN_ALERTA_SEGUNDOS = 45

@dataclass
class SesionTrabajador:
    inicio_sesion: datetime = field(default_factory=datetime.now)
    ultima_deteccion_exitosa: datetime = field(default_factory=datetime.now)
    
    inicio_ojos_cerrados: datetime | None = None
    ultimo_registro_ojos_cerrados: datetime | None = None
    
    inicio_cabeceo: datetime | None = None
    ultimo_registro_cabeceo: datetime | None = None
    
    historial_bostezos: list[datetime] = field(default_factory=list)
    bostezo_actual_activo: bool = False
    inicio_bostezo_actual: float | None = None
    promedio_duracion_bostezo: float = 3.0
    
    inicio_mala_postura: datetime | None = None
    ultimo_registro_mala_postura: datetime | None = None
    ultimo_tiempo_alerta: datetime | None = None
    
    base_ancho_hombros: float = 0.0
    base_ratio_y: float = 0.0
    base_z_nariz_rel: float = 0.0
    base_ancho_cara: float = 0.0
    base_ear: float = 0.0
    base_mar: float = 0.0
    muestras_calibracion: int = 0
    
    ultimo_ear_filtrado: float = 0.0
    ultimo_mar_filtrado: float = 0.0
    ultimo_cuello_filtrado: float = 0.0
    ultimo_lateral_filtrado: float = 0.0
    
    historial_mar: list[float] = field(default_factory=list)
    total_alertas_emitidas: int = 0
    racha_yolo_sueno: int = 0
    racha_yolo_bostezo: int = 0
    indice_fatiga: float = 0.0
 
    def en_cooldown(self) -> bool:
        if self.ultimo_tiempo_alerta is None:
            return False
        return (datetime.now() - self.ultimo_tiempo_alerta).total_seconds() < COOLDOWN_ALERTA_SEGUNDOS

    def registrar_alerta_disparada(self) -> None:
        self.ultimo_tiempo_alerta = datetime.now()

    def registrar_mar_lectura(self, mar: float) -> None:
        self.historial_mar.append(mar)
        if len(self.historial_mar) > 60:
            self.historial_mar.pop(0)

    def registrar_deteccion(self) -> None:
        self.ultima_deteccion_exitosa = datetime.now()
  
    def segundos_sin_deteccion(self) -> float:
        return (datetime.now() - self.ultima_deteccion_exitosa).total_seconds()
  
    def registrar_ojos_cerrados(self) -> None:
        now = datetime.now()
        if self.inicio_ojos_cerrados is None:
            self.inicio_ojos_cerrados = now
        self.ultimo_registro_ojos_cerrados = now
  
    def registrar_ojos_abiertos(self) -> None:
        if self.inicio_ojos_cerrados is not None:
            if (datetime.now() - self.ultimo_registro_ojos_cerrados).total_seconds() > 0.5:
                self.inicio_ojos_cerrados = None
  
    def segundos_ojos_cerrados(self) -> float:
        if self.inicio_ojos_cerrados is None: return 0.0
        return (datetime.now() - self.inicio_ojos_cerrados).total_seconds()
  
    def registrar_cabeceo_iniciado(self) -> None:
        now = datetime.now()
        if self.inicio_cabeceo is None:
            self.inicio_cabeceo = now
        self.ultimo_registro_cabeceo = now
  
    def registrar_cabeza_erguida(self) -> None:
        if self.inicio_cabeceo is not None:
            if (datetime.now() - self.ultimo_registro_cabeceo).total_seconds() > 0.5:
                self.inicio_cabeceo = None
  
    def segundos_cabeceo(self) -> float:
        if self.inicio_cabeceo is None: return 0.0
        return (datetime.now() - self.inicio_cabeceo).total_seconds()
  
    def registrar_mala_postura(self) -> None:
        now = datetime.now()
        if self.inicio_mala_postura is None:
            self.inicio_mala_postura = now
        self.ultimo_registro_mala_postura = now
  
    def registrar_buena_postura(self) -> None:
        if self.inicio_mala_postura is not None:
            if (datetime.now() - self.ultimo_registro_mala_postura).total_seconds() > 0.5:
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
        self.ultimo_registro_ojos_cerrados = None
        self.inicio_cabeceo = None
        self.ultimo_registro_cabeceo = None
        self.inicio_mala_postura = None
        self.ultimo_registro_mala_postura = None
        self.historial_bostezos.clear()
        self.bostezo_actual_activo = False
        self.racha_yolo_sueno = 0
        self.racha_yolo_bostezo = 0
        self.indice_fatiga = 0.0
  
    def duracion_sesion(self) -> timedelta:
        return datetime.now() - self.inicio_sesion
