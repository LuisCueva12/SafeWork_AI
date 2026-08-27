from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import SafeWorkSettings
from .safework_presenter import (
    AusenciaRegistradaVM,
    EstadoSistemaVM,
    IncidenciasResumenVM,
    MetricasLegiblesVM,
)
from .safework_styles import (
    BANNER_CRITICAL,
    CARD_STYLE,
    HEADER_STYLE,
    VIDEO_FEED_ERROR,
    VIDEO_FEED_IDLE,
)
from .safework_widgets import CircularMetricWidget, MiniTrendWidget, StatRow, aplicar_sombra_suave


class HeaderView(QWidget):
    """Encabezado: logo, estado de conexion y perfil del usuario. Sin logica propia."""

    perfil_solicitado = pyqtSignal()

    def __init__(self, settings: SafeWorkSettings, nombre_usuario: str, resumen_rol: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(60)
        self.setStyleSheet(HEADER_STYLE)
        aplicar_sombra_suave(self, blur=16, offset_y=3)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        logo_path = settings.assets_dir / "logo.png"
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

        self._avatar_lbl = QLabel(self._inicial(nombre_usuario))
        self._avatar_lbl.setFixedSize(36, 36)
        self._avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #1e3a5f; background: #e2e8f0; border-radius: 18px;"
        )

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._name_lbl = QLabel(nombre_usuario)
        self._name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #1e293b;")
        self._role_lbl = QLabel(resumen_rol)
        self._role_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        text_layout.addWidget(self._name_lbl)
        text_layout.addWidget(self._role_lbl)

        user_layout.addWidget(self._avatar_lbl)
        user_layout.addLayout(text_layout)

        btn_perfil = QPushButton("Perfil")
        btn_perfil.setFixedHeight(28)
        btn_perfil.setStyleSheet(
            "QPushButton { background: #eef5ff; color: #1e3a5f; border: 1px solid #dbeafe; border-radius: 8px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background: #dbeafe; }"
        )
        btn_perfil.clicked.connect(self.perfil_solicitado.emit)
        user_layout.addWidget(btn_perfil)

        layout.addLayout(user_layout)

    @staticmethod
    def _inicial(nombre: str) -> str:
        nombre = nombre.strip()
        return nombre[0].upper() if nombre else "U"

    def actualizar_subtitulo(self, texto: str) -> None:
        self._subtitulo.setText(texto)

    def actualizar_color_estado(self, color_hex: str) -> None:
        self._dot_status.setStyleSheet(f"font-size: 10px; color: {color_hex};")

    def actualizar_perfil(self, nombre: str, resumen_rol: str) -> None:
        self._name_lbl.setText(nombre)
        self._role_lbl.setText(resumen_rol)
        self._avatar_lbl.setText(self._inicial(nombre))


