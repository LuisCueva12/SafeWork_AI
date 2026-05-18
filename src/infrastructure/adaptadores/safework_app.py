from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .motor_vision_hibrido_qthread import MotorVisionIA
from .voz_qthread_adapter import VozQThreadAdapter


class SafeWorkApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SafeWork AI")
        self.resize(760, 640)
        self.setMinimumSize(680, 560)

        self._ultimo_mensaje_voz = ""
        self._voz_habilitada = True

        self._worker_voz = VozQThreadAdapter(self)
        self._worker_voz.start()

        self._motor = MotorVisionIA(parent=self)
        self._motor.senal_frame_actualizado.connect(self._actualizar_frame)
        self._motor.senal_alerta_emitida.connect(self._manejar_alerta)
        self._motor.senal_estado_sistema.connect(self._actualizar_estado)
        self._motor.senal_detalle_estado.connect(self._actualizar_detalle_estado)
        self._motor.senal_metricas.connect(self._actualizar_metricas)
        self._motor.start()

        self._construir_ui()

    def _construir_ui(self) -> None:
        contenedor = QWidget(self)
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("SAFEWORK AI")
        header.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(header)

        self._subtitulo = QLabel("Monitoreo hibrido de postura y fatiga en tiempo real")
        self._subtitulo.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(self._subtitulo)

        self._video = QLabel("Inicializando camara y modelos...")
        self._video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video.setMinimumSize(640, 360)
        self._video.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px;"
        )
        layout.addWidget(self._video, 1)

        fila_estado = QHBoxLayout()
        fila_estado.setSpacing(12)

        self._estado = QLabel("CALIBRANDO")
        self._estado.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #38bdf8; background: #111827;"
            "padding: 10px 14px; border-radius: 10px;"
        )
        fila_estado.addWidget(self._estado)

        self._detalle = QLabel("Esperando perfil basal del usuario...")
        self._detalle.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        fila_estado.addWidget(self._detalle, 1)

        self._boton_voz = QPushButton("Voz: Activa")
        self._boton_voz.clicked.connect(self._alternar_voz)
        fila_estado.addWidget(self._boton_voz)

        layout.addLayout(fila_estado)

        self._metricas = QLabel("EAR -- | MAR -- | Cuello -- | Lateral --")
        self._metricas.setStyleSheet(
            "font-size: 12px; color: #93c5fd; background: #0f172a; "
            "padding: 8px 10px; border-radius: 8px; border: 1px solid #1e293b;"
        )
        layout.addWidget(self._metricas)
        self.setCentralWidget(contenedor)

        barra = QStatusBar(self)
        barra.showMessage("SafeWork AI listo")
        self.setStatusBar(barra)

    def _actualizar_frame(self, imagen) -> None:
        pixmap = QPixmap.fromImage(imagen)
        if pixmap.isNull():
            return
        escalado = pixmap.scaled(
            self._video.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video.setPixmap(escalado)

    def _actualizar_estado(self, estado: str) -> None:
        self._estado.setText(estado)
        color = "#22c55e"

        estado_upper = estado.upper()
        if "CALIBRANDO" in estado_upper:
            color = "#38bdf8"
        elif "AUSENTE" in estado_upper:
            color = "#94a3b8"
        elif "POSTURA" in estado_upper:
            color = "#f97316"
        elif "FATIGA" in estado_upper or "SUENO" in estado_upper or "CABECEO" in estado_upper:
            color = "#ef4444"

        self._estado.setStyleSheet(
            "font-size: 18px; font-weight: 700; background: #111827;"
            f"padding: 10px 14px; border-radius: 10px; color: {color};"
        )
        self.statusBar().showMessage(estado)

    def _actualizar_detalle_estado(self, detalle: str) -> None:
        if detalle:
            self._detalle.setText(detalle)

    def _actualizar_metricas(self, metricas: str) -> None:
        if metricas:
            self._metricas.setText(metricas)

    def _manejar_alerta(self, mensaje: str) -> None:
        self.statusBar().showMessage(mensaje, 5000)
        if not self._voz_habilitada:
            return
        if mensaje == self._ultimo_mensaje_voz:
            return
        self._ultimo_mensaje_voz = mensaje
        self._worker_voz.emitir_mensaje(mensaje)

    def _alternar_voz(self) -> None:
        self._voz_habilitada = not self._voz_habilitada
        self._boton_voz.setText("Voz: Activa" if self._voz_habilitada else "Voz: Silenciada")

    def closeEvent(self, event) -> None: 
        try:
            self._motor.detener()
        except Exception:
            pass
        try:
            self._worker_voz.detener()
        except Exception:
            pass
        super().closeEvent(event)
