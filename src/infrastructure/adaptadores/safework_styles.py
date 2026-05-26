from __future__ import annotations


APP_STYLESHEET = """
* {
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: #f0f4f8;
}

QWidget {
    color: #1e293b;
    background: transparent;
}

QStatusBar {
    background: #f8fafc;
    color: #475569;
    border-top: 1px solid #dbe4f0;
    font-size: 11px;
    padding: 3px 12px;
}

QStatusBar::item {
    border: none;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #eaf0f7;
    width: 7px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #bac8da;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QMenu {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 10px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 4px;
    color: #334155;
}

QMenu::item:selected {
    background: #eef5ff;
    color: #0f4aa5;
}
"""

SIDEBAR_STYLE = """
QWidget#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #08244a, stop:1 #04162e);
    border-right: 1px solid #17345a;
}
"""

HEADER_STYLE = """
QWidget#header {
    background: #ffffff;
    border-bottom: 1px solid #dbe4f0;
}
"""

CONTENT_BG_STYLE = (
    "QWidget#contentArea {"
    "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    "stop:0 #f4f8fd, stop:1 #eef3f9); }"
)

CARD_STYLE = """
QFrame#card {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 14px;
}
"""

SECTION_TITLE_STYLE = (
    "font-size: 10px; font-weight: 700; color: #64748b; "
    "letter-spacing: 1.5px; text-transform: uppercase;"
)

STATUS_COLORS = {
    "OPTIMO":            ("#059669", "#ecfdf5", "#a7f3d0"),
    "CALIBRANDO":        ("#0284c7", "#eff6ff", "#bae6fd"),
    "CERCANIA":          ("#d97706", "#fffbeb", "#fde68a"),
    "MALA_POSTURA":      ("#ea580c", "#fff7ed", "#fed7aa"),
    "ADVERTENCIA_SUENO": ("#d97706", "#fffbeb", "#fde68a"),
    "FATIGA_EXTREMA":    ("#dc2626", "#fef2f2", "#fecaca"),
    "CABECEO":           ("#dc2626", "#fef2f2", "#fecaca"),
    "AUSENTE":           ("#64748b", "#f8fafc", "#e2e8f0"),
    "LECTURA_INESTABLE": ("#64748b", "#f8fafc", "#e2e8f0"),
    "ERROR":             ("#dc2626", "#fef2f2", "#fecaca"),
}

LEVEL_COLORS = {
    "OBSERVACION":       "#d97706",
    "RIESGO_LEVE":       "#ea580c",
    "RIESGO_CONFIRMADO": "#dc2626",
    "RIESGO_CRITICO":    "#991b1b",
}

METRIC_CHIP_STYLE = (
    "font-size: 12px; color: #475569; background: #f8fafc; "
    "padding: 8px 10px; border-radius: 8px; border: 1px solid #e2e8f0;"
)

METRIC_CHIP_ALERT_STYLE = (
    "font-size: 12px; color: #92400e; background: #fffbeb; "
    "padding: 8px 10px; border-radius: 8px; border: 1px solid #fde68a;"
)

METRIC_CHIP_OK_STYLE = (
    "font-size: 12px; color: #065f46; background: #ecfdf5; "
    "padding: 8px 10px; border-radius: 8px; border: 1px solid #a7f3d0;"
)

METRIC_CHIP_DANGER_STYLE = (
    "font-size: 12px; color: #991b1b; background: #fef2f2; "
    "padding: 8px 10px; border-radius: 8px; border: 1px solid #fecaca;"
)

BTN_VOICE_ON = (
    "QPushButton { background: #0f2040; color: #bae6fd; font-size: 11px; font-weight: 600; "
    "border: none; border-radius: 7px; padding: 6px 16px; }"
    "QPushButton:hover { background: #1e3a5f; }"
    "QPushButton:disabled { background: #e2e8f0; color: #94a3b8; border: none; }"
)

BTN_VOICE_OFF = (
    "QPushButton { background: #fff7ed; color: #92400e; font-size: 11px; font-weight: 600; "
    "border: 1px solid #fde68a; border-radius: 7px; padding: 6px 16px; }"
    "QPushButton:hover { background: #fffbeb; }"
)

BTN_EXPORT = (
    "QPushButton { background: #1d4ed8; color: #ffffff; font-size: 11px; font-weight: 600; "
    "border: none; border-radius: 7px; padding: 8px 16px; }"
    "QPushButton:hover { background: #1e40af; }"
)

BANNER_CRITICAL = (
    "font-size: 13px; font-weight: 700; color: #991b1b; background: #fef2f2; "
    "padding: 10px 14px; border-radius: 10px; border: 1px solid #fecaca;"
)

VIDEO_FEED_IDLE = (
    "background-color: #0f172a; border: 2px solid #1e3a5f; border-radius: 10px; "
    "color: #475569; font-size: 13px;"
)

VIDEO_FEED_ERROR = (
    "background-color: #0f172a; border: 2px solid #dc2626; border-radius: 10px; "
    "color: #fca5a5; font-size: 13px; font-weight: 600;"
)

INCIDENT_PANEL_STYLE = (
    "font-size: 12px; color: #334155; background: #f8fafc; "
    "padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;"
)

NAV_BTN_STYLE = (
    "QPushButton { background: transparent; border: none; "
    "color: #94a3b8; font-size: 11px; font-weight: 500; border-radius: 8px; "
    "padding: 8px 4px; text-align: center; }"
    "QPushButton:hover { background: #1e3a5f; color: #e2e8f0; }"
)

NAV_BTN_ACTIVE_STYLE = (
    "QPushButton { background: #1e3a5f; border: none; "
    "color: #38bdf8; font-size: 11px; font-weight: 600; border-radius: 8px; "
    "padding: 8px 4px; text-align: center; }"
)

STAT_LABEL_STYLE = "font-size: 11px; color: #64748b;"
STAT_VALUE_STYLE = "font-size: 12px; font-weight: 700; color: #1e3a5f;"

NAV_BUTTON_BASE = (
    "QPushButton {"
    "background: transparent; border: none; border-radius: 10px;"
    "padding: 12px 14px; text-align: left; }"
    "QPushButton:hover { background: rgba(59, 130, 246, 0.12); }"
)

NAV_BUTTON_ACTIVE = (
    "QPushButton {"
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
    "stop:0 #0a7abf, stop:1 #1095c7);"
    "border: 1px solid #22b3dc; border-radius: 10px;"
    "padding: 12px 14px; text-align: left; }"
    "QPushButton:hover { background: #0f8fc4; }"
)

HEADER_CHIP_STYLE = (
    "font-size: 12px; color: #1e3a5f; background: #f1f8ff; "
    "padding: 6px 10px; border-radius: 9px; border: 1px solid #d2e8ff;"
)
