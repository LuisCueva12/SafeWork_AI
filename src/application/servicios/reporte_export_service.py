from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path


@dataclass(frozen=True)
class ReporteExportado:
    html_path: Path
    json_path: Path


class ReporteExportService:
    def __init__(
        self,
        profile_path: Path,
        events_path: Path,
        summary_path: Path,
        session_report_path: Path,
        output_dir: Path | None = None,
    ) -> None:
        self._profile_path = profile_path
        self._events_path = events_path
        self._summary_path = summary_path
        self._session_report_path = session_report_path
        self._output_dir = output_dir or (Path.home() / "Documents" / "SafeWork AI Reports")

    def exportar(self, output_dir: Path | None = None) -> ReporteExportado:
        destino = self._resolver_destino(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = destino / f"safework_reporte_{timestamp}"

        payload = {
            "exportado_en": datetime.now().isoformat(),
            "perfil_usuario": self._leer_json(self._profile_path, {}),
            "resumen_incidencias": self._leer_json(self._summary_path, {}),
            "reporte_sesion": self._leer_json(self._session_report_path, {}),
            "eventos": self._leer_json(self._events_path, []),
        }
        payload["analisis_calidad_datos"] = self._analizar_calidad_datos(payload)

        json_path = base.with_suffix(".json")
        html_path = base.with_suffix(".html")
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._renderizar_html(payload), encoding="utf-8")
        return ReporteExportado(html_path=html_path, json_path=json_path)

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
    def _leer_json(path: Path, default):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
        return data

    def _renderizar_html(self, payload: dict[str, object]) -> str:
        eventos = payload.get("eventos", [])
        if not isinstance(eventos, list):
            eventos = []
        resumen = payload.get("resumen_incidencias", {})
        if not isinstance(resumen, dict):
            resumen = {}
        sesion = payload.get("reporte_sesion", {})
        if not isinstance(sesion, dict):
            sesion = {}
        perfil = payload.get("perfil_usuario", {})
        if not isinstance(perfil, dict):
            perfil = {}
        analisis = payload.get("analisis_calidad_datos", {})
        if not isinstance(analisis, dict):
            analisis = {}

        filas_eventos = "\n".join(self._fila_evento(evento) for evento in eventos[-120:] if isinstance(evento, dict))
        if not filas_eventos:
            filas_eventos = "<tr><td colspan='7'>No hay incidencias registradas.</td></tr>"

        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte SafeWork AI</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px; }}
    h1 {{ margin: 0; font-size: 30px; }}
    h2 {{ margin-top: 28px; color: #1e40af; font-size: 18px; }}
    .muted {{ color: #64748b; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }}
    .label {{ color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .value {{ font-size: 22px; font-weight: 800; margin-top: 4px; }}
    .insight {{ line-height: 1.55; }}
    .badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: #dbeafe; color: #1e40af; font-weight: 700; font-size: 12px; }}
    .meter {{ height: 10px; background: #e2e8f0; border-radius: 999px; overflow: hidden; margin-top: 10px; }}
    .bar {{ height: 100%; background: linear-gradient(90deg, #2563eb, #22c55e); }}
    ul {{ margin: 10px 0 0; padding-left: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 11px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #0f172a; color: white; }}
    code {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 12px; }}
    .footer {{ margin-top: 28px; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
<main>
  <h1>Reporte SafeWork AI</h1>
  <p class="muted">Exportado: {escape(str(payload.get("exportado_en", "")))}</p>

  <section class="grid">
    {self._card("Incidencias", resumen.get("total_incidencias", 0))}
    {self._card("Alertas emitidas", sesion.get("alertas_emitidas", 0))}
    {self._card("Lecturas validas", sesion.get("lecturas_validas", 0))}
    {self._card("Calidad ultima", sesion.get("calidad_ultima_lectura", "N/D"))}
  </section>

  {self._renderizar_analisis(analisis)}

  <h2>Resumen de sesion</h2>
  <table>
    <tr><th>Campo</th><th>Valor</th></tr>
    {self._fila_kv("Estado actual", sesion.get("estado_actual", "N/D"))}
    {self._fila_kv("Duracion sesion (s)", sesion.get("duracion_sesion_segundos", "N/D"))}
    {self._fila_kv("Sensibilidad", sesion.get("sensibilidad", "N/D"))}
    {self._fila_kv("Muestras aprendizaje", sesion.get("muestras_aprendizaje", "N/D"))}
  </table>

  <h2>Incidencias registradas</h2>
  <table>
    <tr>
      <th>Fecha</th><th>Estado</th><th>Nivel</th><th>Duracion</th>
      <th>Calidad</th><th>Evidencias</th><th>Accion recomendada</th>
    </tr>
    {filas_eventos}
  </table>

  <h2>Perfil aprendido</h2>
  <div class="card"><code>{escape(json.dumps(perfil, ensure_ascii=False, indent=2))}</code></div>

  <p class="footer">Este reporte no incluye imagenes ni video. Solo contiene metricas, evidencias y eventos locales de SafeWork AI.</p>
</main>
</body>
</html>"""

    def _analizar_calidad_datos(self, payload: dict[str, object]) -> dict[str, object]:
        eventos_raw = payload.get("eventos", [])
        eventos = [evento for evento in eventos_raw if isinstance(evento, dict)] if isinstance(eventos_raw, list) else []
        sesion = payload.get("reporte_sesion", {})
        if not isinstance(sesion, dict):
            sesion = {}

        lecturas_validas = self._to_float(sesion.get("lecturas_validas"), 0.0) or 0.0
        alertas_emitidas = self._to_float(sesion.get("alertas_emitidas"), 0.0) or 0.0
        hay_telemetria = lecturas_validas > 0 or alertas_emitidas > 0 or bool(sesion)

        campos_obligatorios = (
            "timestamp",
            "estado",
            "nivel_riesgo",
            "duracion_riesgo_segundos",
            "calidad_deteccion",
            "evidencias",
            "accion_recomendada",
        )
        if eventos:
            campos_totales = len(eventos) * len(campos_obligatorios)
            campos_completos = sum(
                1
                for evento in eventos
                for campo in campos_obligatorios
                if self._campo_util(evento, campo)
            )
            completitud_pct = round((campos_completos / campos_totales) * 100, 1)
            eventos_con_evidencias = sum(1 for evento in eventos if self._campo_util(evento, "evidencias"))
            cobertura_evidencias_pct = round((eventos_con_evidencias / len(eventos)) * 100, 1)
            calidades = [
                self._normalizar_porcentaje(self._to_float(evento.get("calidad_deteccion"), None))
                for evento in eventos
            ]
            calidades_validas = [calidad for calidad in calidades if calidad is not None]
            eventos_con_calidad = len(calidades_validas)
            cobertura_calidad_pct = round((eventos_con_calidad / len(eventos)) * 100, 1)
            calidad_promedio = round(sum(calidades_validas) / len(calidades_validas), 1) if calidades_validas else None
        else:
            completitud_pct = 100.0 if hay_telemetria else 0.0
            eventos_con_evidencias = 0
            cobertura_evidencias_pct = 100.0 if hay_telemetria else 0.0
            eventos_con_calidad = 0
            cobertura_calidad_pct = 100.0 if hay_telemetria else 0.0
            calidad_promedio = self._normalizar_porcentaje(self._to_float(sesion.get("calidad_ultima_lectura"), None))

        puntaje_sensor = calidad_promedio if calidad_promedio is not None else (75.0 if hay_telemetria else 0.0)
        cobertura_sesion_pct = 100.0 if lecturas_validas > 0 else (70.0 if hay_telemetria else 0.0)
        puntaje = round(
            (completitud_pct * 0.35)
            + (cobertura_evidencias_pct * 0.25)
            + (puntaje_sensor * 0.25)
            + (cobertura_sesion_pct * 0.15),
            1,
        )

        diagnostico, estado_sistema = self._diagnosticar_sistema(puntaje, len(eventos), lecturas_validas)
        recomendaciones = self._crear_recomendaciones(
            total_eventos=len(eventos),
            lecturas_validas=lecturas_validas,
            alertas_emitidas=alertas_emitidas,
            completitud_pct=completitud_pct,
            cobertura_evidencias_pct=cobertura_evidencias_pct,
            calidad_promedio=calidad_promedio,
        )

        return {
            "puntaje_calidad_datos": puntaje,
            "estado_sistema": estado_sistema,
            "diagnostico": diagnostico,
            "total_eventos": len(eventos),
            "lecturas_validas": int(lecturas_validas),
            "alertas_emitidas": int(alertas_emitidas),
            "campos_obligatorios_completos_pct": completitud_pct,
            "eventos_con_evidencias": eventos_con_evidencias,
            "cobertura_evidencias_pct": cobertura_evidencias_pct,
            "eventos_con_calidad": eventos_con_calidad,
            "cobertura_calidad_pct": cobertura_calidad_pct,
            "calidad_promedio_eventos": calidad_promedio,
            "recomendaciones": recomendaciones,
        }

    @staticmethod
    def _diagnosticar_sistema(puntaje: float, total_eventos: int, lecturas_validas: float) -> tuple[str, str]:
        if lecturas_validas <= 0 and total_eventos <= 0:
            return (
                "No hay suficientes lecturas para evaluar la sesion. Ejecuta el monitoreo por mas tiempo.",
                "DATOS INSUFICIENTES",
            )
        if total_eventos == 0:
            return (
                "Sesion sin incidencias registradas. El sistema estuvo observando y no encontro riesgos persistentes.",
                "OPERATIVO SIN INCIDENTES",
            )
        if puntaje >= 85:
            return (
                "Datos consistentes: las incidencias tienen evidencia, calidad y accion recomendada.",
                "CONFIABILIDAD ALTA",
            )
        if puntaje >= 70:
            return (
                "Sistema operativo para piloto B2B. Hay datos utiles, pero conviene mejorar cobertura o calidad.",
                "CONFIABILIDAD MEDIA",
            )
        if puntaje >= 50:
            return (
                "El sistema detecta eventos, pero el reporte necesita mas evidencia para auditoria profesional.",
                "REQUIERE AJUSTE",
            )
        return (
            "Datos debiles para tomar decisiones. Revisa camara, iluminacion, calibracion y registro de eventos.",
            "REQUIERE VALIDACION",
        )

    @staticmethod
    def _crear_recomendaciones(
        *,
        total_eventos: int,
        lecturas_validas: float,
        alertas_emitidas: float,
        completitud_pct: float,
        cobertura_evidencias_pct: float,
        calidad_promedio: float | None,
    ) -> list[str]:
        recomendaciones: list[str] = []
        if lecturas_validas <= 0:
            recomendaciones.append("Ejecutar una sesion de al menos 5 a 10 minutos para generar una muestra valida.")
        if calidad_promedio is not None and calidad_promedio < 70:
            recomendaciones.append("Mejorar iluminacion, encuadre y distancia a la camara para subir la calidad de deteccion.")
        if total_eventos > 0 and cobertura_evidencias_pct < 80:
            recomendaciones.append("Revisar que cada incidencia guarde evidencias claras de postura, distancia o fatiga.")
        if total_eventos > 0 and completitud_pct < 90:
            recomendaciones.append("Completar campos de auditoria: fecha, nivel, duracion, calidad, evidencias y accion.")
        if alertas_emitidas > 0 and total_eventos == 0:
            recomendaciones.append("Validar que las alertas visibles tambien se registren como eventos auditables.")
        if total_eventos == 0 and lecturas_validas > 0:
            recomendaciones.append("Mantener el monitoreo activo; una sesion sin incidentes tambien es un resultado valido.")
        if not recomendaciones:
            recomendaciones.append("Datos listos para revision operativa. Continuar validando con usuarios reales de oficina.")
        return recomendaciones

    def _renderizar_analisis(self, analisis: dict[str, object]) -> str:
        puntaje = self._normalizar_porcentaje(self._to_float(analisis.get("puntaje_calidad_datos"), 0.0)) or 0.0
        recomendaciones = analisis.get("recomendaciones", [])
        if isinstance(recomendaciones, list):
            items = "".join(f"<li>{escape(str(item))}</li>" for item in recomendaciones)
        else:
            items = f"<li>{escape(str(recomendaciones))}</li>"

        return f"""
  <h2>Analisis de calidad de datos</h2>
  <section class="grid">
    {self._card("Puntaje de datos", f"{puntaje:.1f}/100")}
    {self._card("Estado del sistema", analisis.get("estado_sistema", "N/D"))}
    {self._card("Cobertura evidencia", self._formato_pct(analisis.get("cobertura_evidencias_pct")))}
    {self._card("Calidad promedio", self._formato_pct(analisis.get("calidad_promedio_eventos")))}
  </section>
  <div class="card insight">
    <span class="badge">Diagnostico operativo</span>
    <div class="meter"><div class="bar" style="width: {puntaje:.1f}%"></div></div>
    <p>{escape(str(analisis.get("diagnostico", "Sin diagnostico disponible.")))}</p>
    <strong>Recomendaciones</strong>
    <ul>{items}</ul>
  </div>
"""

    @staticmethod
    def _card(label: str, value: object) -> str:
        return f"<div class='card'><div class='label'>{escape(label)}</div><div class='value'>{escape(str(value))}</div></div>"

    @staticmethod
    def _fila_kv(label: str, value: object) -> str:
        return f"<tr><td>{escape(label)}</td><td>{escape(str(value))}</td></tr>"

    @staticmethod
    def _fila_evento(evento: dict[str, object]) -> str:
        evidencias = evento.get("evidencias", [])
        if isinstance(evidencias, list):
            evidencias_texto = ", ".join(str(item) for item in evidencias)
        else:
            evidencias_texto = str(evidencias)
        return (
            "<tr>"
            f"<td>{escape(str(evento.get('timestamp', '')))}</td>"
            f"<td>{escape(str(evento.get('estado', '')))}</td>"
            f"<td>{escape(str(evento.get('nivel_riesgo', evento.get('severidad', ''))))}</td>"
            f"<td>{escape(str(evento.get('duracion_riesgo_segundos', '')))} s</td>"
            f"<td>{escape(str(evento.get('calidad_deteccion', '')))}</td>"
            f"<td>{escape(evidencias_texto)}</td>"
            f"<td>{escape(str(evento.get('accion_recomendada', evento.get('descripcion', ''))))}</td>"
            "</tr>"
        )

    @staticmethod
    def _campo_util(evento: dict[str, object], campo: str) -> bool:
        if campo not in evento:
            return False
        valor = evento.get(campo)
        return valor is not None and valor != "" and valor != [] and valor != {}

    @staticmethod
    def _to_float(value: object, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalizar_porcentaje(value: float | None) -> float | None:
        if value is None:
            return None
        if 0 < value <= 1:
            value *= 100
        return round(max(0.0, min(100.0, value)), 1)

    @staticmethod
    def _formato_pct(value: object) -> str:
        numero = ReporteExportService._normalizar_porcentaje(ReporteExportService._to_float(value, None))
        if numero is None:
            return "N/D"
        return f"{numero:.1f}%"
