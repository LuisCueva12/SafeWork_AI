from __future__ import annotations
import time
import threading
from ...domain.entities.postura import EstadoPostural, LecturaCorporal, Postura
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.reglas.calculo_postural import transformar_lectura_en_postura
from ...domain.puertos.puerto_captura_corporal import PuertoCapturaCorporal
from ...domain.puertos.puerto_emision_alertas import PuertoEmisionAlertas

INTERVALO_MUESTREO = 0.1
DURACION_CALIBRACION = 5


class AnalizarPosturaUseCase:
    def __init__(self, captura_corporal: PuertoCapturaCorporal, emision_alertas: PuertoEmisionAlertas) -> None:
        self._captura = captura_corporal
        self._alertas = emision_alertas
        self._sesion = SesionTrabajador()
        self._ejecutando = False
        self._calibrando = True
        self._inicio_calibracion = time.time()
        self._estado_previo = EstadoPostural.CALIBRANDO

    def iniciar_monitoreo(self) -> None:
        self._captura.iniciar_captura()
        self._ejecutando = True
        threading.Thread(target=self._ciclo, daemon=True).start()

    def detener_monitoreo(self) -> None:
        self._ejecutando = False
        self._captura.detener_captura()

    def obtener_sesion_actual(self) -> SesionTrabajador:
        return self._sesion

    def _ciclo(self) -> None:
        while self._ejecutando:
            if self._en_calibracion():
                time.sleep(INTERVALO_MUESTREO)
                continue
            lectura = self._captura.obtener_lectura_corporal()
            if lectura is None or not lectura.tiene_lecturas_confiables():
                self._manejar_ausencia()
            else:
                self._procesar(lectura)
            time.sleep(INTERVALO_MUESTREO)

    def _en_calibracion(self) -> bool:
        if not self._calibrando:
            return False
        if (time.time() - self._inicio_calibracion) >= DURACION_CALIBRACION:
            self._calibrando = False
            return False
        return True

    def _manejar_ausencia(self) -> None:
        if self._sesion.segundos_sin_deteccion() > 5:
            self._alertas.actualizar_estado_visual(Postura(0, 0, EstadoPostural.AUSENTE))
            self._sesion.registrar_correccion_postural()
            self._estado_previo = EstadoPostural.AUSENTE

    def _procesar(self, lectura: LecturaCorporal) -> None:
        self._sesion.registrar_movimiento()
        self._sesion.registrar_deteccion()

        segundos = self._sesion.segundos_en_desviacion_continua()
        postura = transformar_lectura_en_postura(lectura, segundos)
        self._alertas.actualizar_estado_visual(postura)

        if postura.estado == EstadoPostural.OPTIMO:
            self._sesion.registrar_correccion_postural()
        else:
            self._sesion.registrar_inicio_desviacion()

        # Detectar transición OPTIMO/CALIBRANDO/AUSENTE → ADVERTENCIA (sonido + registro)
        estado_anterior_era_bueno = self._estado_previo in (
            EstadoPostural.OPTIMO, EstadoPostural.CALIBRANDO, EstadoPostural.AUSENTE
        )
        if postura.estado == EstadoPostural.ADVERTENCIA and estado_anterior_era_bueno:
            self._alertas.emitir_notificacion_advertencia(postura)

        self._estado_previo = postura.estado

        if self._alertas.esta_mostrando_alerta():
            return

        if self._sesion.supera_umbral_inactividad():
            self._sesion.incrementar_contador_alertas()
            self._alertas.emitir_alerta_inactividad(self._sesion.minutos_sin_movimiento())
            self._sesion.registrar_movimiento()
            return

        if postura.requiere_intervencion_inmediata():
            self._sesion.incrementar_contador_alertas()
            self._alertas.emitir_alerta_postura_critica(postura)
