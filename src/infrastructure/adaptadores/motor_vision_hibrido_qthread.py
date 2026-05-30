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


_COLOR_OVERLAY_OK      = (34, 197, 94)
_COLOR_OVERLAY_INFO    = (56, 189, 248)
_COLOR_OVERLAY_CRITICO = (68, 68, 239)
_COLOR_OVERLAY_AVISO   = (0, 140, 255)
_COLOR_OVERLAY_BG      = (15, 23, 42)
_COLOR_OVERLAY_TEXT    = (241, 245, 249)
_COLOR_OVERLAY_DIM     = (203, 213, 225)
_COLOR_OVERLAY_MUTED   = (148, 163, 184)
_COLOR_OVERLAY_HOMBROS = (16, 185, 129)
_COLOR_OVERLAY_NARIZ   = (56, 189, 248)

_METRICS_UPDATE_STRIDE = 3
_EMPTY_FRAME_TIMEOUT   = 30


class MotorVisionIA(QThread):
    senal_frame_actualizado   = pyqtSignal(QImage)
    senal_alerta_emitida      = pyqtSignal(str)
    senal_estado_sistema      = pyqtSignal(str)
    senal_detalle_estado      = pyqtSignal(str)
    senal_metricas            = pyqtSignal(str)
    senal_resumen_incidencias = pyqtSignal(object)
    senal_nivel_riesgo        = pyqtSignal(str)
    senal_bloqueo_requerido   = pyqtSignal(str)
    senal_modo_operacion      = pyqtSignal(str)
    senal_error_ocurrido      = pyqtSignal(str)
    senal_ausencia_resuelta   = pyqtSignal(float)

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
        self._fusion_sensores      = FusionSensoresService()
        self._corriendo            = True
        self._ts_inicio_ausencia   = None
        self._ui_visible           = True
        self._frame_contador       = 0
        self._ultimo_estado        = ""
        self._ultimo_detalle       = ""
        self._ultimo_nivel         = ""
        self._canvas_overlay: np.ndarray | None = None

    def detener(self) -> None:
        self._corriendo = False
        self.requestInterruption()
        self.wait(4000)

    def set_ui_visible(self, visible: bool) -> None:
        self._ui_visible = visible

    def guardar_reporte_actual(self) -> None:
        try:
            self._monitor.guardar_reporte_actual()
        except Exception:
            pass

    def run(self) -> None:
        try:
            self._captura.iniciar_captura()
        except Exception as exc:
            self.senal_error_ocurrido.emit(f"Error al inicializar la cámara: {exc}")
            return

        try:
            self.senal_modo_operacion.emit(self._captura.resumen_runtime())
            self._emitir_resumen_incidencias()

            frames_vacios = 0
            while self._corriendo:
                try:
                    lectura = self._captura.capturar_lectura()
                    self._fusion_sensores.aplicar(lectura)
                    frame   = self._captura.obtener_ultimo_frame()
                except Exception as exc:
                    self.senal_error_ocurrido.emit(f"Error de lectura: {exc}")
                    break

                if frame is None:
                    frames_vacios += 1
                    if frames_vacios > _EMPTY_FRAME_TIMEOUT:
                        self.senal_error_ocurrido.emit("Cámara desconectada o sin señal de video.")
                        break
                else:
                    frames_vacios = 0

                try:
                    resultado = self._monitor.procesar_lectura(lectura)
                except Exception as exc:
                    self.senal_error_ocurrido.emit(f"Error en análisis postural: {exc}")
                    break

                self._frame_contador += 1
                self._emitir_signals(resultado)
                self._gestionar_ausencia(resultado.estado_fisico.estado)

                if resultado.estado_fisico.requiere_bloqueo():
                    self.senal_bloqueo_requerido.emit(
                        resultado.mensaje_alerta or resultado.mensaje_estado
                    )

                if frame is not None and self._ui_visible:
                    try:
                        frame_anotado = self._construir_frame(
                            frame, lectura, resultado.estado_fisico.estado
                        )
                        self._emitir_frame(frame_anotado)
                    except Exception:
                        self._emitir_frame(frame)

                self.msleep(self._settings.frame_interval_ms)

        except Exception as exc:
            self.senal_error_ocurrido.emit(f"Fallo crítico en el motor de visión: {exc}")
        finally:
            try:
                self._captura.detener_captura()
            except Exception:
                pass

    def _emitir_signals(self, resultado) -> None:
        if resultado.mensaje_alerta:
            self.senal_alerta_emitida.emit(resultado.mensaje_alerta)
            self._emitir_resumen_incidencias()

        if resultado.mensaje_estado != self._ultimo_estado:
            self.senal_estado_sistema.emit(resultado.mensaje_estado)
            self._ultimo_estado = resultado.mensaje_estado

        if resultado.detalle_estado != self._ultimo_detalle:
            self.senal_detalle_estado.emit(resultado.detalle_estado)
            self._ultimo_detalle = resultado.detalle_estado

        if self._frame_contador % _METRICS_UPDATE_STRIDE == 0:
            self.senal_metricas.emit(resultado.resumen_metricas)
            nivel = resultado.estado_fisico.nivel_riesgo.value
            if nivel != self._ultimo_nivel:
                self.senal_nivel_riesgo.emit(nivel)
                self._ultimo_nivel = nivel

    def _gestionar_ausencia(self, estado: EstadoAlerta) -> None:
        if estado == EstadoAlerta.AUSENTE:
            if self._ts_inicio_ausencia is None:
                self._ts_inicio_ausencia = time.monotonic()
        elif self._ts_inicio_ausencia is not None:
            duracion = time.monotonic() - self._ts_inicio_ausencia
            self._ts_inicio_ausencia = None
            if duracion >= 2.0:
                self.senal_ausencia_resuelta.emit(duracion)

    def _emitir_resumen_incidencias(self) -> None:
        try:
            resumen = self._memoria_usuario.obtener_resumen_incidencias()
        except Exception:
            resumen = {}
        self.senal_resumen_incidencias.emit(resumen)

    def _emitir_frame(self, frame_bgr: np.ndarray) -> None:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        alto, ancho, canales = frame_rgb.shape
        imagen = QImage(
            frame_rgb.data, ancho, alto, canales * ancho, QImage.Format.Format_RGB888
        ).copy()
        self.senal_frame_actualizado.emit(imagen)

    def _construir_frame(
        self,
        frame_bgr: np.ndarray,
        lectura: LecturaHibrida | None,
        estado: EstadoAlerta,
    ) -> np.ndarray:
        alto, ancho = frame_bgr.shape[:2]
        pad_top     = 96
        shape       = (alto + pad_top, ancho, 3)

        if self._canvas_overlay is None or self._canvas_overlay.shape != shape:
            self._canvas_overlay = np.zeros(shape, dtype=np.uint8)
        else:
            self._canvas_overlay[:pad_top, :] = 0

        canvas = self._canvas_overlay
        canvas[pad_top:, :] = frame_bgr

        color = self._color_por_estado(estado)
        cv2.rectangle(canvas, (0, 0), (ancho, pad_top), _COLOR_OVERLAY_BG, -1)
        cv2.putText(
            canvas, "SAFEWORK AI", (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, _COLOR_OVERLAY_TEXT, 2, cv2.LINE_AA
        )
        cv2.putText(
            canvas, f"Estado: {estado.value}", (20, 58),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA
        )

        if lectura is not None:
            resumen = f"Ojos {lectura.ear:.2f} | Boca {lectura.mar:.2f}"
            if self._captura.yolo_activo():
                resumen += f" | IA {lectura.yolo_clase} {lectura.yolo_confianza:.2f}"
            cv2.putText(
                canvas, resumen, (20, 84),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, _COLOR_OVERLAY_DIM, 1, cv2.LINE_AA
            )
            self._dibujar_esqueleto(canvas, lectura, ancho, alto, pad_top)
        else:
            cv2.putText(
                canvas, "Sin lectura disponible", (20, 84),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, _COLOR_OVERLAY_MUTED, 1, cv2.LINE_AA
            )

        return canvas

    @staticmethod
    def _color_por_estado(estado: EstadoAlerta) -> tuple[int, int, int]:
        if estado == EstadoAlerta.CALIBRANDO:
            return _COLOR_OVERLAY_INFO
        if estado in (EstadoAlerta.FATIGA_EXTREMA, EstadoAlerta.CABECEO):
            return _COLOR_OVERLAY_CRITICO
        if estado in (
            EstadoAlerta.MALA_POSTURA,
            EstadoAlerta.CERCANIA_MONITOR,
            EstadoAlerta.ADVERTENCIA_SUENO,
        ):
            return _COLOR_OVERLAY_AVISO
        return _COLOR_OVERLAY_OK

    @staticmethod
    def _dibujar_esqueleto(
        canvas: np.ndarray,
        lectura: LecturaHibrida,
        ancho: int,
        alto: int,
        pad_y: int,
    ) -> None:
        if not lectura.cuerpo_detectado:
            return

        def proyectar(punto):
            return (int(punto.x * ancho), int(punto.y * alto) + pad_y) if punto.es_confiable() else None

        hombro_izq = proyectar(lectura.hombro_izquierdo)
        hombro_der = proyectar(lectura.hombro_derecho)
        nariz      = proyectar(lectura.nariz)

        if hombro_izq and hombro_der:
            cv2.line(canvas, hombro_izq, hombro_der, _COLOR_OVERLAY_HOMBROS, 2, cv2.LINE_AA)
        if nariz:
            cv2.circle(canvas, nariz, 5, _COLOR_OVERLAY_NARIZ, -1)