class VideoPanelView(QFrame):
    """Panel de video en vivo + tarjetas de metricas circulares. Sin logica propia."""

    def __init__(self, debug_hud_enabled: bool, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)
        aplicar_sombra_suave(self)
        layout = QVBoxLayout(self)
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

        self._hud_diagnostico: QLabel | None = None
        if debug_hud_enabled:
            self._hud_diagnostico = QLabel("Diagnostico: esperando datos...")
            self._hud_diagnostico.setStyleSheet(
                "font-family: 'Consolas', monospace; font-size: 10px; color: #22c55e; "
                "background: #05100a; padding: 6px 8px; border-radius: 8px;"
            )
            self._hud_diagnostico.setWordWrap(True)
            layout.addWidget(self._hud_diagnostico)

        self._bloqueo_banner = QLabel("RIESGO CRITICO: realiza una pausa activa antes de continuar.")
        self._bloqueo_banner.setWordWrap(True)
        self._bloqueo_banner.setVisible(False)
        self._bloqueo_banner.setStyleSheet(BANNER_CRITICAL)
        layout.addWidget(self._bloqueo_banner)

        metricas_row = QHBoxLayout()
        metricas_row.setSpacing(4)
        metricas_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._circ_postura = CircularMetricWidget("Postura", "postura")
        self._circ_ojos = CircularMetricWidget("Fatiga", "fatiga")
        self._circ_distancia = CircularMetricWidget("Distancia", "distancia")
        self._circ_energia = CircularMetricWidget("Atencion", "atencion")

        for w in (self._circ_postura, self._circ_ojos, self._circ_distancia, self._circ_energia):
            metricas_row.addWidget(w)

        layout.addLayout(metricas_row)

    def tiene_hud(self) -> bool:
        return self._hud_diagnostico is not None

    def actualizar_diagnostico(self, texto: str) -> None:
        if self._hud_diagnostico is not None:
            self._hud_diagnostico.setText(texto)

    def actualizar_frame(self, imagen) -> None:
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

    def actualizar_modo(self, mensaje: str) -> None:
        self._label_modo.setText(mensaje[:60])

    def mostrar_error(self, mensaje_error: str) -> None:
        self._video.setText(
            f"SISTEMA EN PAUSA\n\n{mensaje_error}\n\nVerifica la conexion de tu camara."
        )
        self._video.setStyleSheet(VIDEO_FEED_ERROR)

    def aplicar_glow_riesgo(self, color_glow_hex: str) -> None:
        color_glow = QColor(color_glow_hex)
        color_glow.setAlpha(110)
        self._video.setStyleSheet("background-color: #020912; border: none; border-radius: 14px;")
        aplicar_sombra_suave(self._video, blur=28, offset_y=0, color=color_glow)

    def ocultar_banner_bloqueo(self) -> None:
        self._bloqueo_banner.setVisible(False)

    def mostrar_banner_bloqueo(self, mensaje: str) -> None:
        self._bloqueo_banner.setText(f"RIESGO CRITICO: {mensaje}")
        self._bloqueo_banner.setVisible(True)

    def actualizar_metricas(self, vm: MetricasLegiblesVM) -> None:
        self._circ_ojos.actualizar(
            vm.ojos.valor_texto, vm.ojos.porcentaje, vm.ojos.subtexto, vm.ojos.descripcion, vm.ojos.color_hex
        )
        self._circ_postura.actualizar(
            vm.postura.valor_texto, vm.postura.porcentaje, vm.postura.subtexto, vm.postura.descripcion, vm.postura.color_hex
        )
        self._circ_distancia.actualizar(
            vm.distancia.valor_texto, vm.distancia.porcentaje, vm.distancia.subtexto, vm.distancia.descripcion, vm.distancia.color_hex
        )
        self._circ_energia.actualizar(
            vm.energia.valor_texto, vm.energia.porcentaje, vm.energia.subtexto, vm.energia.descripcion, vm.energia.color_hex
        )


