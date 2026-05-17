from __future__ import annotations
import time
import threading
from ...domain.entities.postura import EstadoAlerta, LecturaHibrida, EstadoFisico
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.reglas.calculo_postural import analizar_lectura_hibrida
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
            lectura = self._captura.obtener_lectura_corporal()
            
            if self._en_calibracion():
                if lectura and lectura.cuerpo_detectado and lectura.rostro_detectado:
                    if lectura.nariz.es_confiable() and lectura.hombro_izquierdo.es_confiable() and lectura.hombro_derecho.es_confiable():
                        h_y = (lectura.hombro_izquierdo.y + lectura.hombro_derecho.y) / 2
                        ancho = abs(lectura.hombro_izquierdo.x - lectura.hombro_derecho.x)
                        if ancho > 0:
                            ratio = (h_y - lectura.nariz.y) / ancho
                            n = self._sesion.muestras_calibracion
                            self._sesion.base_ancho_hombros = (self._sesion.base_ancho_hombros * n + ancho) / (n + 1)
                            self._sesion.base_ratio_y = (self._sesion.base_ratio_y * n + ratio) / (n + 1)
                            self._sesion.base_ancho_cara = (self._sesion.base_ancho_cara * n + lectura.ancho_cara) / (n + 1)
                            self._sesion.base_ear = (self._sesion.base_ear * n + lectura.ear) / (n + 1)
                            self._sesion.base_mar = (self._sesion.base_mar * n + lectura.mar) / (n + 1)
                            self._sesion.muestras_calibracion += 1

                self._alertas.actualizar_estado_visual(EstadoFisico(0, 0, 0, 0, EstadoAlerta.CALIBRANDO))
                time.sleep(INTERVALO_MUESTREO)
                continue
            
            if lectura is None or (not lectura.rostro_detectado and not lectura.cuerpo_detectado):
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
            self._alertas.actualizar_estado_visual(EstadoFisico(0, 0, 0, 0, EstadoAlerta.AUSENTE))

    def _procesar(self, lectura: LecturaHibrida) -> None:
        self._sesion.registrar_deteccion()

        estado_fisico = analizar_lectura_hibrida(lectura, self._sesion)
        self._alertas.actualizar_estado_visual(estado_fisico)

        if self._alertas.esta_mostrando_alerta():
            return

        if estado_fisico.requiere_bloqueo():
            self._sesion.incrementar_contador_alertas()
            self._alertas.emitir_alerta_bloqueante(estado_fisico)
