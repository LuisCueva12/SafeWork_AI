from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
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
        self.resize(920, 600)
        self.setMinimumSize(860, 560)

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
        self._motor.senal_resumen_incidencias.connect(self._actualizar_panel_incidencias)
        self._motor.start()

        self._construir_ui()

    def _construir_ui(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0f172a;
                color: #e2e8f0;
            }
            QFrame#card {
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 16px;
            }
            QFrame#metricCard {
                background: #0b1220;
                border: 1px solid #1f2937;
                border-radius: 12px;
            }
            QFrame#metricRow {
                background: #0b1220;
                border: 1px solid #1f2937;
                border-radius: 10px;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: 700;
                color: #f8fafc;
            }
            QLabel#subtitle {
                font-size: 12px;
                color: #94a3b8;
            }
            QLabel#sectionTitle {
                font-size: 12px;
                font-weight: 600;
                color: #93c5fd;
                text-transform: uppercase;
            }
            QLabel#metricName {
                font-size: 11px;
                font-weight: 600;
                color: #93c5fd;
            }
            QLabel#metricValue {
                font-size: 12px;
                color: #e2e8f0;
            }
            QPushButton {
                background: #172554;
                color: #dbeafe;
                border: 1px solid #2563eb;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            """
        )

        contenedor = QWidget(self)
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QLabel("SAFEWORK AI")
        header.setObjectName("title")
        layout.addWidget(header)

        self._subtitulo = QLabel("Monitoreo hibrido de postura y fatiga en tiempo real")
        self._subtitulo.setObjectName("subtitle")
        layout.addWidget(self._subtitulo)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(10)

        video_card = self._crear_card()
        video_layout = QVBoxLayout(video_card)
        video_layout.setContentsMargins(10, 10, 10, 10)

        self._video = QLabel("Inicializando camara y modelos...")
        self._video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video.setMinimumSize(600, 360)
        self._video.setStyleSheet(
            "background-color: #020617; border: 1px solid #1e293b; border-radius: 12px;"
        )
        video_layout.addWidget(self._video, 1)
        cuerpo.addWidget(video_card, 1)

        lateral = QVBoxLayout()
        lateral.setSpacing(10)
        lateral.setContentsMargins(0, 0, 0, 0)
        lateral.setStretch(0, 0)
        lateral.setStretch(1, 0)
        lateral.setStretch(2, 1)

        estado_card = self._crear_card()
        estado_layout = QVBoxLayout(estado_card)
        estado_layout.setContentsMargins(12, 12, 12, 12)
        estado_layout.setSpacing(8)

        estado_title = QLabel("Estado actual")
        estado_title.setObjectName("sectionTitle")
        estado_layout.addWidget(estado_title)

        self._estado = QLabel("CALIBRANDO")
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: #38bdf8;"
        )
        estado_layout.addWidget(self._estado)

        self._detalle = QLabel("Esperando perfil basal del usuario...")
        self._detalle.setWordWrap(True)
        self._detalle.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        estado_layout.addWidget(self._detalle)

        self._boton_voz = QPushButton("Voz: Activa")
        self._boton_voz.clicked.connect(self._alternar_voz)
        estado_layout.addWidget(self._boton_voz, 0, Qt.AlignmentFlag.AlignLeft)
        lateral.addWidget(estado_card)

        metricas_card = self._crear_card()
        metricas_layout = QVBoxLayout(metricas_card)
        metricas_layout.setContentsMargins(12, 12, 12, 12)
        metricas_layout.setSpacing(8)

        metricas_title = QLabel("Metricas")
        metricas_title.setObjectName("sectionTitle")
        metricas_layout.addWidget(metricas_title)

        self._metricas_resumen = QLabel("Lectura corporal en preparacion.")
        self._metricas_resumen.setWordWrap(True)
        self._metricas_resumen.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        metricas_layout.addWidget(self._metricas_resumen)

        self._card_ojos = self._crear_resumen_metrica("Ojos", "Sin lectura")
        self._card_postura = self._crear_resumen_metrica("Postura", "Sin lectura")
        self._card_distancia = self._crear_resumen_metrica("Distancia", "Sin lectura")
        self._card_energia = self._crear_resumen_metrica("Energia", "Sin lectura")
        metricas_layout.addWidget(self._card_ojos)
        metricas_layout.addWidget(self._card_postura)
        metricas_layout.addWidget(self._card_distancia)
        metricas_layout.addWidget(self._card_energia)
        lateral.addWidget(metricas_card)

        incidencias_card = self._crear_card()
        incidencias_layout = QVBoxLayout(incidencias_card)
        incidencias_layout.setContentsMargins(12, 12, 12, 12)
        incidencias_layout.setSpacing(8)

        incidencias_title = QLabel("Incidencias")
        incidencias_title.setObjectName("sectionTitle")
        incidencias_layout.addWidget(incidencias_title)

        self._chip_total = self._crear_chip("Total de incidencias", "--")
        self._chip_ergonomia = self._crear_chip("Postura", "--")
        self._chip_proximidad = self._crear_chip("Cercania a pantalla", "--")
        self._chip_somnolencia = self._crear_chip("Fatiga o somnolencia", "--")
        incidencias_layout.addWidget(self._chip_total)
        incidencias_layout.addWidget(self._chip_ergonomia)
        incidencias_layout.addWidget(self._chip_proximidad)
        incidencias_layout.addWidget(self._chip_somnolencia)

        self._ultima_incidencia = QLabel("Aun no se registran incidencias.")
        self._ultima_incidencia.setWordWrap(True)
        self._ultima_incidencia.setMinimumHeight(74)
        self._ultima_incidencia.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._ultima_incidencia.setStyleSheet(
            "font-size: 12px; color: #cbd5e1; background: #0b1220; "
            "padding: 10px; border-radius: 10px; border: 1px solid #1f2937;"
        )
        incidencias_layout.addWidget(self._ultima_incidencia)

        self._log_resumen = QLabel("El historial mostrara la ultima incidencia validada.")
        self._log_resumen.setWordWrap(True)
        self._log_resumen.setStyleSheet("font-size: 11px; color: #94a3b8;")
        incidencias_layout.addWidget(self._log_resumen)
        lateral.addWidget(incidencias_card, 1)

        lateral_wrap = QWidget()
        lateral_wrap.setFixedWidth(332)
        lateral_wrap.setLayout(lateral)
        cuerpo.addWidget(lateral_wrap, 0)
        layout.addLayout(cuerpo, 1)
        self.setCentralWidget(contenedor)

        barra = QStatusBar(self)
        barra.showMessage("SafeWork AI listo")
        self.setStatusBar(barra)

    @staticmethod
    def _crear_card() -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        return card

    @staticmethod
    def _crear_chip(titulo: str, valor: str) -> QLabel:
        chip = QLabel(f"{titulo}: {valor}")
        chip.setWordWrap(True)
        chip.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        chip.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #e2e8f0; background: #0b1220; "
            "border: 1px solid #1f2937; border-radius: 10px; padding: 10px;"
        )
        chip.setMinimumHeight(40)
        return chip

    @staticmethod
    def _crear_resumen_metrica(titulo: str, valor: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricRow")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        title = QLabel(titulo)
        title.setObjectName("metricName")
        title.setFixedWidth(72)
        value = QLabel(valor)
        value.setObjectName("metricValue")
        value.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(value, 1)
        card._value_label = value
        return card

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
        elif "CERCANIA" in estado_upper:
            color = "#f59e0b"
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
            self._aplicar_metricas_legibles(metricas)

    def _actualizar_panel_incidencias(self, resumen: object) -> None:
        if not isinstance(resumen, dict):
            return

        total = int(resumen.get("total_incidencias", 0) or 0)
        por_categoria = resumen.get("por_categoria", {})
        if not isinstance(por_categoria, dict):
            por_categoria = {}

        self._chip_total.setText(f"Total de incidencias: {total}")
        self._chip_ergonomia.setText(f"Postura: {int(por_categoria.get('ergonomia', 0) or 0)}")
        self._chip_proximidad.setText(f"Cercania a pantalla: {int(por_categoria.get('proximidad', 0) or 0)}")
        self._chip_somnolencia.setText(f"Fatiga o somnolencia: {int(por_categoria.get('somnolencia', 0) or 0)}")

        ultimas = resumen.get("ultimas_incidencias", [])
        if isinstance(ultimas, list) and ultimas:
            ultima = ultimas[0] if isinstance(ultimas[0], dict) else {}
            estado = str(ultima.get("estado", "Incidencia"))
            severidad = str(ultima.get("severidad", "informativa")).upper()
            descripcion = str(ultima.get("descripcion", "Sin descripcion"))
            timestamp = str(ultima.get("timestamp", ""))
            self._ultima_incidencia.setText(f"Ultima incidencia: {estado}\n{descripcion}")
            self._log_resumen.setText(f"Ultimo registro: {timestamp}\nPrioridad: {severidad}")
        else:
            self._ultima_incidencia.setText("Aun no se registran incidencias.")
            self._log_resumen.setText("El historial mostrara la ultima incidencia validada.")

    def _aplicar_metricas_legibles(self, metricas: str) -> None:
        valores = self._parsear_metricas(metricas)
        ear = valores.get("EAR", 0.0)
        mar = valores.get("MAR", 0.0)
        cuello = valores.get("Cuello", 0.0)
        lateral = valores.get("Lateral", 0.0)
        proximidad = valores.get("Prox", 0.0)

        ojos_texto = "Ojos relajados"
        if ear < 0.22:
            ojos_texto = "Ojos muy cerrados"
        elif ear < 0.28:
            ojos_texto = "Ojos cansados"

        energia_texto = "Atencion estable"
        if mar > 0.45:
            energia_texto = "Posible bostezo"
        elif mar > 0.20:
            energia_texto = "Atencion variable"

        postura_texto = "Postura centrada"
        if cuello >= 28.0:
            postura_texto = "Cabeza muy inclinada"
        elif cuello >= 14.0 or lateral >= 7.5:
            postura_texto = "Postura por corregir"

        distancia_texto = "Distancia adecuada"
        if proximidad >= 0.72:
            distancia_texto = "Muy cerca a la pantalla"
        elif proximidad >= 0.35:
            distancia_texto = "Acercamiento leve"

        self._metricas_resumen.setText(
            "Resumen rapido: "
            f"{ojos_texto.lower()}, {postura_texto.lower()} y {distancia_texto.lower()}."
        )
        self._card_ojos._value_label.setText(ojos_texto)
        self._card_postura._value_label.setText(postura_texto)
        self._card_distancia._value_label.setText(distancia_texto)
        self._card_energia._value_label.setText(energia_texto)

    @staticmethod
    def _parsear_metricas(metricas: str) -> dict[str, float]:
        valores: dict[str, float] = {}
        for bloque in metricas.split("|"):
            partes = bloque.strip().split(" ", 1)
            if len(partes) != 2:
                continue
            clave, valor = partes
            try:
                valores[clave] = float(valor)
            except ValueError:
                continue
        return valores

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