class InsightsPanelView(QFrame):
    """Tarjeta 'Insights IA': estado del sistema, voz, ausencias e incidencias. Sin logica propia."""

    voz_alternada = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)
        aplicar_sombra_suave(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        sec_title = QLabel("Insights IA")
        sec_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #1e293b;")
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
        alert_badge = QLabel("3")
        alert_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        alert_badge.setStyleSheet(
            "background: #e0f2fe; color: #0284c7; border-radius: 8px; font-weight: bold; font-size: 10px; padding: 2px 6px;"
        )
        sub_row.addWidget(sub_title)
        sub_row.addStretch(1)
        sub_row.addWidget(alert_badge)
        layout.addLayout(sub_row)

        voz_row = QHBoxLayout()
        voz_lbl = QLabel("Control de voz")
        voz_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")
        self._btn_voz_toggle = QPushButton("● Voz activa")
        self._btn_voz_toggle.setFixedHeight(28)
        self._btn_voz_toggle.setStyleSheet(self._estilo_voz(activa=True))
        self._btn_voz_toggle.clicked.connect(self.voz_alternada.emit)
        voz_row.addWidget(voz_lbl)
        voz_row.addStretch(1)
        voz_row.addWidget(self._btn_voz_toggle)
        layout.addLayout(voz_row)

        self._estado = QLabel("CALIBRANDO")
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #0284c7; "
            "background: #eff6ff; padding: 12px; border-radius: 10px;"
        )
        layout.addWidget(self._estado)

        self._estado_aux = QLabel("")
        self._estado_aux.setVisible(False)
        self._detalle = QLabel("")
        self._detalle.setVisible(False)
        self._metricas_resumen = QLabel("")
        self._metricas_resumen.setVisible(False)
        self._ausencia_total_lbl = StatRow("", "")
        self._ausencia_total_lbl.setVisible(False)
        self._ausencia_conteo_lbl = StatRow("", "")
        self._ausencia_conteo_lbl.setVisible(False)
        self._log_resumen = QLabel("")
        self._log_resumen.setVisible(False)

        self._ausencia_ultima = QLabel("")
        self._ausencia_ultima.setWordWrap(True)
        self._ausencia_ultima.setStyleSheet(
            "font-size: 12px; color: #1d4ed8; background: #eff6ff; "
            "padding: 12px; border-radius: 10px;"
        )
        self._ausencia_ultima.setVisible(False)
        layout.addWidget(self._ausencia_ultima)

        self._ultima_incidencia = QLabel("")
        self._ultima_incidencia.setWordWrap(True)
        self._ultima_incidencia.setStyleSheet(
            "font-size: 12px; color: #065f46; background: #ecfdf5; "
            "padding: 12px; border-radius: 10px;"
        )
        self._ultima_incidencia.setVisible(False)
        layout.addWidget(self._ultima_incidencia)

        layout.addStretch(1)

    @staticmethod
    def _estilo_voz(activa: bool) -> str:
        if activa:
            return (
                "QPushButton { background: #0ea5a4; color: #ffffff; border: none; border-radius: 7px; "
                "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
                "QPushButton:hover { background: #0f8f8e; }"
            )
        return (
            "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 7px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 700; }"
            "QPushButton:hover { background: #e2e8f0; }"
        )

    def actualizar_estado(self, vm: EstadoSistemaVM, forzar_estilo: bool = True) -> None:
        self._estado.setText(vm.estado_base)
        if forzar_estilo:
            self._estado.setStyleSheet(
                f"font-size: 15px; font-weight: 700; color: {vm.color}; "
                f"background: {vm.color_fondo}; padding: 8px 12px; border-radius: 10px;"
            )
        self._estado_aux.setText(vm.texto_auxiliar)

    def actualizar_estado_auxiliar(self, texto: str) -> None:
        self._estado_aux.setText(texto)

    def actualizar_detalle(self, texto: str) -> None:
        if texto:
            self._detalle.setText(texto)

    def actualizar_metricas_resumen(self, texto: str) -> None:
        self._metricas_resumen.setText(texto)

    def actualizar_ausencia(self, vm: AusenciaRegistradaVM) -> None:
        self._ausencia_ultima.setText(vm.texto_ultima_ausencia)
        self._ausencia_ultima.setStyleSheet(
            "font-size: 12px; color: #374151; background: #eff6ff; "
            "padding: 8px 10px; border-radius: 10px;"
        )
        self._ausencia_ultima.setVisible(True)
        self._ausencia_total_lbl.actualizar(vm.texto_total_acumulado)
        self._ausencia_conteo_lbl.actualizar(vm.texto_conteo)

    def actualizar_ultima_incidencia(self, visible: bool, texto: str, log_texto: str) -> None:
        self._ultima_incidencia.setVisible(visible)
        if visible:
            self._ultima_incidencia.setText(texto)
        self._log_resumen.setText(log_texto)

    def actualizar_estado_voz(self, activa: bool) -> None:
        self._btn_voz_toggle.setText("● Voz activa" if activa else "○ Voz inactiva")
        self._btn_voz_toggle.setStyleSheet(self._estilo_voz(activa))

    def deshabilitar_voz(self) -> None:
        self._btn_voz_toggle.setText("Voz inactiva")
        self._btn_voz_toggle.setStyleSheet(self._estilo_voz(activa=False))
        self._btn_voz_toggle.setEnabled(False)


