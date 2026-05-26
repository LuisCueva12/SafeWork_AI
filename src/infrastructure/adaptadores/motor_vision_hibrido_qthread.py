from __future__ import annotations

import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from ...application.servicios import FusionSensoresService, MonitorSafeWorkService
from ...domain.entities.postura import EstadoAlerta, LecturaHibrida, NivelRiesgo
from ..config import SafeWorkSettings
from .captura_hibrida_adapter import CapturaHibridaAdapter
from .memoria_usuario_json_adapter import MemoriaUsuarioJsonAdapter


class MotorVisionIA(QThread):
    senal_frame_actualizado = pyqtSignal(QImage)
    senal_alerta_emitida = pyqtSignal(str)
    senal_estado_sistema = pyqtSignal(str)
    senal_detalle_estado = pyqtSignal(str)
    senal_metricas = pyqtSignal(str)
    senal_resumen_incidencias = pyqtSignal(object)
    senal_nivel_riesgo = pyqtSignal(str)
    senal_bloqueo_requerido = pyqtSignal(str)
    senal_modo_operacion = pyqtSignal(str)
    senal_error_ocurrido = pyqtSignal(str)
    senal_ausencia_resuelta = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = SafeWorkSettings.from_runtime()
        self._captura = CapturaHibridaAdapter(self._settings)
        self._memoria_usuario = MemoriaUsuarioJsonAdapter(
            self._settings.profile_path,
            self._settings.events_path,
            self._settings.incidents_summary_path,
            self._settings.session_report_path,
        )
        contexto_operativo = self._memoria_usuario.construir_contexto_operativo(
            self._settings.contexto_operativo()
        )
        self._monitor = MonitorSafeWorkService(
            self._settings.calibration_seconds,
            memoria_usuario=self._memoria_usuario,
            sensibilidad=self._settings.sensitivity,
            cooldown_alerta_segundos=self._settings.alert_cooldown_seconds,
            contexto_operativo=contexto_operativo,
        )
        self._fusion_sensores = FusionSensoresService()
        self._corriendo = True
        self._ts_inicio_ausencia: float | None = None

    def detener(self) -> None:
        self._corriendo = False
        self.wait(4000)

    def guardar_reporte_actual(self) -> None:
        try:
            self._monitor.guardar_reporte_actual()
        except Exception:
            pass

    def run(self) -> None:
        try:
            self._captura.iniciar_captura()
        except Exception as e:
            self.senal_error_ocurrido.emit(f"Error al inicializar la cámara: {str(e)}")
            return

        try:
            self.senal_modo_operacion.emit(self._captura.resumen_runtime())
            self._emitir_resumen_incidencias()
            
            conteo_frames_vacios = 0
            while self._corriendo:
                try:
                    lectura = self._captura.capturar_lectura()
                    self._fusion_sensores.aplicar(lectura)
                    frame = self._captura.obtener_ultimo_frame()
                except Exception as ex:
                    self.senal_error_ocurrido.emit(f"Error de lectura o procesamiento: {str(ex)}")
                    break

                if frame is None:
                    conteo_frames_vacios += 1
                    if conteo_frames_vacios > 30: # Cerca de 3 segundos continuos sin imagen
                        self.senal_error_ocurrido.emit("Cámara desconectada o sin señal de video.")
                        break
                else:
                    conteo_frames_vacios = 0

                try:
                    resultado = self._monitor.procesar_lectura(lectura)
                except Exception as ex:
                    # Si falla el monitor, reportar el error en vez de colapsar la app
                    self.senal_error_ocurrido.emit(f"Error interno en análisis postural: {str(ex)}")
                    break

                if resultado.mensaje_alerta:
                    self.senal_alerta_emitida.emit(resultado.mensaje_alerta)
                    self._emitir_resumen_incidencias()

                self.senal_estado_sistema.emit(resultado.mensaje_estado)
                self.senal_detalle_estado.emit(resultado.detalle_estado)
                self.senal_metricas.emit(resultado.resumen_metricas)
                self.senal_nivel_riesgo.emit(resultado.estado_fisico.nivel_riesgo.value)

                estado_actual = resultado.estado_fisico.estado
                if estado_actual == EstadoAlerta.AUSENTE:
                    if self._ts_inicio_ausencia is None:
                        self._ts_inicio_ausencia = time.monotonic()
                elif self._ts_inicio_ausencia is not None:
                    duracion = time.monotonic() - self._ts_inicio_ausencia
                    self._ts_inicio_ausencia = None
                    if duracion >= 2.0:
                        self.senal_ausencia_resuelta.emit(duracion)
                
                if resultado.estado_fisico.requiere_bloqueo():
                    self.senal_bloqueo_requerido.emit(resultado.mensaje_alerta or resultado.mensaje_estado)

                if frame is not None:
                    try:
                        frame_anotado = self._dibujar_overlay(frame, lectura, resultado.estado_fisico.estado)
                        self._emitir_frame(frame_anotado)
                    except Exception:
                        # Fallback en caso de que falle el dibujo en el frame, emitimos el frame original
                        self._emitir_frame(frame)

                self.msleep(self._settings.frame_interval_ms)
        except Exception as e:
            self.senal_error_ocurrido.emit(f"Fallo crítico en el motor de visión: {str(e)}")
        finally:
            try:
                self._captura.detener_captura()
            except Exception:
                pass

    def _emitir_resumen_incidencias(self) -> None:
        try:
            resumen = self._memoria_usuario.obtener_resumen_incidencias()
        except Exception:
            resumen = {}
        self.senal_resumen_incidencias.emit(resumen)

    @staticmethod
    def _aplicar_fusion_sensores(lectura: LecturaHibrida | None) -> None:
        FusionSensoresService().aplicar(lectura)

    def _emitir_frame(self, frame_bgr: np.ndarray) -> None:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        alto, ancho, canales = frame_rgb.shape
        imagen = QImage(frame_rgb.data, ancho, alto, canales * ancho, QImage.Format.Format_RGB888).copy()
        self.senal_frame_actualizado.emit(imagen)

    def _dibujar_overlay(
        self,
        frame_bgr: np.ndarray,
        lectura: LecturaHibrida | None,
        estado: EstadoAlerta,
    ) -> np.ndarray:
        canvas = frame_bgr.copy()
        alto, ancho = canvas.shape[:2]

        color_estado = (34, 197, 94)
        if estado == EstadoAlerta.CALIBRANDO:
            color_estado = (56, 189, 248)
        elif estado in (EstadoAlerta.FATIGA_EXTREMA, EstadoAlerta.CABECEO):
            color_estado = (68, 68, 239)
        elif estado in (EstadoAlerta.MALA_POSTURA, EstadoAlerta.CERCANIA_MONITOR, EstadoAlerta.ADVERTENCIA_SUENO):
            color_estado = (0, 140, 255)

        cv2.rectangle(canvas, (0, 0), (ancho, 92), (15, 23, 42), -1)
        cv2.putText(canvas, "SAFEWORK AI", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (241, 245, 249), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Estado: {estado.value}", (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_estado, 2, cv2.LINE_AA)

        if lectura is not None:
            resumen_sensores = f"Ojos {lectura.ear:.2f} | Boca {lectura.mar:.2f}"
            if self._captura.yolo_activo():
                resumen_sensores += f" | IA {lectura.yolo_clase} {lectura.yolo_confianza:.2f}"
            cv2.putText(
                canvas,
                resumen_sensores,
                (20, 82),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (203, 213, 225),
                1,
                cv2.LINE_AA,
            )
            self._dibujar_referencias_corporales(canvas, lectura, ancho, alto)
        else:
            cv2.putText(canvas, "Sin lectura disponible", (20, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

        return canvas

    @staticmethod
    def _dibujar_referencias_corporales(canvas: np.ndarray, lectura: LecturaHibrida, ancho: int, alto: int) -> None:
        if not lectura.cuerpo_detectado:
            return

        puntos = [lectura.hombro_izquierdo, lectura.hombro_derecho, lectura.nariz]
        proyectados = []
        for punto in puntos:
            if punto.es_confiable():
                proyectados.append((int(punto.x * ancho), int(punto.y * alto)))
            else:
                proyectados.append(None)

        if proyectados[0] and proyectados[1]:
            cv2.line(canvas, proyectados[0], proyectados[1], (16, 185, 129), 2, cv2.LINE_AA)
        if proyectados[2]:
            cv2.circle(canvas, proyectados[2], 5, (56, 189, 248), -1)
