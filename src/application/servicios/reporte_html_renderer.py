from __future__ import annotations

from datetime import datetime
from html import escape

from .reporte_analisis_service import ReporteAnalisisService


class ReporteHtmlRenderer:
    def renderizar(self, payload: dict[str, object]) -> str:
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
        metricas = resumen.get("metricas_agregadas", {})
        if not isinstance(metricas, dict):
            metricas = {}
        contexto = sesion.get("contexto_operativo", {})
        if not isinstance(contexto, dict):
            contexto = {}
        periodos = metricas.get("periodos", {})
        if not isinstance(periodos, dict):
            periodos = {}
        recomendaciones = analisis.get("recomendaciones", [])
        if not isinstance(recomendaciones, list):
            recomendaciones = [recomendaciones]

        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte SafeWork AI</title>
  <style>
    :root {{ --ink: #0f172a; --muted: #64748b; --line: #dbe4ef; --soft: #f8fafc; --brand: #1d4ed8; --ok: #15803d; --warn: #b45309; --bad: #b91c1c; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #eef3f9; color: var(--ink); }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 30px; }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: -0.02em; }}
    h2 {{ margin: 30px 0 8px; color: var(--brand); font-size: 18px; }}
    h3 {{ margin: 0 0 10px; font-size: 15px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; background: linear-gradient(135deg, #0f172a, #1e3a8a); color: white; border-radius: 18px; padding: 24px; box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18); }}
    .hero .muted {{ color: #bfdbfe; }}
    .muted {{ color: var(--muted); }}
    .section-note {{ margin: 0 0 14px; color: var(--muted); line-height: 1.55; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
    .card {{ background: white; border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }}
    .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }}
    .value {{ font-size: 23px; font-weight: 800; margin-top: 5px; line-height: 1.1; }}
    .hint {{ margin-top: 8px; color: var(--muted); font-size: 12px; line-height: 1.4; }}
    .badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: #dbeafe; color: #1e40af; font-weight: 700; font-size: 12px; }}
    .pill {{ display: inline-block; padding: 7px 12px; border-radius: 999px; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); color: white; font-weight: 700; font-size: 12px; white-space: nowrap; }}
    ul {{ margin: 10px 0 0; padding-left: 20px; }}
    li {{ margin-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 12px 13px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #0f172a; color: white; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: none; }}
    .estado-ok {{ color: var(--ok); font-weight: 800; }}
    .estado-warn {{ color: var(--warn); font-weight: 800; }}
    .estado-bad {{ color: var(--bad); font-weight: 800; }}
    .small {{ font-size: 12px; color: var(--muted); }}
    .footer {{ margin-top: 28px; font-size: 12px; color: var(--muted); }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .hero {{ flex-direction: column; }} }}
  </style>
</head>
<body>
<main>
  <header class="hero">
    <div>
      <h1>Reporte SafeWork AI</h1>
      <p class="muted">Monitoreo de ergonomia, fatiga y proximidad frente al computador.</p>
      <p class="muted">Exportado: {escape(self._formato_fecha(payload.get("exportado_en", "")))}</p>
    </div>
    <span class="pill">{escape(str(analisis.get("estado_sistema", "SIN DIAGNOSTICO")))}</span>
  </header>

  <h2>Identificacion</h2>
  <p class="section-note">Datos principales del usuario monitoreado y del contexto donde se genero el reporte.</p>
  <section class="grid">
    {self._card("Persona analizada", contexto.get("nombre", contexto.get("trabajador", "N/D")))}
    {self._card("Rol", self._texto_legible(contexto.get("rol", "N/D")))}
    {self._card("Tipo de usuario", self._texto_legible(contexto.get("tipo_usuario", "N/D")))}
    {self._card("Puesto", self._texto_legible(contexto.get("puesto", "N/D")))}
  </section>

  <h2>Resumen principal</h2>
  <p class="section-note">Vista corta con lo mas importante de la sesion.</p>
  <section class="grid">
    {self._card("Estado final", self._texto_legible(sesion.get("estado_actual", "N/D")))}
    {self._card("Incidencias", resumen.get("total_incidencias", 0))}
    {self._card("Alertas emitidas", sesion.get("alertas_emitidas", 0))}
    {self._card("Calidad de lectura", self._formato_pct(sesion.get("calidad_ultima_lectura")))}
    {self._card("Duracion", self._formato_duracion(sesion.get("duracion_sesion_segundos")))}
    {self._card("Lecturas validas", sesion.get("lecturas_validas", 0))}
    {self._card("Incidencias hoy", periodos.get("hoy", 0))}
    {self._card("Incidencias 7 dias", periodos.get("ultimos_7_dias", 0))}
  </section>

  <h2>Indicadores clave</h2>
  <table>
    <tr><th>Indicador</th><th>Valor</th><th>Lectura</th></tr>
    {self._fila_kv("Empresa", contexto.get("empresa", "N/D"), "Organizacion asociada al sistema.")}
    {self._fila_kv("Area", self._texto_legible(contexto.get("area", "N/D")), "Area o grupo al que pertenece el usuario.")}
    {self._fila_kv("Perfil de riesgo", self._texto_legible(contexto.get("perfil_riesgo", "N/D")), "Nivel de exigencia esperado en la supervision.")}
    {self._fila_kv("Sensibilidad", self._texto_legible(sesion.get("sensibilidad", "N/D")), "Configuracion activa del monitoreo.")}
    {self._fila_kv("Promedio de calidad", self._formato_pct(metricas.get("calidad_promedio")), "Confianza media de los eventos registrados.")}
  </table>

  <h2>Recomendaciones</h2>
  <div class="card">
    <span class="badge">Acciones sugeridas</span>
    <ul>{''.join(f"<li>{escape(str(item))}</li>" for item in recomendaciones[:5]) or '<li>Sin recomendaciones adicionales.</li>'}</ul>
  </div>

  {self._renderizar_eventos(eventos)}

  <h2>Perfil base del usuario</h2>
  <section class="grid">
    {self._card("Ojos base", self._formato_numero(perfil.get("base_ear")))}
    {self._card("Boca base", self._formato_numero(perfil.get("base_mar")))}
    {self._card("Referencia facial", self._formato_numero(perfil.get("base_ancho_cara")))}
    {self._card("Muestras de calibracion", self._formato_numero(perfil.get("muestras_calibracion")))}
  </section>

  <p class="footer">Este reporte no incluye imagenes ni video. Solo contiene metricas, evidencias y eventos locales de SafeWork AI.</p>
</main>
</body>
</html>"""

    def _renderizar_eventos(self, eventos: list[object]) -> str:
        filas_eventos = "\n".join(
            self._fila_evento(evento) for evento in eventos[-12:] if isinstance(evento, dict)
        )
        if not filas_eventos:
            filas_eventos = "<tr><td colspan='5'>No hay incidencias registradas en esta sesion.</td></tr>"
        return f"""
  <h2>Alertas relevantes</h2>
  <p class="section-note">Solo se muestran las alertas mas importantes de la sesion.</p>
  <table>
    <tr>
      <th>Fecha</th><th>Indicador</th><th>Nivel</th><th>Duracion</th><th>Accion recomendada</th>
    </tr>
    {filas_eventos}
  </table>
"""

    @staticmethod
    def _card(label: str, value: object, detail: str | None = None, *, html_value: bool = False) -> str:
        valor = str(value) if html_value else escape(str(value))
        detalle = f"<div class='hint'>{escape(detail)}</div>" if detail else ""
        return f"<div class='card'><div class='label'>{escape(label)}</div><div class='value'>{valor}</div>{detalle}</div>"

    @staticmethod
    def _fila_kv(label: str, value: object, detail: str | None = None) -> str:
        if detail is None:
            return f"<tr><td>{escape(label)}</td><td>{escape(str(value))}</td></tr>"
        return f"<tr><td>{escape(label)}</td><td>{escape(str(value))}</td><td>{escape(detail)}</td></tr>"

    @staticmethod
    def _fila_evento(evento: dict[str, object]) -> str:
        return (
            "<tr>"
            f"<td>{escape(ReporteHtmlRenderer._formato_fecha(evento.get('timestamp', '')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._texto_legible(evento.get('estado', '')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._texto_legible(evento.get('nivel_riesgo', evento.get('severidad', ''))))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._formato_duracion(evento.get('duracion_riesgo_segundos')))}</td>"
            f"<td>{escape(str(evento.get('accion_recomendada', evento.get('descripcion', ''))))}</td>"
            "</tr>"
        )

    @staticmethod
    def _parsear_fecha(value: object) -> datetime | None:
        return ReporteAnalisisService.parsear_fecha(value)

    @staticmethod
    def _formato_fecha(value: object) -> str:
        fecha = ReporteHtmlRenderer._parsear_fecha(value)
        if fecha is None:
            return str(value) if value else "N/D"
        return fecha.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _formato_fecha_timestamp(value: object) -> str:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return ReporteHtmlRenderer._formato_fecha(value)
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            return "N/D"

    @staticmethod
    def _formato_duracion(value: object) -> str:
        try:
            segundos = max(0.0, float(value))
        except (TypeError, ValueError):
            return "N/D"
        minutos = int(segundos // 60)
        resto = int(round(segundos % 60))
        if minutos <= 0:
            return f"{resto} s"
        return f"{minutos} min {resto} s"

    @staticmethod
    def _formato_numero(value: object) -> str:
        try:
            numero = float(value)
        except (TypeError, ValueError):
            return "N/D"
        if numero.is_integer():
            return str(int(numero))
        return f"{numero:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _formato_pct(value: object) -> str:
        numero = ReporteHtmlRenderer._normalizar_porcentaje(ReporteHtmlRenderer._to_float(value, None))
        if numero is None:
            return "N/D"
        return f"{numero:.1f}%"

    @staticmethod
    def _texto_legible(value: object) -> str:
        return ReporteAnalisisService.texto_legible(value)

    @staticmethod
    def _texto_clave_distribucion(value: object) -> str:
        texto = str(value).strip()
        if any(caracter.isdigit() for caracter in texto) and ("-" in texto or "W" in texto.upper()):
            return texto
        return ReporteHtmlRenderer._texto_legible(texto)

    @staticmethod
    def _clase_estado_operativo(value: str) -> str:
        texto = value.upper()
        if any(token in texto for token in ("ALTA", "BUENA", "OPERATIVO")):
            return "estado-ok"
        if any(token in texto for token in ("MEDIA", "PARCIAL", "PENDIENTE", "AJUSTE")):
            return "estado-warn"
        if any(token in texto for token in ("INSUFICIENTE", "REQUIERE", "DEBIL")):
            return "estado-bad"
        return "estado-warn"

    @staticmethod
    def _to_float(value: object, default: float | None) -> float | None:
        return ReporteAnalisisService.to_float(value, default)

    @staticmethod
    def _normalizar_porcentaje(value: float | None) -> float | None:
        return ReporteAnalisisService.normalizar_porcentaje(value)
