from __future__ import annotations

import os
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.infrastructure.adaptadores.safework_app import SafeWorkApp


def ejecutar() -> int:
    # Evita warnings ruidosos de fuentes legacy de Windows que no afectan la UI
    # final y fija una base visual consistente para toda la app.
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    ventana = SafeWorkApp()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(ejecutar())
