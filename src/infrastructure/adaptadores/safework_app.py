from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from .memoria_usuario_json_adapter import MemoriaUsuarioJsonAdapter
from .motor_vision_hibrido_qthread import MotorVisionIA
from .safework_presenter import (
    construir_estado_error,
    construir_estado_sistema,
    construir_metricas_legibles,
    construir_nivel_riesgo,
    construir_registro_ausencia,
    construir_resumen_incidencias,
    perfil_requiere_configuracion,
    perfil_resumen_rol,
    resolver_aviso_visible,
)
from .safework_styles import APP_STYLESHEET, CARD_STYLE, CONTENT_BG_STYLE
from .safework_views import HeaderView, IncidenciasCardView, InsightsPanelView, VideoPanelView
from .safework_widgets import aplicar_sombra_suave
from .voz_qthread_adapter import VozQThreadAdapter


class SafeWorkApp(QMainWindow):
    """Ventana principal: compone las vistas, conecta senales con el presentador
    y orquesta el ciclo de vida (bandeja, dialogo de perfil, hilos de fondo).
    No contiene umbrales, parseo ni formateo — eso vive en safework_presenter.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SafeWork AI")
        self.resize(1140, 720)
        self.setMinimumSize(1080, 720)

        self._ultimo_mensaje_voz = ""
        self._voz_habilitada = True
        self._ultimo_estado_base = "CALIBRANDO"
        self._nivel_riesgo_actual = "OBSERVACION"
        self._ultimo_color_clave: tuple[str, str] | None = None
        self._settings = SafeWorkSettings.from_runtime()
        self._errores_runtime, self._avisos_runtime = self._settings.validar_runtime()
        self._memoria_usuario = MemoriaUsuarioJsonAdapter(
            self._settings.profile_path,
            self._settings.events_path,
            self._settings.incidents_summary_path,
            self._settings.session_report_path,
        )
        self._perfil_usuario = self._memoria_usuario.cargar_perfil_usuario()
        self._exportador_reporte = ReporteExportService(
            self._settings.profile_path,
            self._settings.events_path,
            self._settings.incidents_summary_path,
            self._settings.session_report_path,
            validation_labels_path=self._settings.validation_labels_path,
        )
        self._worker_voz: VozQThreadAdapter | None = None
        self._motor: MotorVisionIA | None = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._saliendo = False
        self._total_ausencias_seg: float = 0.0
        self._conteo_ausencias: int = 0

        self.setStyleSheet(APP_STYLESHEET)
        self._construir_ui()
        if perfil_requiere_configuracion(self._perfil_usuario.get("nombre", "")):
            self._mostrar_dialogo_perfil(obligatorio=True)
        self._configurar_bandeja()
        self._arrancar_componentes()

    # ------------------------------------------------------------------
    # Composicion de la UI: solo instancia vistas y las conecta.
    # ------------------------------------------------------------------
    def _construir_ui(self) -> None:
        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        main_area = QWidget()
        main_area.setObjectName("mainArea")
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nombre = self._perfil_usuario.get("nombre", "Usuario local")
        resumen_rol = perfil_resumen_rol(
            self._perfil_usuario.get("rol", "Usuario"), self._perfil_usuario.get("tipo_usuario", "empleado")
        )
        self._header = HeaderView(self._settings, nombre, resumen_rol)
        self._header.perfil_solicitado.connect(self._mostrar_dialogo_perfil)
        main_layout.addWidget(self._header)

        content = QWidget()
        content.setObjectName("contentArea")
        content.setStyleSheet(CONTENT_BG_STYLE)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)

        self._video_panel = VideoPanelView(self._settings.debug_hud_enabled)
        content_layout.addWidget(self._video_panel, 1)

        lateral_container = QWidget()
        lateral_layout = QVBoxLayout(lateral_container)
        lateral_layout.setContentsMargins(0, 0, 6, 0)
        lateral_layout.setSpacing(12)

        self._insights = InsightsPanelView()
        self._insights.voz_alternada.connect(self._alternar_voz)
        lateral_layout.addWidget(self._insights)

        self._incidencias = IncidenciasCardView()
        self._incidencias.exportar_solicitado.connect(self._exportar_reporte)
        lateral_layout.addWidget(self._incidencias)

        lateral_layout.addStretch(1)

        lateral_scroll = QScrollArea()
        lateral_scroll.setWidgetResizable(True)
        lateral_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lateral_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lateral_scroll.setFixedWidth(390)
        lateral_scroll.setWidget(lateral_container)
        content_layout.addWidget(lateral_scroll)

        main_layout.addWidget(content, 1)
        root_layout.addWidget(main_area, 1)

        barra = QStatusBar(self)
        barra.setObjectName("statusbar")
        barra.showMessage("SafeWork AI listo")
        self.setStatusBar(barra)

    def _mostrar_dialogo_perfil(self, obligatorio: bool = False) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Perfil del usuario")
        dialog.setModal(True)
        dialog.resize(470, 360)
        dialog.setStyleSheet(
            "QDialog { background: #f8fbff; }"
            "QLabel { color: #0f172a; font-size: 12px; }"
            "QLineEdit, QComboBox { background: #ffffff; color: #0f172a; border: 1px solid #dbe4f0; "
            "border-radius: 10px; padding: 9px 10px; min-height: 18px; }"
            "QLineEdit:focus, QComboBox:focus { border: 1px solid #38bdf8; }"
            "QPushButton { background: #0f766e; color: #ffffff; border: none; border-radius: 10px; "
            "padding: 8px 14px; font-size: 12px; font-weight: 700; min-width: 96px; }"
            "QPushButton:hover { background: #115e59; }"
        )
        if obligatorio:
            dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(20, 20, 20, 18)
        root_layout.setSpacing(14)

        titulo = QLabel("Configura tu perfil de uso")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        subtitulo = QLabel(
            "Estos datos se solicitan solo la primera vez. Despues podras editarlos desde el perfil."
        )
        subtitulo.setWordWrap(True)
        subtitulo.setStyleSheet("font-size: 12px; color: #64748b;")
        root_layout.addWidget(titulo)
        root_layout.addWidget(subtitulo)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_card.setStyleSheet(CARD_STYLE)
        aplicar_sombra_suave(form_card, blur=18)
        form = QFormLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        nombre = QLineEdit(self._perfil_usuario.get("nombre", ""))
        identificador = QLineEdit(self._perfil_usuario.get("identificador", ""))
        empresa = QLineEdit(self._perfil_usuario.get("empresa", ""))
        area = QLineEdit(self._perfil_usuario.get("area", ""))
        puesto = QLineEdit(self._perfil_usuario.get("puesto", ""))

        rol = QComboBox()
        rol.addItems(["Usuario", "Administrador", "Supervisor", "Estudiante", "Analista"])
        rol.setCurrentText(self._perfil_usuario.get("rol", "Usuario"))

        tipo = QComboBox()
        tipo.addItems(["empleado", "estudiante", "docente", "visitante"])
        tipo.setCurrentText(self._perfil_usuario.get("tipo_usuario", "empleado"))

        form.addRow("Nombre completo", nombre)
        form.addRow("Identificador", identificador)
        form.addRow("Rol", rol)
        form.addRow("Tipo de usuario", tipo)
        form.addRow("Empresa", empresa)
        form.addRow("Area", area)
        form.addRow("Puesto", puesto)
        root_layout.addWidget(form_card)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save)
        if not obligatorio:
            buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
            boton_cancelar = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if boton_cancelar is not None:
                boton_cancelar.setStyleSheet(
                    "QPushButton { background: #ffffff; color: #334155; border: 1px solid #cbd5e1; "
                    "border-radius: 10px; padding: 8px 14px; font-size: 12px; font-weight: 700; min-width: 96px; }"
                    "QPushButton:hover { background: #f8fafc; }"
                )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root_layout.addWidget(buttons)

        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            if obligatorio:
                self.close()
            return

        self._perfil_usuario = self._memoria_usuario.guardar_perfil_usuario(
            {
                "nombre": nombre.text(),
                "identificador": identificador.text(),
                "rol": rol.currentText(),
                "tipo_usuario": tipo.currentText(),
                "empresa": empresa.text(),
                "area": area.text(),
                "puesto": puesto.text(),
            }
        )
        self._header.actualizar_perfil(
            self._perfil_usuario.get("nombre", "Usuario local"),
            perfil_resumen_rol(
                self._perfil_usuario.get("rol", "Usuario"), self._perfil_usuario.get("tipo_usuario", "empleado")
            ),
        )

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

    # ------------------------------------------------------------------
    # Arranque y wiring de senales del motor de vision / voz.
    # ------------------------------------------------------------------
    def _arrancar_componentes(self) -> None:
        if self._errores_runtime:
            vm = construir_estado_error("CONFIGURACION INCOMPLETA", "Faltan recursos obligatorios")
            self._insights.actualizar_estado(vm)
            self._insights.actualizar_detalle(" | ".join(self._errores_runtime))
            self._header.actualizar_subtitulo("No fue posible iniciar el motor de vision.")
            self.statusBar().showMessage("Configuracion incompleta: revisa los modelos requeridos.")
            return

        if self._avisos_runtime:
            aviso_visible = resolver_aviso_visible(self._avisos_runtime)
            self._header.actualizar_subtitulo(aviso_visible)
            self.statusBar().showMessage(aviso_visible, 12000)

        self._worker_voz = VozQThreadAdapter(self)
        self._worker_voz.error_senal.connect(self._manejar_error_voz)
        self._worker_voz.start()

        self._motor = MotorVisionIA(parent=self)
        self._motor.senal_frame_actualizado.connect(self._video_panel.actualizar_frame)
        self._motor.senal_alerta_emitida.connect(self._manejar_alerta)
        self._motor.senal_estado_sistema.connect(self._actualizar_estado)
        self._motor.senal_detalle_estado.connect(self._insights.actualizar_detalle)
        self._motor.senal_metricas.connect(self._actualizar_metricas)
        self._motor.senal_resumen_incidencias.connect(self._actualizar_panel_incidencias)
        self._motor.senal_nivel_riesgo.connect(self._actualizar_nivel_riesgo)
        self._motor.senal_bloqueo_requerido.connect(self._manejar_bloqueo_critico)
        self._motor.senal_modo_operacion.connect(self._actualizar_modo_operacion)
        self._motor.senal_error_ocurrido.connect(self._manejar_error_motor)
        self._motor.senal_ausencia_resuelta.connect(self._registrar_ausencia)
        if self._video_panel.tiene_hud():
            self._motor.senal_diagnostico.connect(self._video_panel.actualizar_diagnostico)
        self._motor.start()

    # ------------------------------------------------------------------
    # Slots: cada uno llama al presentador puro y empuja el resultado a
    # la(s) vista(s) correspondiente(s). Cero umbrales/parseo aqui.
    # ------------------------------------------------------------------
    def _manejar_error_motor(self, mensaje_error: str) -> None:
        vm = construir_estado_error("ERROR DE SENSOR", "Error en camara o procesamiento de IA")
        self._insights.actualizar_estado(vm)
        self._insights.actualizar_detalle(mensaje_error)
        self._video_panel.mostrar_error(mensaje_error)
        self._header.actualizar_color_estado("#ef4444")
        self.statusBar().showMessage(f"Error detectado: {mensaje_error}", 15000)

    def _manejar_error_voz(self, mensaje_error: str) -> None:
        self._voz_habilitada = False
        self._insights.deshabilitar_voz()
        self.statusBar().showMessage(f"Asistente de voz inactivo: {mensaje_error}", 8000)

    def _alternar_voz(self) -> None:
        if self._worker_voz is None:
            return
        self._voz_habilitada = not self._voz_habilitada
        if not self._voz_habilitada:
            self._worker_voz.limpiar_cola()
        self._insights.actualizar_estado_voz(self._voz_habilitada)
        estado = "Activo" if self._voz_habilitada else "Silenciado"
        self.statusBar().showMessage(f"Asistente de voz: {estado}", 4000)

    def _registrar_ausencia(self, duracion_seg: float) -> None:
        vm = construir_registro_ausencia(duracion_seg, self._total_ausencias_seg, self._conteo_ausencias)
        self._total_ausencias_seg = vm.total_acumulado_seg
        self._conteo_ausencias = vm.conteo_acumulado
        self._insights.actualizar_ausencia(vm)
        self.statusBar().showMessage(vm.mensaje_status_bar, 6000)

    def _actualizar_estado(self, estado: str) -> None:
        vm = construir_estado_sistema(estado)
        self._ultimo_estado_base = vm.estado_base
        colores = (vm.color, vm.color_fondo)
        forzar_estilo = colores != self._ultimo_color_clave
        self._insights.actualizar_estado(vm, forzar_estilo=forzar_estilo)
        if forzar_estilo:
            self._ultimo_color_clave = colores
        self.statusBar().showMessage(estado)

    def _actualizar_modo_operacion(self, mensaje: str) -> None:
        if not mensaje:
            return
        self._header.actualizar_subtitulo(mensaje)
        self._video_panel.actualizar_modo(mensaje)
        self.statusBar().showMessage(mensaje, 10000)

    def _actualizar_metricas(self, metricas: str) -> None:
        if not metricas:
            return
        vm = construir_metricas_legibles(metricas)
        self._video_panel.actualizar_metricas(vm)
        self._incidencias.actualizar_indice_global(vm.indice_global, vm.detalle_indice_global, vm.tendencia_indice)
        self._incidencias.actualizar_riesgos(vm.riesgo_postura, vm.riesgo_pantalla, vm.riesgo_fatiga)
        self._insights.actualizar_metricas_resumen(vm.resumen_texto)

    def _actualizar_nivel_riesgo(self, nivel: str) -> None:
        self._nivel_riesgo_actual = nivel
        vm = construir_nivel_riesgo(nivel)
        self._video_panel.aplicar_glow_riesgo(vm.color_glow_hex)
        self._insights.actualizar_estado_auxiliar(vm.texto_auxiliar)
        if vm.ocultar_banner:
            self._video_panel.ocultar_banner_bloqueo()

    def _manejar_bloqueo_critico(self, mensaje: str) -> None:
        self._video_panel.mostrar_banner_bloqueo(mensaje)
        self.statusBar().showMessage(f"Riesgo critico: {mensaje}", 7000)

    def _actualizar_panel_incidencias(self, resumen: object) -> None:
        vm = construir_resumen_incidencias(resumen)
        if vm is None:
            return
        self._incidencias.actualizar_resumen(vm)
        self._insights.actualizar_ultima_incidencia(
            vm.mostrar_ultima_incidencia, vm.ultima_incidencia_texto, vm.log_resumen_texto
        )

    def _manejar_alerta(self, mensaje: str) -> None:
        self.statusBar().showMessage(mensaje, 5000)
        if not self._voz_habilitada or mensaje == self._ultimo_mensaje_voz:
            return
        self._ultimo_mensaje_voz = mensaje
        if self._worker_voz is not None:
            self._worker_voz.emitir_mensaje(mensaje)

    def _exportar_reporte(self) -> None:
        try:
            if self._motor is not None:
                self._motor.guardar_reporte_actual()
            reporte = self._exportador_reporte.exportar()
            carpeta = reporte.pdf_path.parent
            self.statusBar().showMessage(f"Reportes PDF guardados en: {carpeta}", 15000)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(reporte.pdf_path)))
        except Exception as exc:
            self.statusBar().showMessage(f"No se pudo exportar el reporte: {exc}", 10000)

    # ------------------------------------------------------------------
    # Ciclo de vida de ventana: bandeja, minimizado, cierre.
    # ------------------------------------------------------------------
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
        """Minimiza a la bandeja del sistema y pausa el renderizado de video."""
        if event.type() == QEvent.Type.WindowStateChange:
            if (
                self.isMinimized()
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
            if self._motor is not None:
                is_minimized_or_hidden = self.isMinimized() or self.isHidden()
                self._motor.set_ui_visible(not is_minimized_or_hidden)
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
        QApplication.instance().quit()
