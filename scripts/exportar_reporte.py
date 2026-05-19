from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.servicios import ReporteExportService
from src.infrastructure.config import SafeWorkSettings


def main() -> None:
    settings = SafeWorkSettings.from_runtime()
    exportador = ReporteExportService(
        settings.profile_path,
        settings.events_path,
        settings.incidents_summary_path,
        settings.session_report_path,
    )
    reporte = exportador.exportar()
    print(f"Reporte HTML: {reporte.html_path}")
    print(f"Reporte JSON: {reporte.json_path}")


if __name__ == "__main__":
    main()
