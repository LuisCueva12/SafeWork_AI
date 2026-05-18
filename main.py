from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from src.infrastructure.adaptadores.safework_app import SafeWorkApp


def ejecutar() -> int:
    app = QApplication(sys.argv)

    try:
        import qdarktheme

        qdarktheme.setup_theme("dark")
    except Exception:
        pass

    ventana = SafeWorkApp()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(ejecutar())
