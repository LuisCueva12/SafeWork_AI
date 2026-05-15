"""
Caso de Uso Central: AnalizarPosturaUseCase.
Orquesta el flujo completo sin acoplarse a ninguna tecnología externa.

BUG FIXES:
- Imports corregidos: las entidades y puertos viven en domain (3 niveles arriba desde application/casos_de_uso)
- __future__ annotations para compatibilidad Python 3.10
- El contador de alertas solo se incrementa aquí, no en el adaptador
"""
from __future__ import annotations
import time
import threading
from ...domain.entities.postura import EstadoPostural, LecturaCorporal
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.reglas.calculo_postural import transformar_lectura_en_postura
from ...domain.puertos.puerto_captura_corporal import PuertoCapturaCorporal
from ...domain.puertos.puerto_emision_alertas import PuertoEmisionAlertas


INTERVALO_MUESTREO_SEGUNDOS = 0.1
DURACION_CALIBRACION_SEGUNDOS = 5


class AnalizarPosturaUseCase:

    def __init__(
        self,
        captura_corporal: PuertoCapturaCorporal,
        emision_alertas: PuertoEmisionAlertas,
    ) -> None:
        self._captura = captura_corporal
        self._alertas = emision_alertas
        self._sesion = SesionTrabajador()
        self._ejecutando = False
        self._hilo_monitoreo: threading.Thread | None = None
        self._calibrando = True
        self._inicio_calibracion = time.time()

    def iniciar_monitoreo(self) -> None:
        self._captura.iniciar_captura()
        self._ejecutando = True
        self._hilo_monitoreo = threading.Thread(
            target=self._ciclo_monitoreo_continuo,
            daemon=True,
        )
        self._hilo_monitoreo.start()

    def detener_monitoreo(self) -> None:
        self._ejecutando = False
        self._captura.detener_captura()

    def obtener_sesion_actual(self) -> SesionTrabajador:
        return self._sesion

    def esta_calibrando(self) -> bool:
        return self._calibrando

    def _ciclo_monitoreo_continuo(self) -> None:
        while self._ejecutando:
            if self._esta_en_periodo_calibracion():
                time.sleep(INTERVALO_MUESTREO_SEGUNDOS)
                continue

            lectura = self._captura.obtener_lectura_corporal()

            if lectura is None or not lectura.tiene_lecturas_confiables():
                time.sleep(INTERVALO_MUESTREO_SEGUNDOS)
                continue

            self._procesar_lectura_corporal(lectura)
            time.sleep(INTERVALO_MUESTREO_SEGUNDOS)

    def _esta_en_periodo_calibracion(self) -> bool:
        if not self._calibrando:
            return False
        tiempo_transcurrido = time.time() - self._inicio_calibracion
        if tiempo_transcurrido >= DURACION_CALIBRACION_SEGUNDOS:
            self._calibrando = False
            return False
        return True

    def _procesar_lectura_corporal(self, lectura: LecturaCorporal) -> None:
        self._sesion.registrar_movimiento()

        segundos_desviacion = self._sesion.segundos_en_desviacion_continua()
        postura = transformar_lectura_en_postura(lectura, segundos_desviacion)

        self._alertas.actualizar_estado_visual(postura)

        if postura.estado == EstadoPostural.OPTIMO:
            self._sesion.registrar_correccion_postural()
        else:
            self._sesion.registrar_inicio_desviacion()

        if self._alertas.esta_mostrando_alerta():
            return

        if self._sesion.supera_umbral_inactividad():
            self._sesion.incrementar_contador_alertas()
            self._alertas.emitir_alerta_inactividad(
                self._sesion.minutos_sin_movimiento()
            )
            self._sesion.registrar_movimiento()
            return

        if postura.requiere_intervencion_inmediata():
            self._sesion.incrementar_contador_alertas()
            self._alertas.emitir_alerta_postura_critica(postura)
