from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ...application.servicios import ReporteExportService
from ..config import SafeWorkSettings
from .motor_vision_hibrido_qthread import MotorVisionIA
from .voz_qthread_adapter import VozQThreadAdapter


class SafeWorkApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SafeWork AI")
        self.resize(1040, 680)
        self.setMinimumSize(940, 600)

        self._ultimo_mensaje_voz = ""
        self._voz_habilitada = True
        self._ultimo_estado_base = "CALIBRANDO"
        self._nivel_riesgo_actual = "OBSERVACION"
        self._settings = SafeWorkSettings.from_runtime()
        self._errores_runtime, self._avisos_runtime = self._settings.validar_runtime()
        self._exportador_reporte = ReporteExportService(
            self._settings.profile_path,
            self._settings.events_path,
            self._settings.incidents_summary_path,
            self._settings.session_report_path,
            validation_labels_path=self._settings.validation_labels_path,
        )
        self._worker_voz = None
        self._motor = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._saliendo = False

        self._construir_ui()
        self._configurar_bandeja()
        self._arrancar_componentes()

    def _arrancar_componentes(self) -> None:
        if self._errores_runtime:
            self._estado.setText("CONFIGURACION INCOMPLETA")
            self._estado.setStyleSheet(
                "font-size: 16px; font-weight: 700; background: #0b1220;"
                "padding: 8px 12px; border-radius: 8px; color: #ef4444;"
            )
            self._estado_aux.setText("Faltan recursos obligatorios para iniciar el monitoreo")
            self._detalle.setText(" | ".join(self._errores_runtime))
            self._subtitulo.setText("No fue posible iniciar el motor de vision.")
            self.statusBar().showMessage("Configuracion incompleta: revisa los modelos requeridos.")
            self._boton_voz.setEnabled(False)
            return

        if self._avisos_runtime:
            self._subtitulo.setText(" | ".join(self._avisos_runtime))
            self.statusBar().showMessage(self._avisos_runtime[0], 12000)

        self._worker_voz = VozQThreadAdapter(self)
        self._worker_voz.error_senal.connect(self._manejar_error_voz)
        self._worker_voz.start()

        self._motor = MotorVisionIA(parent=self)
        self._motor.senal_frame_actualizado.connect(self._actualizar_frame)
        self._motor.senal_alerta_emitida.connect(self._manejar_alerta)
        self._motor.senal_estado_sistema.connect(self._actualizar_estado)
        self._motor.senal_detalle_estado.connect(self._actualizar_detalle_estado)
        self._motor.senal_metricas.connect(self._actualizar_metricas)
        self._motor.senal_resumen_incidencias.connect(self._actualizar_panel_incidencias)
        self._motor.senal_nivel_riesgo.connect(self._actualizar_nivel_riesgo)
        self._motor.senal_bloqueo_requerido.connect(self._manejar_bloqueo_critico)
        self._motor.senal_modo_operacion.connect(self._actualizar_modo_operacion)
        self._motor.senal_error_ocurrido.connect(self._manejar_error_motor)
        self._motor.start()

    def _manejar_error_motor(self, mensaje_error: str) -> None:
        self._estado.setText("ERROR DE SENSOR")
        self._estado.setStyleSheet(
            "font-size: 16px; font-weight: 700; background: #0b1220;"
            "padding: 8px 12px; border-radius: 8px; color: #ef4444;"
        )
        self._estado_aux.setText("Error en cámara o procesamiento de IA")
        self._detalle.setText(mensaje_error)
        self._video.setText(f"SISTEMA EN PAUSA\n\n{mensaje_error}\n\nPor favor, verifica la conexión de tu cámara.")
        self._video.setStyleSheet(
            "background-color: #020617; border: 2px solid #ef4444; border-radius: 6px; color: #fee2e2; font-size: 14px; font-weight: bold; qproperty-alignment: 'AlignCenter';"
        )
        self.statusBar().showMessage(f"Error detectado: {mensaje_error}", 15000)

    def _manejar_error_voz(self, mensaje_error: str) -> None:
        self._voz_habilitada = False
        self._boton_voz.setText("Voz: No disponible")
        self._boton_voz.setEnabled(False)
        self.statusBar().showMessage(f"Asistente de voz inactivo: {mensaje_error}", 8000)

    def _construir_ui(self) -> None:
        self.setStyleSheet(
            """
            * {
                font-family: 'Segoe UI', sans-serif;
            }
            QMainWindow {
                background: #111827;
            }
            QWidget {
                color: #e2e8f0;
                background: transparent;
            }
            QFrame#card {
                background: #0f172a;
                border: 1px solid #243044;
                border-radius: 8px;
            }
            QLabel#title {
                font-size: 24px;
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
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #111827;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
            }
            QPushButton {
                background: #14532d;
                color: #dcfce7;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid #22c55e;
                border-radius: 8px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #166534;
            }
            """
        )

        contenedor = QWidget(self)
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        header = QLabel("SAFEWORK AI")
        header.setObjectName("title")
        layout.addWidget(header)

        self._subtitulo = QLabel("Monitoreo hibrido de postura y fatiga en tiempo real")
        self._subtitulo.setObjectName("subtitle")
        layout.addWidget(self._subtitulo)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(12)

        video_card = self._crear_card()
        video_layout = QVBoxLayout(video_card)
        video_layout.setContentsMargins(10, 10, 10, 10)

        self._video = QLabel("Inicializando camara y modelos...")
        self._video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video.setMinimumSize(640, 420)
        self._video.setStyleSheet(
            "background-color: #020617; border: 1px solid #334155; border-radius: 6px;"
        )
        video_layout.addWidget(self._video, 1)

        self._bloqueo_banner = QLabel("RIESGO CRITICO: realiza una pausa activa antes de continuar.")
        self._bloqueo_banner.setWordWrap(True)
        self._bloqueo_banner.setVisible(False)
        self._bloqueo_banner.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #fee2e2; background: #7f1d1d; "
            "padding: 10px 12px; border-radius: 8px; border: 1px solid #ef4444;"
        )
        video_layout.addWidget(self._bloqueo_banner)
        cuerpo.addWidget(video_card, 1)

        lateral_content = QWidget()
        lateral = QVBoxLayout(lateral_content)
        lateral.setSpacing(12)
        lateral.setContentsMargins(0, 0, 0, 0)

        estado_card = self._crear_card()
        estado_layout = QVBoxLayout(estado_card)
        estado_layout.setContentsMargins(12, 12, 12, 12)
        estado_layout.setSpacing(10)

        estado_title = QLabel("Estado actual")
        estado_title.setObjectName("sectionTitle")
        estado_layout.addWidget(estado_title)

        self._estado = QLabel("CALIBRANDO")
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #38bdf8;"
        )
        estado_layout.addWidget(self._estado)

        self._estado_aux = QLabel("Preparando monitoreo")
        self._estado_aux.setWordWrap(True)
        self._estado_aux.setStyleSheet("font-size: 11px; color: #94a3b8;")
        estado_layout.addWidget(self._estado_aux)

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
        metricas_layout.setSpacing(10)

        metricas_title = QLabel("Metricas")
        metricas_title.setObjectName("sectionTitle")
        metricas_layout.addWidget(metricas_title)

        self._metricas_resumen = QLabel("Lectura corporal en preparacion.")
        self._metricas_resumen.setWordWrap(True)
        self._metricas_resumen.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        metricas_layout.addWidget(self._metricas_resumen)

        self._linea_ojos = self._crear_linea_simple("Ojos: Sin lectura")
        self._linea_postura = self._crear_linea_simple("Postura: Sin lectura")
        self._linea_distancia = self._crear_linea_simple("Distancia: Sin lectura")
        self._linea_energia = self._crear_linea_simple("Energia: Sin lectura")
        metricas_layout.addWidget(self._linea_ojos)
        metricas_layout.addWidget(self._linea_postura)
        metricas_layout.addWidget(self._linea_distancia)
        metricas_layout.addWidget(self._linea_energia)
        lateral.addWidget(metricas_card)

        incidencias_card = self._crear_card()
        incidencias_layout = QVBoxLayout(incidencias_card)
        incidencias_layout.setContentsMargins(12, 12, 12, 12)
        incidencias_layout.setSpacing(10)

        incidencias_title = QLabel("Incidencias")
        incidencias_title.setObjectName("sectionTitle")
        incidencias_layout.addWidget(incidencias_title)

        self._incidencias_totales = self._crear_linea_simple("Total de incidencias: --")
        self._incidencias_postura = self._crear_linea_simple("Incidencias por postura: --")
        self._incidencias_pantalla = self._crear_linea_simple("Incidencias por cercania: --")
        self._incidencias_fatiga = self._crear_linea_simple("Incidencias por fatiga: --")
        self._historial_hoy = self._crear_linea_simple("Hoy: --")
        self._historial_semana = self._crear_linea_simple("Ultimos 7 dias: --")
        self._historial_mes = self._crear_linea_simple("Ultimos 30 dias: --")
        incidencias_layout.addWidget(self._incidencias_totales)
        incidencias_layout.addWidget(self._incidencias_postura)
        incidencias_layout.addWidget(self._incidencias_pantalla)
        incidencias_layout.addWidget(self._incidencias_fatiga)
        incidencias_layout.addWidget(self._historial_hoy)
        incidencias_layout.addWidget(self._historial_semana)
        incidencias_layout.addWidget(self._historial_mes)

        self._ultima_incidencia = QLabel("Aun no se registran incidencias.")
        self._ultima_incidencia.setWordWrap(True)
        self._ultima_incidencia.setMinimumHeight(96)
        self._ultima_incidencia.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._ultima_incidencia.setStyleSheet(
            "font-size: 12px; color: #e2e8f0; background: #0b1220; "
            "padding: 10px; border-radius: 10px; border: 1px solid #1f2937;"
        )
        incidencias_layout.addWidget(self._ultima_incidencia)

        self._log_resumen = QLabel("El historial mostrara la ultima incidencia validada.")
        self._log_resumen.setWordWrap(True)
        self._log_resumen.setStyleSheet("font-size: 11px; color: #94a3b8;")
        incidencias_layout.addWidget(self._log_resumen)

        self._boton_exportar = QPushButton("Exportar reporte")
        self._boton_exportar.clicked.connect(self._exportar_reporte)
        incidencias_layout.addWidget(self._boton_exportar)
        lateral.addWidget(incidencias_card)
        lateral.addStretch(1)

        lateral_scroll = QScrollArea()
        lateral_scroll.setWidgetResizable(True)
        lateral_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lateral_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lateral_scroll.setFixedWidth(360)
        lateral_scroll.setWidget(lateral_content)
        cuerpo.addWidget(lateral_scroll, 0)
        layout.addLayout(cuerpo, 1)
        self.setCentralWidget(contenedor)

        barra = QStatusBar(self)
        barra.showMessage("SafeWork AI listo")
        self.setStatusBar(barra)

    def _configurar_bandeja(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = self._settings.assets_dir / "safework_icon.ico"
        icon = QIcon(str(icon_path)) if icon_path.exists() else self.windowIcon()
        self.setWindowIcon(icon)

        tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)

        restaurar = QAction("Restaurar", self)
        restaurar.triggered.connect(self._restaurar_desde_bandeja)
        menu.addAction(restaurar)

        salir = QAction("Salir", self)
        salir.triggered.connect(self._salir_desde_bandeja)
        menu.addAction(salir)

        tray.setContextMenu(menu)
        tray.setToolTip("SafeWork AI")
        tray.activated.connect(self._manejar_activacion_bandeja)
        tray.show()
        self._tray_icon = tray

    @staticmethod
    def _crear_card() -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        return card

    @staticmethod
    def _crear_linea_simple(texto: str) -> QLabel:
        label = QLabel(texto)
        label.setWordWrap(True)
        label.setStyleSheet(
            "font-size: 12px; color: #e2e8f0; background: #0b1220; "
            "padding: 8px 10px; border-radius: 10px; border: 1px solid #1f2937;"
        )
        return label

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
        estado_base = estado.replace(" - Cooldown activo", "")
        self._ultimo_estado_base = estado_base
        self._estado.setText(estado_base)
        color = "#22c55e"

        estado_upper = estado_base.upper()
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
            "font-size: 16px; font-weight: 700; background: #0b1220;"
            f"padding: 8px 12px; border-radius: 8px; color: {color};"
        )
        self._estado_aux.setText("Pausa temporal entre alertas" if "Cooldown activo" in estado else "Monitoreo activo")
        self.statusBar().showMessage(estado)

    def _actualizar_detalle_estado(self, detalle: str) -> None:
        if detalle:
            self._detalle.setText(detalle)

    def _actualizar_modo_operacion(self, mensaje: str) -> None:
        if not mensaje:
            return
        self._subtitulo.setText(mensaje)
        self.statusBar().showMessage(mensaje, 10000)

    def _actualizar_metricas(self, metricas: str) -> None:
        if metricas:
            self._aplicar_metricas_legibles(metricas)

    def _actualizar_nivel_riesgo(self, nivel: str) -> None:
        self._nivel_riesgo_actual = nivel
        estilos = {
            "OBSERVACION": ("#facc15", "Observacion preventiva"),
            "RIESGO_LEVE": ("#f59e0b", "Riesgo leve"),
            "RIESGO_CONFIRMADO": ("#f97316", "Riesgo confirmado"),
            "RIESGO_CRITICO": ("#ef4444", "Riesgo critico"),
        }
        color, texto = estilos.get(nivel, ("#334155", "Monitoreo activo"))
        self._video.setStyleSheet(
            "background-color: #020617; "
            f"border: 2px solid {color}; "
            "border-radius: 6px;"
        )
        self._estado_aux.setText(texto)
        if nivel != "RIESGO_CRITICO":
            self._bloqueo_banner.setVisible(False)

    def _manejar_bloqueo_critico(self, mensaje: str) -> None:
        self._bloqueo_banner.setText(f"RIESGO CRITICO: {mensaje}")
        self._bloqueo_banner.setVisible(True)
        self.statusBar().showMessage(f"Riesgo critico: {mensaje}", 7000)

    def _actualizar_panel_incidencias(self, resumen: object) -> None:
        if not isinstance(resumen, dict):
            return

        total = int(resumen.get("total_incidencias", 0) or 0)
        por_categoria = resumen.get("por_categoria", {})
        if not isinstance(por_categoria, dict):
            por_categoria = {}

        self._incidencias_totales.setText(f"Total de incidencias: {total}")
        self._incidencias_postura.setText(f"Incidencias por postura: {int(por_categoria.get('ergonomia', 0) or 0)}")
        self._incidencias_pantalla.setText(f"Incidencias por cercania: {int(por_categoria.get('proximidad', 0) or 0)}")
        self._incidencias_fatiga.setText(f"Incidencias por fatiga: {int(por_categoria.get('somnolencia', 0) or 0)}")
        metricas = resumen.get("metricas_agregadas", {})
        periodos = metricas.get("periodos", {}) if isinstance(metricas, dict) else {}
        if not isinstance(periodos, dict):
            periodos = {}
        self._historial_hoy.setText(f"Hoy: {int(periodos.get('hoy', 0) or 0)}")
        self._historial_semana.setText(f"Ultimos 7 dias: {int(periodos.get('ultimos_7_dias', 0) or 0)}")
        self._historial_mes.setText(f"Ultimos 30 dias: {int(periodos.get('ultimos_30_dias', 0) or 0)}")

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
        self._linea_ojos.setText(f"Ojos: {ojos_texto}")
        self._linea_postura.setText(f"Postura: {postura_texto}")
        self._linea_distancia.setText(f"Distancia: {distancia_texto}")
        self._linea_energia.setText(f"Energia: {energia_texto}")

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
        if self._worker_voz is not None:
            self._worker_voz.emitir_mensaje(mensaje)

    def _alternar_voz(self) -> None:
        if self._worker_voz is None:
            return
        self._voz_habilitada = not self._voz_habilitada
        self._boton_voz.setText("Voz: Activa" if self._voz_habilitada else "Voz: Silenciada")

    def _exportar_reporte(self) -> None:
        try:
            if self._motor is not None:
                self._motor.guardar_reporte_actual()
            reporte = self._exportador_reporte.exportar()
            self.statusBar().showMessage(f"Reporte exportado: {reporte.html_path}", 10000)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(reporte.html_path)))
        except Exception as exc:
            self.statusBar().showMessage(f"No se pudo exportar el reporte: {exc}", 10000)

    def _manejar_activacion_bandeja(self, motivo: QSystemTrayIcon.ActivationReason) -> None:
        if motivo in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self._restaurar_desde_bandeja()

    def _restaurar_desde_bandeja(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _salir_desde_bandeja(self) -> None:
        self._saliendo = True
        self.close()

    def changeEvent(self, event: QEvent) -> None:
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self._tray_icon is not None
            and self._tray_icon.isVisible()
        ):
            self.hide()
            self._tray_icon.showMessage(
                "SafeWork AI",
                "La aplicacion fue minimizada a la bandeja del sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._tray_icon is not None and self._tray_icon.isVisible() and not self._saliendo:
            self.hide()
            self._tray_icon.showMessage(
                "SafeWork AI",
                "La aplicacion sigue activa en la bandeja del sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
            event.ignore()
            return
        try:
            if self._motor is not None:
                self._motor.guardar_reporte_actual()
        except Exception:
            pass
        try:
            if self._motor is not None:
                self._motor.detener()
        except Exception:
            pass
        try:
            if self._worker_voz is not None:
                self._worker_voz.detener()
        except Exception:
            pass
        if self._tray_icon is not None:
            self._tray_icon.hide()
        super().closeEvent(event)
