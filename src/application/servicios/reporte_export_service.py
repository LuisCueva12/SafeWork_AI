from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .ofuscacion_json import desofuscar
from .reporte_analisis_service import ReporteAnalisisService
from .reporte_pdf_renderer import ReportePdfRenderer


@dataclass(frozen=True)
class ReporteExportado:
    json_path: Path
    pdf_path: Path
    historial_pdf_path: Path


class ReporteExportService:
    def __init__(
        self,
        profile_path: Path,
        events_path: Path,
        summary_path: Path,
        session_report_path: Path,
        output_dir: Path | None = None,
        validation_labels_path: Path | None = None,
        analisis_service: ReporteAnalisisService | None = None,
        pdf_renderer: ReportePdfRenderer | None = None,
    ) -> None:
        self._profile_path = profile_path
        self._events_path = events_path
        self._summary_path = summary_path
        self._session_report_path = session_report_path
        self._output_dir = output_dir or (Path.home() / "Documents" / "SafeWork AI Reports")
        self._validation_labels_path = validation_labels_path
        self._analisis = analisis_service or ReporteAnalisisService()
        self._pdf_renderer = pdf_renderer or ReportePdfRenderer()

    def exportar(self, output_dir: Path | None = None) -> ReporteExportado:
        destino = self._resolver_destino(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_jornada = destino / f"safework_reporte_jornada_{timestamp}"
        base_historial = destino / f"safework_historial_global_{timestamp}"
        perfil_usuario = self._leer_json(self._profile_path, {})
        reporte_sesion = self._leer_json(self._session_report_path, {})
        if not isinstance(perfil_usuario, dict):
            perfil_usuario = {}
        if not isinstance(reporte_sesion, dict):
            reporte_sesion = {}
        reporte_sesion["contexto_operativo"] = self._mezclar_contexto_operativo(
            reporte_sesion.get("contexto_operativo", {}),
            perfil_usuario,
        )

        payload = self._analisis.preparar_payload(
            {
                "exportado_en": datetime.now().isoformat(),
                "perfil_usuario": perfil_usuario,
                "resumen_incidencias": self._leer_json(self._summary_path, {}),
                "reporte_sesion": reporte_sesion,
                "eventos": self._leer_json(self._events_path, []),
                "validacion_humana": self._leer_json(self._validation_labels_path, [])
                if self._validation_labels_path
                else [],
            }
        )

        json_path = base_jornada.with_suffix(".json")
        pdf_path = base_jornada.with_suffix(".pdf")
        historial_pdf_path = base_historial.with_suffix(".pdf")
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        pdf_path.write_bytes(self._pdf_renderer.renderizar(payload, modo="jornada"))
        historial_pdf_path.write_bytes(self._pdf_renderer.renderizar(payload, modo="global"))
        return ReporteExportado(json_path=json_path, pdf_path=pdf_path, historial_pdf_path=historial_pdf_path)

    def _resolver_destino(self, output_dir: Path | None) -> Path:
        candidatos = [
            output_dir,
            self._output_dir,
            self._session_report_path.parent / "exports",
            Path.cwd() / "reportes_safework",
            Path(tempfile.gettempdir()) / "SafeWork AI Reports",
        ]
        for candidato in candidatos:
            if candidato is None:
                continue
            try:
                candidato.mkdir(parents=True, exist_ok=True)
                prueba = candidato / ".safework_write_test"
                prueba.write_text("ok", encoding="utf-8")
                prueba.unlink(missing_ok=True)
                return candidato
            except Exception:
                continue
        raise PermissionError("No se encontro una carpeta disponible para exportar el reporte.")

    @staticmethod
    def _mezclar_contexto_operativo(contexto: object, perfil: dict[str, object]) -> dict[str, object]:
        base = dict(contexto) if isinstance(contexto, dict) else {}
        mapping = {
            "nombre": "nombre",
            "identificador": "trabajador",
            "rol": "rol",
            "tipo_usuario": "tipo_usuario",
            "area": "area",
            "empresa": "empresa",
            "puesto": "puesto",
            "perfil_riesgo": "perfil_riesgo",
        }
        for origen, destino in mapping.items():
            valor = str(perfil.get(origen, "")).strip()
            if valor:
                base[destino] = valor
        return base

    @staticmethod
    def _leer_json(path: Path | None, default):
        if path is None:
            return default
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            try:
                contenido = path.read_text(encoding="utf-8")
                data = json.loads(desofuscar(contenido))
            except Exception:
                return default
        return data
