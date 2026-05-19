from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ...domain.entities.trabajador import SesionTrabajador


class MemoriaUsuarioJsonAdapter:
    def __init__(
        self,
        profile_path: Path,
        events_path: Path,
        summary_path: Path | None = None,
        session_report_path: Path | None = None,
    ) -> None:
        self._profile_path = profile_path
        self._events_path = events_path
        self._summary_path = summary_path or events_path.with_name("incident_summary.json")
        self._session_report_path = session_report_path or events_path.with_name("session_report.json")
        for path in (
            self._profile_path.parent,
            self._events_path.parent,
            self._summary_path.parent,
            self._session_report_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def cargar_sesion_base(self) -> dict[str, float]:
        try:
            data = json.loads(self._profile_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}

    def guardar_sesion_base(self, sesion: SesionTrabajador) -> None:
        payload = {
            "base_ancho_hombros": sesion.base_ancho_hombros,
            "base_ratio_y": sesion.base_ratio_y,
            "base_z_nariz_rel": sesion.base_z_nariz_rel,
            "base_ancho_cara": sesion.base_ancho_cara,
            "base_ear": sesion.base_ear,
            "base_mar": sesion.base_mar,
            "muestras_calibracion": float(sesion.muestras_calibracion),
            "updated_at": datetime.now().timestamp(),
        }
        self._profile_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def registrar_evento(self, evento: dict[str, object]) -> None:
        eventos = self._leer_eventos()
        eventos.append(evento)
        eventos = eventos[-300:]
        self._events_path.write_text(json.dumps(eventos, ensure_ascii=False, indent=2), encoding="utf-8")
        self._summary_path.write_text(
            json.dumps(self._construir_resumen_incidencias(eventos), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def obtener_resumen_incidencias(self) -> dict[str, object]:
        try:
            resumen = json.loads(self._summary_path.read_text(encoding="utf-8"))
            if isinstance(resumen, dict):
                return resumen
        except Exception:
            pass
        eventos = self._leer_eventos()
        resumen = self._construir_resumen_incidencias(eventos)
        try:
            self._summary_path.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return resumen

    def guardar_reporte_sesion(self, reporte: dict[str, object]) -> None:
        self._session_report_path.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _leer_eventos(self) -> list[dict[str, object]]:
        try:
            eventos = json.loads(self._events_path.read_text(encoding="utf-8"))
            if isinstance(eventos, list):
                return [evento for evento in eventos if isinstance(evento, dict)]
        except Exception:
            pass
        return []

    def _construir_resumen_incidencias(self, eventos: list[dict[str, object]]) -> dict[str, object]:
        conteos: dict[str, int] = {}
        categoria_conteos: dict[str, int] = {}
        recientes = []
        for evento in eventos:
            estado = str(evento.get("estado", "DESCONOCIDO"))
            categoria = str(evento.get("categoria", "general"))
            conteos[estado] = conteos.get(estado, 0) + 1
            categoria_conteos[categoria] = categoria_conteos.get(categoria, 0) + 1

        for evento in reversed(eventos[-5:]):
            recientes.append(
                {
                    "timestamp": evento.get("timestamp", ""),
                    "estado": evento.get("estado", ""),
                    "categoria": evento.get("categoria", ""),
                    "severidad": evento.get("severidad", ""),
                    "descripcion": evento.get("descripcion", ""),
                    "nivel_riesgo": evento.get("nivel_riesgo", ""),
                    "duracion_riesgo_segundos": evento.get("duracion_riesgo_segundos", ""),
                    "calidad_deteccion": evento.get("calidad_deteccion", ""),
                    "accion_recomendada": evento.get("accion_recomendada", ""),
                    "evidencias": evento.get("evidencias", []),
                }
            )

        return {
            "total_incidencias": len(eventos),
            "por_estado": conteos,
            "por_categoria": categoria_conteos,
            "ultimas_incidencias": recientes,
            "updated_at": datetime.now().isoformat(),
        }
