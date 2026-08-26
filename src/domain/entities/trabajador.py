from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .postura import EstadoAlerta, NivelRiesgo

UMBRAL_OJOS_CERRADOS_SEGUNDOS = 2.0
UMBRAL_CABECEO_SEGUNDOS = 5.0
VENTANA_BOSTEZOS_MINUTOS = 5
MAX_BOSTEZOS_PERMITIDOS = 1
COOLDOWN_ALERTA_SEGUNDOS = 45

@dataclass
class SesionTrabajador:
    inicio_sesion: datetime = field(default_factory=datetime.now)
    ultima_deteccion_exitosa: datetime = field(default_factory=datetime.now)
    inicio_ausencia: datetime | None = None
    ultimo_reingreso: datetime | None = None
    
    inicio_ojos_cerrados: datetime | None = None
    ultimo_registro_ojos_cerrados: datetime | None = None
    
    inicio_cabeceo: datetime | None = None
    ultimo_registro_cabeceo: datetime | None = None
    
    historial_bostezos: list[datetime] = field(default_factory=list)
    bostezo_actual_activo: bool = False
    inicio_bostezo_actual: float | None = None
    ultimo_bostezo_confirmado: datetime | None = None
    promedio_duracion_bostezo: float = 3.0
    
    inicio_mala_postura: datetime | None = None
    ultimo_registro_mala_postura: datetime | None = None
    inicio_cercania_monitor: datetime | None = None
    ultimo_registro_cercania_monitor: datetime | None = None
    ultimo_tiempo_alerta: datetime | None = None
    
    base_ancho_hombros: float = 0.0
    base_ratio_y: float = 0.0
    base_z_nariz_rel: float = 0.0
    base_ancho_cara: float = 0.0
    base_ear: float = 0.0
    base_mar: float = 0.0
    muestras_calibracion: int = 0
    muestras_aprendizaje: int = 0
    
    ultimo_ear_filtrado: float = 0.0
    ultimo_mar_filtrado: float = 0.0
    ultimo_cuello_filtrado: float = 0.0
    ultimo_lateral_filtrado: float = 0.0
    ultimo_proximidad_filtrada: float = 0.0
    
    historial_mar: list[float] = field(default_factory=list)
    total_alertas_emitidas: int = 0
    total_lecturas_validas: int = 0
    racha_yolo_sueno: int = 0
    racha_yolo_bostezo: int = 0
    racha_ojos_cerrados: int = 0
    racha_boca_abierta: int = 0
    racha_estable: int = 0
    racha_cercania_monitor: int = 0
    racha_postura_riesgo: int = 0
    racha_cabeceo_riesgo: int = 0
    indice_fatiga: float = 0.0
    en_riesgo_cabeceo: bool = False
    en_riesgo_postura_cuello: bool = False
    en_riesgo_lateral: bool = False
    en_riesgo_cercania: bool = False
    niveles_riesgo_actuales: dict[str, str] = field(default_factory=dict)
    incidentes: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    estado_estable_actual: str = EstadoAlerta.OPTIMO.name
    ultimo_riesgo_observado: datetime | None = None
    sensibilidad: str = "media"
    cooldown_alerta_segundos: int = COOLDOWN_ALERTA_SEGUNDOS
    contexto_operativo: dict[str, str] = field(default_factory=dict)
 
    def en_cooldown(self) -> bool:
        if self.ultimo_tiempo_alerta is None:
            return False
        return (datetime.now() - self.ultimo_tiempo_alerta).total_seconds() < self.cooldown_alerta_segundos

    def registrar_alerta_disparada(self) -> None:
        self.ultimo_tiempo_alerta = datetime.now()

    def registrar_mar_lectura(self, mar: float) -> None:
        self.historial_mar.append(mar)
        if len(self.historial_mar) > 60:
            self.historial_mar.pop(0)

    def registrar_deteccion(self) -> None:
        now = datetime.now()
        if self.inicio_ausencia is not None:
            self.ultimo_reingreso = now
            self.inicio_ausencia = None
            self.indice_fatiga = max(0.0, self.indice_fatiga - 0.20)
        self.ultima_deteccion_exitosa = now
        self.total_lecturas_validas += 1

    def registrar_ausencia(self) -> None:
        if self.inicio_ausencia is None:
            self.inicio_ausencia = datetime.now()
        self.limpiar_estado_transitorio()
  
    def segundos_sin_deteccion(self) -> float:
        return (datetime.now() - self.ultima_deteccion_exitosa).total_seconds()

    def en_ventana_reingreso(self, segundos_estabilizacion: float = 1.6) -> bool:
        if self.ultimo_reingreso is None:
            return False
        return (datetime.now() - self.ultimo_reingreso).total_seconds() < segundos_estabilizacion
  
    def registrar_ojos_cerrados(self) -> None:
        now = datetime.now()
        if self.inicio_ojos_cerrados is None:
            self.inicio_ojos_cerrados = now
        self.ultimo_registro_ojos_cerrados = now
        self.racha_ojos_cerrados = min(240, self.racha_ojos_cerrados + 1)
  
    def registrar_ojos_abiertos(self) -> None:
        self.racha_ojos_cerrados = max(0, self.racha_ojos_cerrados - 2)
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
            if (datetime.now() - self.ultimo_registro_cabeceo).total_seconds() > 0.1:
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
            if (datetime.now() - self.ultimo_registro_mala_postura).total_seconds() > 0.1:
                self.inicio_mala_postura = None
  
    def segundos_mala_postura(self) -> float:
        if self.inicio_mala_postura is None: return 0.0
        return (datetime.now() - self.inicio_mala_postura).total_seconds()

    def registrar_cercania_monitor(self) -> None:
        now = datetime.now()
        if self.inicio_cercania_monitor is None:
            self.inicio_cercania_monitor = now
        self.ultimo_registro_cercania_monitor = now

    def registrar_distancia_correcta(self) -> None:
        if self.inicio_cercania_monitor is not None:
            if (datetime.now() - self.ultimo_registro_cercania_monitor).total_seconds() > 0.5:
                self.inicio_cercania_monitor = None

    def segundos_cercania_monitor(self) -> float:
        if self.inicio_cercania_monitor is None: return 0.0
        return (datetime.now() - self.inicio_cercania_monitor).total_seconds()
  

    def finalizar_bostezo(self) -> None:
        self.bostezo_actual_activo = False

    def confirmar_bostezo(self, intervalo_minimo_segundos: float = 2.0) -> bool:
        now = datetime.now()
        if self.ultimo_bostezo_confirmado is not None:
            delta = (now - self.ultimo_bostezo_confirmado).total_seconds()
            if delta < intervalo_minimo_segundos:
                return False
        self.historial_bostezos.append(now)
        self.ultimo_bostezo_confirmado = now
        self.bostezo_actual_activo = False
        self.inicio_bostezo_actual = None
        self.racha_boca_abierta = 0
        return True
  
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
        self.historial_bostezos.clear()
        self.bostezo_actual_activo = False
        self.inicio_bostezo_actual = None
        self.ultimo_bostezo_confirmado = None
        self.racha_yolo_sueno = 0
        self.racha_yolo_bostezo = 0
        self.racha_ojos_cerrados = 0
        self.racha_boca_abierta = 0
        self.indice_fatiga = 0.0
        self.en_riesgo_cabeceo = False
        self.en_riesgo_postura_cuello = False
        self.en_riesgo_lateral = False
        self.en_riesgo_cercania = False

    def limpiar_estado_transitorio(self) -> None:
        self.inicio_ojos_cerrados = None
        self.ultimo_registro_ojos_cerrados = None
        self.inicio_cabeceo = None
        self.ultimo_registro_cabeceo = None
        self.inicio_mala_postura = None
        self.ultimo_registro_mala_postura = None
        self.inicio_cercania_monitor = None
        self.ultimo_registro_cercania_monitor = None
        self.historial_bostezos.clear()
        self.bostezo_actual_activo = False
        self.inicio_bostezo_actual = None
        self.ultimo_bostezo_confirmado = None
        self.racha_yolo_sueno = 0
        self.racha_yolo_bostezo = 0
        self.racha_ojos_cerrados = 0
        self.racha_boca_abierta = 0
        self.racha_estable = 0
        self.racha_cercania_monitor = 0
        self.racha_postura_riesgo = 0
        self.racha_cabeceo_riesgo = 0
        self.indice_fatiga = 0.0
        self.en_riesgo_cabeceo = False
        self.en_riesgo_postura_cuello = False
        self.en_riesgo_lateral = False
        self.en_riesgo_cercania = False
  
    def duracion_sesion(self) -> timedelta:
        return datetime.now() - self.inicio_sesion

    def factor_sensibilidad(self) -> float:
        factores = {
            "alta": 0.90,
            "media": 1.0,
            "baja": 1.15,
        }
        return factores.get(self.sensibilidad.lower(), 1.0)

    def aplicar_histeresis_estado(self, estado: EstadoAlerta, salida_segundos: float = 2.0) -> tuple[EstadoAlerta, bool]:
        now = datetime.now()
        if estado not in {EstadoAlerta.OPTIMO, EstadoAlerta.LECTURA_INESTABLE}:
            self.estado_estable_actual = estado.name
            self.ultimo_riesgo_observado = now
            return estado, False

        if self.estado_estable_actual not in {EstadoAlerta.OPTIMO.name, EstadoAlerta.LECTURA_INESTABLE.name}:
            if self.ultimo_riesgo_observado is not None:
                if (now - self.ultimo_riesgo_observado).total_seconds() < salida_segundos:
                    try:
                        return EstadoAlerta[self.estado_estable_actual], True
                    except KeyError:
                        pass

        self.estado_estable_actual = estado.name
        return estado, False

    def registrar_incidente(
        self,
        tipo: str,
        nivel: NivelRiesgo | str,
        duracion: float,
        timestamp: datetime | None = None,
    ) -> None:
        nivel_nombre = nivel.name if isinstance(nivel, NivelRiesgo) else str(nivel)
        momento = timestamp or datetime.now()
        incidente = {
            "tipo": tipo,
            "nivel": nivel_nombre,
            "duracion_segundos": round(duracion, 2),
            "timestamp": momento.isoformat(),
        }
        self.incidentes.setdefault(tipo, []).append(incidente)

    def actualizar_nivel_riesgo(self, tipo: str, nivel: NivelRiesgo, duracion: float) -> None:
        previo = self.niveles_riesgo_actuales.get(tipo, NivelRiesgo.OBSERVACION.name)
        self.niveles_riesgo_actuales[tipo] = nivel.name
        if nivel == NivelRiesgo.RIESGO_CRITICO and previo in {
            NivelRiesgo.RIESGO_LEVE.name,
            NivelRiesgo.RIESGO_CONFIRMADO.name,
        }:
            self.registrar_incidente(tipo, nivel, duracion, datetime.now())
