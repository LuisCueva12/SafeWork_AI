from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QPixmap
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ...application.servicios import ReporteExportService
from ..config import SafeWorkSettings
from .memoria_usuario_json_adapter import MemoriaUsuarioJsonAdapter
from .motor_vision_hibrido_qthread import MotorVisionIA
from .safework_styles import (
    APP_STYLESHEET,
    BANNER_CRITICAL,
    CARD_STYLE,
    CONTENT_BG_STYLE,
    HEADER_CHIP_STYLE,
    HEADER_STYLE,
    LEVEL_COLORS,
    NAV_BUTTON_ACTIVE,
    NAV_BUTTON_BASE,
    SIDEBAR_STYLE,
    STAT_LABEL_STYLE,
    STAT_VALUE_STYLE,
    STATUS_COLORS,
    VIDEO_FEED_ERROR,
    VIDEO_FEED_IDLE,
)
from .safework_widgets import CircularMetricWidget, MiniTrendWidget
from .voz_qthread_adapter import VozQThreadAdapter


class SafeWorkApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SafeWork AI")
        self.resize(1140, 720)
        self.setMinimumSize(1080, 720)

        self._ultimo_mensaje_voz = ""
        self._voz_habilitada = True
        self._ultimo_estado_base = "CALIBRANDO"
        self._nivel_riesgo_actual = "OBSERVACION"
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
        self._worker_voz = None
        self._motor = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._saliendo = False
        self._total_ausencias_seg: float = 0.0
        self._conteo_ausencias: int = 0
        self._ultimo_color_clave: str | None = None
        self._en_calibracion: bool = True

        self.setStyleSheet(APP_STYLESHEET)
        self._construir_ui()
        if self._perfil_requiere_configuracion():
            self._mostrar_dialogo_perfil(obligatorio=True)
        self._configurar_bandeja()
        self._arrancar_componentes()

    def _arrancar_componentes(self) -> None:
        if self._errores_runtime:
            self._set_estado_error(
                "CONFIGURACION INCOMPLETA",
                "Faltan recursos obligatorios",
                " | ".join(self._errores_runtime),
            )
            self._subtitulo.setText("No fue posible iniciar el motor de vision.")
            self.statusBar().showMessage("Configuracion incompleta: revisa los modelos requeridos.")
            return

        if self._avisos_runtime:
            aviso_visible = self._resolver_aviso_visible(self._avisos_runtime)
            self._subtitulo.setText(aviso_visible)
            self.statusBar().showMessage(aviso_visible, 12000)

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
        self._motor.senal_ausencia_resuelta.connect(self._registrar_ausencia)
        self._motor.start()

    @staticmethod
    def _resolver_aviso_visible(avisos: list[str]) -> str:
        for aviso in avisos:
            aviso_up = aviso.upper()
            if "NO SE ENCONTRO EL MODELO YOLO" in aviso_up:
                return "Monitoreo visual activo y listo para uso."
            if "ULTRALYTICS NO ESTA DISPONIBLE" in aviso_up:
                return "Monitoreo visual activo con analisis principal disponible."
            if "ONNXRUNTIME" in aviso_up:
                return "Motor visual activo. Ajustando compatibilidad del entorno."
        return avisos[0] if avisos else "Sistema activo."

    def _perfil_requiere_configuracion(self) -> bool:
        nombre = self._perfil_usuario.get("nombre", "").strip().lower()
        return nombre in {"", "usuario local", "usuario_local"}

    def _perfil_resumen_rol(self) -> str:
        rol = self._perfil_usuario.get("rol", "Usuario")
        tipo = self._perfil_usuario.get("tipo_usuario", "empleado")
        return f"{rol} | {tipo.title()}"

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

        header = self._crear_header()
        main_layout.addWidget(header)

        content = QWidget()
        content.setObjectName("contentArea")
        content.setStyleSheet(CONTENT_BG_STYLE)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)

        video_panel = self._crear_panel_video()
        content_layout.addWidget(video_panel, 1)

        lateral_scroll = QScrollArea()
        lateral_scroll.setWidgetResizable(True)
        lateral_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lateral_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lateral_scroll.setFixedWidth(390)
        lateral_scroll.setWidget(self._crear_panel_lateral())
        content_layout.addWidget(lateral_scroll)

        main_layout.addWidget(content, 1)
        root_layout.addWidget(main_area, 1)

        barra = QStatusBar(self)
        barra.setObjectName("statusbar")
        barra.showMessage("SafeWork AI listo")
        self.setStatusBar(barra)



    def _crear_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(60)
        header.setStyleSheet(HEADER_STYLE)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        logo_path = self._settings.assets_dir / "logo.png"
        if logo_path.exists():
            logo_lbl = QLabel()
            px = QPixmap(str(logo_path)).scaled(
                140, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(px)
            layout.addWidget(logo_lbl)
        else:
            title_lbl = QLabel("SafeWork AI")
            title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f2040;")
            layout.addWidget(title_lbl)

        layout.addSpacing(16)

        self._dot_status = QLabel("●")
        self._dot_status.setStyleSheet("font-size: 12px; color: #059669;")
        layout.addWidget(self._dot_status)

        self._subtitulo = QLabel("Inicializando sistema...")
        self._subtitulo.setStyleSheet("font-size: 13px; color: #64748b;")
        layout.addWidget(self._subtitulo)

        layout.addStretch(1)
        
        user_layout = QHBoxLayout()
        user_layout.setSpacing(10)
        
        avatar_lbl = QLabel("\uE77B")
        avatar_lbl.setFixedSize(36, 36)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet("font-family: 'Segoe MDL2 Assets'; font-size: 16px; color: #1e3a5f; background: #e2e8f0; border-radius: 18px;")
        
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._name_lbl = QLabel(self._perfil_usuario.get("nombre", "Usuario local"))
        self._name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #1e293b;")
        self._role_lbl = QLabel(self._perfil_resumen_rol())
        self._role_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        text_layout.addWidget(self._name_lbl)
        text_layout.addWidget(self._role_lbl)
        
        user_layout.addWidget(avatar_lbl)
        user_layout.addLayout(text_layout)

        btn_perfil = QPushButton("Perfil")
        btn_perfil.setFixedHeight(28)
        btn_perfil.setStyleSheet(
            "QPushButton { background: #eef5ff; color: #1e3a5f; border: 1px solid #dbeafe; border-radius: 8px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background: #dbeafe; }"
        )
        btn_perfil.clicked.connect(self._mostrar_dialogo_perfil)
        user_layout.addWidget(btn_perfil)
        
        layout.addLayout(user_layout)

        return header

    def _crear_panel_video(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        cam_label = QLabel("Monitoreo en Vivo")
        cam_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1e293b;")
        top_row.addWidget(cam_label)
        top_row.addStretch(1)
        self._label_modo = QLabel("Iniciando...")
        self._label_modo.setStyleSheet("font-size: 11px; color: #94a3b8;")
        top_row.addWidget(self._label_modo)
        layout.addLayout(top_row)

        self._video = QLabel("Inicializando camara y modelos de IA...")
        self._video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._video.setMinimumSize(400, 260)
        self._video.setStyleSheet(VIDEO_FEED_IDLE)
        layout.addWidget(self._video, 1)

        self._bloqueo_banner = QLabel("RIESGO CRITICO: realiza una pausa activa antes de continuar.")
        self._bloqueo_banner.setWordWrap(True)
        self._bloqueo_banner.setVisible(False)
        self._bloqueo_banner.setStyleSheet(BANNER_CRITICAL)
        layout.addWidget(self._bloqueo_banner)

        metricas_row = QHBoxLayout()
        metricas_row.setSpacing(4)
        metricas_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._circ_postura = CircularMetricWidget("Postura", "\uE1E2")
        self._circ_ojos = CircularMetricWidget("Fatiga", "\uE890")
        self._circ_distancia = CircularMetricWidget("Distancia", "\uE7F4")
        self._circ_energia = CircularMetricWidget("Atencion", "\uE734")

        for w in (self._circ_postura, self._circ_ojos, self._circ_distancia, self._circ_energia):
            metricas_row.addWidget(w)

        layout.addLayout(metricas_row)
        return card

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
        self._refrescar_perfil_ui()

    def _refrescar_perfil_ui(self) -> None:
        if hasattr(self, "_name_lbl"):
            self._name_lbl.setText(self._perfil_usuario.get("nombre", "Usuario local"))
        if hasattr(self, "_role_lbl"):
            self._role_lbl.setText(self._perfil_resumen_rol())

    def _crear_panel_lateral(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)

        layout.addWidget(self._crear_card_estado())
        layout.addWidget(self._crear_card_incidencias())
        layout.addStretch(1)
        return container

    def _crear_card_estado(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        icon_lbl = QLabel("\uE9A2")
        icon_lbl.setStyleSheet("font-family: 'Segoe MDL2 Assets'; font-size: 16px; color: #1e293b;")
        sec_title = QLabel("Insights IA")
        sec_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #1e293b;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(sec_title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        layout.addWidget(sep)

        sub_row = QHBoxLayout()
        sub_title = QLabel("Alertas y recomendaciones")
        sub_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")
        self._alert_badge = QLabel("3")
        self._alert_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._alert_badge.setStyleSheet("background: #e0f2fe; color: #0284c7; border-radius: 8px; font-weight: bold; font-size: 10px; padding: 2px 6px;")
        sub_row.addWidget(sub_title)
        sub_row.addStretch(1)
        sub_row.addWidget(self._alert_badge)
        layout.addLayout(sub_row)

        voz_row = QHBoxLayout()
        voz_lbl = QLabel("Control de voz")
        voz_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")
        self._btn_voz_toggle = QPushButton("Voz activa")
        self._btn_voz_toggle.setFixedHeight(28)
        self._btn_voz_toggle.setStyleSheet(
            "QPushButton { background: #0ea5a4; color: #ffffff; border: none; border-radius: 7px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
            "QPushButton:hover { background: #0f8f8e; }"
        )
        self._btn_voz_toggle.clicked.connect(self._alternar_voz)
        voz_row.addWidget(voz_lbl)
        voz_row.addStretch(1)
        voz_row.addWidget(self._btn_voz_toggle)
        layout.addLayout(voz_row)

        self._estado = QLabel("CALIBRANDO")
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #0284c7; "
            "background: #eff6ff; padding: 12px; border-radius: 8px; border: 1px solid #bae6fd;"
        )
        layout.addWidget(self._estado)

        self._estado_aux = QLabel("")
        self._estado_aux.setVisible(False)
        self._detalle = QLabel("")
        self._detalle.setVisible(False)
        self._metricas_resumen = QLabel("")
        self._metricas_resumen.setVisible(False)
        self._ausencia_total_lbl = self._crear_stat_row("", "")
        self._ausencia_total_lbl.setVisible(False)
        self._ausencia_conteo_lbl = self._crear_stat_row("", "")
        self._ausencia_conteo_lbl.setVisible(False)
        self._log_resumen = QLabel("")
        self._log_resumen.setVisible(False)

        self._ausencia_ultima = QLabel("Sin ausencias registradas")
        self._ausencia_ultima.setWordWrap(True)
        self._ausencia_ultima.setStyleSheet(
            "font-size: 12px; color: #1d4ed8; background: #eff6ff; "
            "padding: 12px; border-radius: 8px; border: 1px solid #bfdbfe;"
        )
        layout.addWidget(self._ausencia_ultima)

        self._ultima_incidencia = QLabel("Aun no se registran incidencias.")
        self._ultima_incidencia.setWordWrap(True)
        self._ultima_incidencia.setStyleSheet(
            "font-size: 12px; color: #065f46; background: #ecfdf5; "
            "padding: 12px; border-radius: 8px; border: 1px solid #a7f3d0;"
        )
        layout.addWidget(self._ultima_incidencia)
        
        layout.addStretch(1)
        return card

    def _crear_card_incidencias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        sec_title = QLabel("Resumen ergonomico (Hoy)")
        sec_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #1e293b;")
        title_row.addWidget(sec_title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e2e8f0; margin: 4px 0;")
        layout.addWidget(sep)

        score_panel = QFrame()
        score_panel.setStyleSheet(
            "QFrame { background: #f8fbff; border: 1px solid #dbeafe; border-radius: 8px; }"
        )
        score_row = QHBoxLayout(score_panel)
        score_row.setContentsMargins(12, 10, 12, 10)
        score_row.setSpacing(10)

        icon_score = QLabel("\uE9D2")
        icon_score.setFixedSize(34, 34)
        icon_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_score.setStyleSheet(
            "font-family: 'Segoe MDL2 Assets'; font-size: 20px; color: #0f766e; "
            "background: #ccfbf1; border-radius: 8px;"
        )
        self._score_global = QLabel("100")
        self._score_global.setStyleSheet("font-size: 38px; font-weight: 800; color: #0f766e;")
        self._score_detalle = QLabel("Indice general\nOperacion optima")
        self._score_detalle.setStyleSheet("font-size: 13px; color: #475569;")

        score_row.addWidget(icon_score)
        score_row.addWidget(self._score_global)
        score_row.addWidget(self._score_detalle)
        score_row.addStretch(1)
        layout.addWidget(score_panel)

        self._grafico_global = MiniTrendWidget()
        self._grafico_global.setMinimumHeight(82)
        layout.addWidget(self._grafico_global)

        self._incidencias_totales = self._crear_stat_row("Alertas jornada", "--")
        self._incidencias_postura = self._crear_stat_row("Riesgo postural", "--")
        self._incidencias_pantalla = self._crear_stat_row("Distancia monitor", "--")
        self._incidencias_fatiga = self._crear_stat_row("Fatiga visual", "--")
        self._historial_hoy = self._crear_stat_row("Eventos hoy", "--")
        self._historial_semana = self._crear_stat_row("Ultimos 7 dias", "--")
        self._historial_mes = self._crear_stat_row("Ultimos 30 dias", "--")

        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(6)
        for row in (
            self._incidencias_totales,
            self._incidencias_postura,
            self._incidencias_pantalla,
            self._incidencias_fatiga,
            self._historial_hoy,
            self._historial_semana,
            self._historial_mes,
        ):
            stats_layout.addWidget(row)
        layout.addLayout(stats_layout)

        layout.addStretch(1)

        self._boton_exportar = QPushButton("\uE8A5  Exportar reporte")
        self._boton_exportar.setStyleSheet(
            "QPushButton { font-family: 'Segoe UI', 'Segoe MDL2 Assets'; background: #1d4ed8; color: #ffffff; "
            "font-size: 12px; font-weight: 700; border: none; border-radius: 8px; padding: 11px 14px; }"
            "QPushButton:hover { background: #1e40af; }"
        )
        self._boton_exportar.clicked.connect(self._exportar_reporte)
        layout.addWidget(self._boton_exportar)

        return card


    @staticmethod
    def _crear_stat_row(etiqueta: str, valor: str) -> QWidget:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(6)
        lbl = QLabel(etiqueta)
        lbl.setStyleSheet(STAT_LABEL_STYLE)
        val = QLabel(valor)
        val.setObjectName("statValue")
        val.setStyleSheet(STAT_VALUE_STYLE)
        layout.addWidget(lbl)
        layout.addStretch(1)
        layout.addWidget(val)
        row._value_label = val
        return row
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

    def _set_estado_error(self, titulo: str, aux: str, detalle: str) -> None:
        self._estado.setText(titulo)
        color, bg, border = STATUS_COLORS.get("ERROR", ("#ef4444", "#1f0202", "#7f1d1d"))
        self._estado.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {color}; "
            f"background: {bg}; padding: 8px 12px; border-radius: 8px; border: 1px solid {border};"
        )
        self._estado_aux.setText(aux)
        self._detalle.setText(detalle)

    def _manejar_error_motor(self, mensaje_error: str) -> None:
        self._set_estado_error("ERROR DE SENSOR", "Error en camara o procesamiento de IA", mensaje_error)
        self._video.setText(
            f"SISTEMA EN PAUSA\n\n{mensaje_error}\n\nVerifica la conexion de tu camara."
        )
        self._video.setStyleSheet(VIDEO_FEED_ERROR)
        self._dot_status.setStyleSheet("font-size: 10px; color: #ef4444;")
        self.statusBar().showMessage(f"Error detectado: {mensaje_error}", 15000)

    def _manejar_error_voz(self, mensaje_error: str) -> None:
        self._voz_habilitada = False
        if hasattr(self, "_btn_voz_toggle"):
            self._btn_voz_toggle.setText("Voz inactiva")
            self._btn_voz_toggle.setStyleSheet(
                "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 7px; "
                "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
            )
            self._btn_voz_toggle.setEnabled(False)
        self.statusBar().showMessage(f"Asistente de voz inactivo: {mensaje_error}", 8000)

    def _alternar_voz(self) -> None:
        if self._worker_voz is None:
            return
        self._voz_habilitada = not self._voz_habilitada
        estado = "Activo" if self._voz_habilitada else "Silenciado"
        if not self._voz_habilitada:
            self._worker_voz.limpiar_cola()
        if hasattr(self, "_btn_voz_toggle"):
            if self._voz_habilitada:
                self._btn_voz_toggle.setText("\uE995 Voz activa")
                self._btn_voz_toggle.setStyleSheet(
                    "QPushButton { font-family: 'Segoe UI', 'Segoe MDL2 Assets'; background: #0ea5a4; color: #ffffff; border: none; border-radius: 7px; "
                    "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
                    "QPushButton:hover { background: #0f8f8e; }"
                )
            else:
                self._btn_voz_toggle.setText("\uE1D6 Voz inactiva")
                self._btn_voz_toggle.setStyleSheet(
                    "QPushButton { font-family: 'Segoe UI', 'Segoe MDL2 Assets'; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 7px; "
                    "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
                    "QPushButton:hover { background: #e2e8f0; }"
                )
        self.statusBar().showMessage(f"Asistente de voz: {estado}", 4000)

    def _registrar_ausencia(self, duracion_seg: float) -> None:
        self._conteo_ausencias += 1
        self._total_ausencias_seg += duracion_seg

        if duracion_seg < 60:
            duracion_fmt = f"{int(duracion_seg)} seg"
        else:
            mins = int(duracion_seg) // 60
            segs = int(duracion_seg) % 60
            duracion_fmt = f"{mins} min {segs:02d} seg"

        total = self._total_ausencias_seg
        if total < 60:
            total_fmt = f"{int(total)} seg"
        else:
            mins_t = int(total) // 60
            segs_t = int(total) % 60
            total_fmt = f"{mins_t} min {segs_t:02d} seg"

        self._ausencia_ultima.setText(
            f"Ultima ausencia: {duracion_fmt}\nEl usuario regreso al puesto de trabajo."
        )
        self._ausencia_ultima.setStyleSheet(
            "font-size: 12px; color: #374151; background: #eff6ff; "
            "padding: 8px 10px; border-radius: 8px; border: 1px solid #bae6fd;"
        )
        self._actualizar_stat(self._ausencia_total_lbl, total_fmt)
        self._actualizar_stat(self._ausencia_conteo_lbl, f"{self._conteo_ausencias} vez" if self._conteo_ausencias == 1 else f"{self._conteo_ausencias} veces")
        self.statusBar().showMessage(f"Retorno registrado - ausencia de {duracion_fmt}", 6000)

    def _actualizar_frame(self, imagen) -> None:
        pixmap = QPixmap.fromImage(imagen)
        if pixmap.isNull():
            return
        target = self._video.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        escalado = pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._video.setPixmap(escalado)

    def _actualizar_estado(self, estado: str) -> None:
        estado_base = estado.replace(" - Cooldown activo", "")
        self._ultimo_estado_base = estado_base
        self._estado.setText(estado_base)

        clave = next((k for k in STATUS_COLORS if k in estado_base.upper()), None)
        if clave != self._ultimo_color_clave:
            color, bg, border = STATUS_COLORS.get(clave, ("#1e293b", "#f8fafc", "#e2e8f0"))
            self._estado.setStyleSheet(
                f"font-size: 15px; font-weight: 700; color: {color}; "
                f"background: {bg}; padding: 8px 12px; border-radius: 8px; border: 1px solid {border};"
            )
            self._ultimo_color_clave = clave
        self._estado_aux.setText(
            "Pausa temporal entre alertas" if "Cooldown activo" in estado else "Monitoreo activo"
        )
        self.statusBar().showMessage(estado)

    def _actualizar_detalle_estado(self, detalle: str) -> None:
        if detalle:
            self._detalle.setText(detalle)

    def _actualizar_modo_operacion(self, mensaje: str) -> None:
        if not mensaje:
            return
        self._subtitulo.setText(mensaje)
        self._label_modo.setText(mensaje[:60])
        self.statusBar().showMessage(mensaje, 10000)

    def _actualizar_metricas(self, metricas: str) -> None:
        if metricas:
            self._aplicar_metricas_legibles(metricas)

    def _actualizar_nivel_riesgo(self, nivel: str) -> None:
        self._nivel_riesgo_actual = nivel
        border_color = LEVEL_COLORS.get(nivel, "#0f2040")
        self._video.setStyleSheet(
            f"background-color: #020912; border: 2px solid {border_color}; border-radius: 10px;"
        )
        etiquetas = {
            "OBSERVACION":       "Observacion preventiva",
            "RIESGO_LEVE":       "Riesgo leve",
            "RIESGO_CONFIRMADO": "Riesgo confirmado",
            "RIESGO_CRITICO":    "Riesgo critico",
        }
        texto = etiquetas.get(nivel, "Monitoreo activo")
        self._estado_aux.setText(texto)
        if nivel == "RIESGO_CRITICO":
            # Si el riesgo es crítico, el banner muestra el último mensaje
            pass
        else:
            self._bloqueo_banner.setVisible(False)

    def _manejar_bloqueo_critico(self, mensaje: str) -> None:
        self._bloqueo_banner.setText(f"RIESGO CRITICO: {mensaje}")
        self._bloqueo_banner.setVisible(True)
        self.statusBar().showMessage(f"Riesgo critico: {mensaje}", 7000)

    def _actualizar_panel_incidencias(self, resumen: object) -> None:
        if not isinstance(resumen, dict):
            return

        metricas = resumen.get("metricas_agregadas", {})
        periodos = metricas.get("periodos", {}) if isinstance(metricas, dict) else {}
        if not isinstance(periodos, dict):
            periodos = {}
        self._actualizar_stat(self._incidencias_totales, str(int(periodos.get("hoy", 0) or 0)))
        self._actualizar_stat(self._historial_hoy, str(int(periodos.get("hoy", 0) or 0)))
        self._actualizar_stat(self._historial_semana, str(int(periodos.get("ultimos_7_dias", 0) or 0)))
        self._actualizar_stat(self._historial_mes, str(int(periodos.get("ultimos_30_dias", 0) or 0)))

        hoy = float(int(periodos.get("hoy", 0) or 0))
        sem = float(int(periodos.get("ultimos_7_dias", 0) or 0))
        mes = float(int(periodos.get("ultimos_30_dias", 0) or 0))
        if hasattr(self, "_grafico_global"):
            self._grafico_global.actualizar([mes / 4.0, sem / 2.0, hoy * 0.8, hoy])

        ultimas = resumen.get("ultimas_incidencias", [])
        if isinstance(ultimas, list) and ultimas:
            ultima = ultimas[0] if isinstance(ultimas[0], dict) else {}
            estado_str = str(ultima.get("estado", "Incidencia"))
            severidad = str(ultima.get("severidad", "informativa")).upper()
            descripcion = str(ultima.get("descripcion", "Sin descripcion"))
            timestamp = str(ultima.get("timestamp", ""))
            self._ultima_incidencia.setText(f"{estado_str}\n{descripcion}")
            self._log_resumen.setText(f"{timestamp} | Prioridad: {severidad}")
        else:
            self._ultima_incidencia.setText("Aun no se registran incidencias.")
            self._log_resumen.setText("El historial mostrara la ultima incidencia validada.")

    @staticmethod
    def _actualizar_stat(row_widget: QWidget, valor: str) -> None:
        if hasattr(row_widget, "_value_label"):
            row_widget._value_label.setText(valor)

    def _aplicar_metricas_legibles(self, metricas: str) -> None:
        valores = self._parsear_metricas(metricas)
        ear = valores.get("EAR", 0.0)
        mar = valores.get("MAR", 0.0)
        cuello = valores.get("Cuello", 0.0)
        lateral = valores.get("Lateral", 0.0)
        proximidad = valores.get("Prox", 0.0)
        calidad = valores.get("Calidad", 100.0)

        ear_pct = min(100.0, max(0.0, (ear / 0.34) * 100.0))
        if ear < 0.22:
            ojos_sub, ojos_color, ojos_desc = "Cerrados", "#dc2626", "Nivel de alerta alto"
        elif ear < 0.28:
            ojos_sub, ojos_color, ojos_desc = "Cansados", "#d97706", "Descansa la vista"
        else:
            ojos_sub, ojos_color, ojos_desc = "Relajados", "#059669", "Estado ocular normal"

        severidad_postural = max(cuello / 32.0, lateral / 10.0)
        postura_pct = max(0.0, min(100.0, 100.0 - severidad_postural * 100.0))
        if cuello >= 28.0:
            pos_sub, pos_color, pos_desc = "Inclinada", "#dc2626", "Corrige la posicion"
        elif cuello >= 14.0 or lateral >= 7.5:
            pos_sub, pos_color, pos_desc = "Por corregir", "#d97706", "Ajusta tu postura"
        else:
            pos_sub, pos_color, pos_desc = "Correcta", "#059669", "Manten la espalda recta"

        dist_pct = max(0.0, min(100.0, 100.0 - (proximidad / 0.9) * 100.0))
        if proximidad >= 0.72:
            dist_sub, dist_color, dist_desc = "Muy cerca", "#dc2626", "Aleja el monitor"
        elif proximidad >= 0.35:
            dist_sub, dist_color, dist_desc = "Leve", "#d97706", "Rango recomendado"
        else:
            dist_sub, dist_color, dist_desc = "Optima", "#059669", "Rango recomendado"

        mar_pct = max(0.0, min(100.0, 100.0 - (mar / 0.6) * 100.0))
        if mar > 0.45:
            ene_sub, ene_color, ene_desc = "Bostezo", "#d97706", "Posible fatiga"
        elif mar > 0.20:
            ene_sub, ene_color, ene_desc = "Variable", "#d97706", "Atencion baja"
        else:
            ene_sub, ene_color, ene_desc = "Estable", "#059669", "Concentracion normal"

        self._circ_ojos.actualizar(f"{int(ear_pct)}%", ear_pct, ojos_sub, ojos_desc, ojos_color)
        self._circ_postura.actualizar(f"{int(postura_pct)}%", postura_pct, pos_sub, pos_desc, pos_color)
        self._circ_distancia.actualizar(f"{int(dist_pct)}%", dist_pct, dist_sub, dist_desc, dist_color)
        self._circ_energia.actualizar(f"{int(mar_pct)}%", mar_pct, ene_sub, ene_desc, ene_color)

        indice_global = int(
            round(
                postura_pct * 0.30
                + ear_pct * 0.24
                + dist_pct * 0.18
                + mar_pct * 0.18
                + max(0.0, min(100.0, calidad)) * 0.10
            )
        )
        indice_global = max(0, min(100, indice_global))
        if hasattr(self, "_score_global"):
            self._score_global.setText(str(indice_global))
        if hasattr(self, "_score_detalle"):
            self._score_detalle.setText(self._describir_indice_global(indice_global))
        if hasattr(self, "_grafico_global"):
            self._grafico_global.actualizar(
                [
                    max(0.0, 100.0 - postura_pct),
                    max(0.0, 100.0 - dist_pct),
                    max(0.0, 100.0 - ear_pct),
                    max(0.0, 100.0 - mar_pct),
                ]
            )
        self._actualizar_stat(self._incidencias_postura, self._etiqueta_riesgo(100.0 - postura_pct))
        self._actualizar_stat(self._incidencias_pantalla, self._etiqueta_riesgo(100.0 - dist_pct))
        self._actualizar_stat(self._incidencias_fatiga, self._etiqueta_riesgo(max(100.0 - ear_pct, 100.0 - mar_pct)))

        self._metricas_resumen.setText(
            f"{ojos_sub.lower()}, postura {pos_sub.lower()}, distancia {dist_sub.lower()}."
        )

    @staticmethod
    def _describir_indice_global(score: int) -> str:
        if score >= 85:
            return "Indice general\nOperacion optima"
        if score >= 70:
            return "Indice general\nSeguimiento estable"
        if score >= 50:
            return "Indice general\nAtencion preventiva"
        return "Indice general\nCorreccion prioritaria"

    @staticmethod
    def _etiqueta_riesgo(valor: float) -> str:
        valor_int = max(0, min(100, int(round(valor))))
        if valor_int < 20:
            return f"Bajo ({valor_int}%)"
        if valor_int < 45:
            return f"Medio ({valor_int}%)"
        return f"Alto ({valor_int}%)"

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
        QApplication.instance().quit()

    def changeEvent(self, event: QEvent) -> None:
        """Pausa la renderización del frame de video si la ventana se oculta o minimiza."""
        if event.type() == QEvent.Type.WindowStateChange:
            is_minimized_or_hidden = self.isMinimized() or self.isHidden()
            if self._motor is not None:
                self._motor.set_ui_visible(not is_minimized_or_hidden)
        super().changeEvent(event)