class IncidenciasCardView(QFrame):
    """Tarjeta 'Resumen ergonomico': indice global, tendencia y estadisticas. Sin logica propia."""

    exportar_solicitado = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)
        aplicar_sombra_suave(self)
        layout = QVBoxLayout(self)
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
        score_panel.setStyleSheet("QFrame { background: #f8fbff; border-radius: 10px; }")
        score_row = QHBoxLayout(score_panel)
        score_row.setContentsMargins(12, 10, 12, 10)
        score_row.setSpacing(10)

        self._score_global = QLabel("100")
        self._score_global.setStyleSheet("font-size: 38px; font-weight: 800; color: #0f766e;")
        self._score_detalle = QLabel("Indice general\nOperacion optima")
        self._score_detalle.setStyleSheet("font-size: 13px; color: #475569;")

        score_row.addWidget(self._score_global)
        score_row.addWidget(self._score_detalle)
        score_row.addStretch(1)
        layout.addWidget(score_panel)

        self._grafico_global = MiniTrendWidget()
        self._grafico_global.setMinimumHeight(82)
        layout.addWidget(self._grafico_global)

        self._incidencias_totales = StatRow("Alertas jornada", "--")
        self._incidencias_postura = StatRow("Riesgo postural", "--")
        self._incidencias_pantalla = StatRow("Distancia monitor", "--")
        self._incidencias_fatiga = StatRow("Fatiga visual", "--")
        self._historial_hoy = StatRow("Eventos hoy", "--")
        self._historial_semana = StatRow("Ultimos 7 dias", "--")
        self._historial_mes = StatRow("Ultimos 30 dias", "--")

        stats_layout = QGridLayout()
        stats_layout.setHorizontalSpacing(8)
        stats_layout.setVerticalSpacing(6)
        filas_stats = (
            self._incidencias_totales,
            self._incidencias_postura,
            self._incidencias_pantalla,
            self._incidencias_fatiga,
            self._historial_hoy,
            self._historial_semana,
            self._historial_mes,
        )
        for indice, row in enumerate(filas_stats):
            stats_layout.addWidget(row, indice // 2, indice % 2)
        layout.addLayout(stats_layout)

        layout.addStretch(1)

        boton_exportar = QPushButton("↓  Exportar reporte")
        boton_exportar.setStyleSheet(
            "QPushButton { background: #1d4ed8; color: #ffffff; "
            "font-size: 12px; font-weight: 700; border: none; border-radius: 8px; padding: 11px 14px; }"
            "QPushButton:hover { background: #1e40af; }"
        )
        boton_exportar.clicked.connect(self.exportar_solicitado.emit)
        layout.addWidget(boton_exportar)

    def actualizar_indice_global(self, indice: int, detalle: str, tendencia: list[float]) -> None:
        self._score_global.setText(str(indice))
        self._score_detalle.setText(detalle)
        self._grafico_global.actualizar(tendencia)

    def actualizar_riesgos(self, postura: str, pantalla: str, fatiga: str) -> None:
        self._incidencias_postura.actualizar(postura)
        self._incidencias_pantalla.actualizar(pantalla)
        self._incidencias_fatiga.actualizar(fatiga)

    def actualizar_resumen(self, vm: IncidenciasResumenVM) -> None:
        self._incidencias_totales.actualizar(vm.total_hoy)
        self._historial_hoy.actualizar(vm.total_hoy)
        self._historial_semana.actualizar(vm.total_semana)
        self._historial_mes.actualizar(vm.total_mes)
        self._grafico_global.actualizar(vm.tendencia)
