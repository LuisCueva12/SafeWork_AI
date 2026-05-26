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
        validacion_modelo = payload.get("validacion_modelo", {})
        if not isinstance(validacion_modelo, dict):
            validacion_modelo = {}

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
    .grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }}
    .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }}
    .value {{ font-size: 23px; font-weight: 800; margin-top: 5px; line-height: 1.1; }}
    .hint {{ margin-top: 8px; color: var(--muted); font-size: 12px; line-height: 1.4; }}
    .insight {{ line-height: 1.6; }}
    .badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: #dbeafe; color: #1e40af; font-weight: 700; font-size: 12px; }}
    .pill {{ display: inline-block; padding: 7px 12px; border-radius: 999px; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); color: white; font-weight: 700; font-size: 12px; white-space: nowrap; }}
    .meter {{ height: 10px; background: #e2e8f0; border-radius: 999px; overflow: hidden; margin-top: 12px; }}
    .bar {{ height: 100%; background: linear-gradient(90deg, #2563eb, #22c55e); }}
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
    @media (max-width: 900px) {{ .grid, .grid-2 {{ grid-template-columns: 1fr; }} .hero {{ flex-direction: column; }} }}
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

  <h2>Resumen ejecutivo</h2>
  <p class="section-note">Esta seccion responde rapidamente que paso durante la sesion y si los datos son suficientes para una revision operativa.</p>
  <section class="grid">
    {self._card("Incidencias", resumen.get("total_incidencias", 0), "Eventos validados que generaron registro.")}
    {self._card("Alertas emitidas", sesion.get("alertas_emitidas", 0), "Avisos entregados al usuario por voz o interfaz.")}
    {self._card("Lecturas validas", sesion.get("lecturas_validas", 0), "Muestras en las que camara y sensores dieron datos utilizables.")}
    {self._card("Calidad ultima", self._formato_pct(sesion.get("calidad_ultima_lectura")), "Calidad de la lectura mas reciente.")}
  </section>

  {self._renderizar_analisis(analisis)}
  {self._renderizar_contexto_operativo(sesion.get("contexto_operativo", {}))}
  {self._renderizar_metricas_agregadas(resumen.get("metricas_agregadas", {}))}
  {self._renderizar_validacion_modelo(validacion_modelo)}
  {self._renderizar_resumen_sesion(sesion)}
  {self._renderizar_eventos(eventos)}
  {self._renderizar_perfil_aprendido(perfil)}

  <p class="footer">Este reporte no incluye imagenes ni video. Solo contiene metricas, evidencias y eventos locales de SafeWork AI.</p>
</main>
</body>
</html>"""

    def _renderizar_analisis(self, analisis: dict[str, object]) -> str:
        puntaje = self._normalizar_porcentaje(self._to_float(analisis.get("puntaje_calidad_datos"), 0.0)) or 0.0
        recomendaciones = analisis.get("recomendaciones", [])
        if isinstance(recomendaciones, list):
            items = "".join(f"<li>{escape(str(item))}</li>" for item in recomendaciones)
        else:
            items = f"<li>{escape(str(recomendaciones))}</li>"
        estado_css = self._clase_estado_operativo(str(analisis.get("estado_sistema", "")))

        return f"""
  <h2>Analisis de calidad de datos</h2>
  <p class="section-note">Indica si el reporte tiene lecturas suficientes, evidencias claras y campos completos para una revision confiable.</p>
  <section class="grid">
    {self._card("Puntaje de datos", f"{puntaje:.1f}/100", "Mientras mas alto, mas completo y confiable es el reporte.")}
    {self._card("Estado del sistema", f"<span class='{estado_css}'>{escape(self._texto_legible(analisis.get('estado_sistema', 'N/D')))}</span>", "Diagnostico general de operacion.", html_value=True)}
    {self._card("Evidencias completas", self._formato_pct(analisis.get("cobertura_evidencias_pct")), "Porcentaje de incidencias con pruebas registradas.")}
    {self._card("Calidad promedio", self._formato_pct(analisis.get("calidad_promedio_eventos")), "Confianza promedio de las detecciones registradas.")}
  </section>
  <div class="card insight">
    <span class="badge">Diagnostico operativo</span>
    <div class="meter"><div class="bar" style="width: {puntaje:.1f}%"></div></div>
    <p>{escape(str(analisis.get("diagnostico", "Sin diagnostico disponible.")))}</p>
    <strong>Recomendaciones</strong>
    <ul>{items}</ul>
  </div>
"""

    def _renderizar_contexto_operativo(self, contexto: object) -> str:
        if not isinstance(contexto, dict) or not contexto:
            contexto = {
                "empresa": "No especificada",
                "trabajador": "No especificado",
                "puesto": "No especificado",
                "perfil_riesgo": "No especificado",
                "camara": "No especificada",
                "iluminacion": "No especificada",
            }
        return f"""
  <h2>Contexto de validacion</h2>
  <p class="section-note">Estos datos permiten comparar sesiones de forma justa: no es lo mismo una webcam integrada con poca luz que una camara externa bien iluminada.</p>
  <section class="grid">
    {self._card("Empresa", contexto.get("empresa", "N/D"))}
    {self._card("Trabajador", contexto.get("trabajador", "N/D"))}
    {self._card("Puesto", self._texto_legible(contexto.get("puesto", "N/D")))}
    {self._card("Perfil de riesgo", self._texto_legible(contexto.get("perfil_riesgo", "N/D")))}
  </section>
  <table>
    <tr><th>Condicion</th><th>Valor registrado</th></tr>
    {self._fila_kv("Camara utilizada", self._texto_legible(contexto.get("camara", "N/D")))}
    {self._fila_kv("Condicion de iluminacion", self._texto_legible(contexto.get("iluminacion", "N/D")))}
  </table>
"""

    def _renderizar_metricas_agregadas(self, metricas: object) -> str:
        if not isinstance(metricas, dict):
            metricas = {}
        periodos = metricas.get("periodos", {})
        if not isinstance(periodos, dict):
            periodos = {}
        return f"""
  <h2>Historico agregado</h2>
  <p class="section-note">Resume la frecuencia de incidencias para seguimiento por trabajador, area o campana preventiva.</p>
  <section class="grid">
    {self._card("Hoy", periodos.get("hoy", 0), "Incidencias registradas durante el dia actual.")}
    {self._card("Ultimos 7 dias", periodos.get("ultimos_7_dias", 0), "Tendencia semanal del trabajador.")}
    {self._card("Ultimos 30 dias", periodos.get("ultimos_30_dias", 0), "Tendencia mensual para prevencion.")}
    {self._card("Calidad promedio", self._formato_pct(metricas.get("calidad_promedio")), "Promedio de confianza de los eventos historicos.")}
  </section>
  <div class="grid-2">
    {self._tabla_distribucion("Incidencias por dia", "Fecha", "Cantidad", metricas.get("por_dia", {}))}
    {self._tabla_distribucion("Incidencias por severidad", "Severidad", "Cantidad", metricas.get("por_severidad", {}))}
    {self._tabla_distribucion("Incidencias por semana", "Semana", "Cantidad", metricas.get("por_semana", {}))}
    {self._tabla_distribucion("Incidencias por mes", "Mes", "Cantidad", metricas.get("por_mes", {}))}
  </div>
"""

    def _renderizar_validacion_modelo(self, validacion: dict[str, object]) -> str:
        precision = self._formato_pct(validacion.get("precision"))
        sensibilidad = self._formato_pct(validacion.get("sensibilidad"))
        estado_css = self._clase_estado_operativo(str(validacion.get("estado", "")))
        return f"""
  <h2>Validacion del modelo</h2>
  <p class="section-note">Esta seccion sirve para auditoria: compara lo que detecto SafeWork con revision humana cuando existan etiquetas de validacion.</p>
  <section class="grid">
    {self._card("Estado validacion", f"<span class='{estado_css}'>{escape(self._texto_legible(validacion.get('estado', 'N/D')))}</span>", "Estado de la revision humana disponible.", html_value=True)}
    {self._card("Muestras revisadas", validacion.get("muestras_etiquetadas", 0), "Eventos revisados por una persona.")}
    {self._card("Precision", precision, "De las alertas emitidas, cuantas fueron correctas.")}
    {self._card("Sensibilidad", sensibilidad, "De los riesgos reales revisados, cuantos detecto el sistema.")}
  </section>
  <table>
    <tr><th>Metrica</th><th>Valor</th></tr>
    {self._fila_kv("Verdaderos positivos", validacion.get("verdaderos_positivos", 0))}
    {self._fila_kv("Falsos positivos", validacion.get("falsos_positivos", 0))}
    {self._fila_kv("Falsos negativos", validacion.get("falsos_negativos", 0))}
    {self._fila_kv("Recomendacion", validacion.get("recomendacion", "N/D"))}
  </table>
"""

    def _renderizar_resumen_sesion(self, sesion: dict[str, object]) -> str:
        return f"""
  <h2>Detalle de la sesion</h2>
  <p class="section-note">Describe como se ejecuto el monitoreo durante esta sesion.</p>
  <table>
    <tr><th>Dato</th><th>Valor</th><th>Interpretacion</th></tr>
    {self._fila_kv("Estado final", self._texto_legible(sesion.get("estado_actual", "N/D")), "Ultimo estado observado al cerrar o exportar el reporte.")}
    {self._fila_kv("Duracion de sesion", self._formato_duracion(sesion.get("duracion_sesion_segundos")), "Tiempo total monitoreado.")}
    {self._fila_kv("Sensibilidad", self._texto_legible(sesion.get("sensibilidad", "N/D")), "Nivel de exigencia usado para las reglas de riesgo.")}
    {self._fila_kv("Muestras de aprendizaje", sesion.get("muestras_aprendizaje", "N/D"), "Lecturas estables usadas para adaptar el perfil del usuario.")}
    {self._fila_kv("Indice de fatiga actual", sesion.get("indice_fatiga_actual", "N/D"), "Valor interno de seguimiento, mayor indica mas senales acumuladas de fatiga.")}
  </table>
"""

    def _renderizar_eventos(self, eventos: list[object]) -> str:
        filas_eventos = "\n".join(
            self._fila_evento(evento) for evento in eventos[-120:] if isinstance(evento, dict)
        )
        if not filas_eventos:
            filas_eventos = "<tr><td colspan='7'>No hay incidencias registradas en esta sesion.</td></tr>"
        return f"""
  <h2>Incidencias registradas</h2>
  <p class="section-note">Cada fila representa un evento guardado por SafeWork. Se muestra la evidencia y la accion recomendada para que el supervisor entienda por que se registro.</p>
  <table>
    <tr>
      <th>Fecha</th><th>Riesgo detectado</th><th>Nivel</th><th>Tiempo sostenido</th>
      <th>Calidad</th><th>Evidencias</th><th>Accion recomendada</th>
    </tr>
    {filas_eventos}
  </table>
"""

    def _renderizar_perfil_aprendido(self, perfil: dict[str, object]) -> str:
        return f"""
  <h2>Perfil aprendido del usuario</h2>
  <p class="section-note">Estos valores son la base personal del usuario. Sirven para que SafeWork compare contra la postura normal de esa persona, no contra un valor generico.</p>
  <section class="grid">
    {self._card("Ojos base", self._formato_numero(perfil.get("base_ear")), "Apertura ocular normal durante calibracion.")}
    {self._card("Boca base", self._formato_numero(perfil.get("base_mar")), "Apertura normal de boca durante calibracion.")}
    {self._card("Rostro base", self._formato_numero(perfil.get("base_ancho_cara")), "Referencia para estimar cercania al monitor.")}
    {self._card("Muestras", self._formato_numero(perfil.get("muestras_calibracion")), "Cantidad de lecturas usadas para crear el perfil.")}
  </section>
  <table>
    <tr><th>Medida aprendida</th><th>Valor</th><th>Uso dentro del sistema</th></tr>
    {self._fila_kv("Postura vertical base", self._formato_numero(perfil.get("base_ratio_y")), "Referencia de postura normal del usuario.")}
    {self._fila_kv("Profundidad base", self._formato_numero(perfil.get("base_z_nariz_rel")), "Referencia para detectar si el usuario se acerca demasiado.")}
    {self._fila_kv("Ultima actualizacion", self._formato_fecha_timestamp(perfil.get("updated_at")), "Fecha en que se actualizo el perfil aprendido.")}
  </table>
"""

    def _tabla_distribucion(self, titulo: str, columna: str, valor_label: str, datos: object) -> str:
        if not isinstance(datos, dict) or not datos:
            filas = f"<tr><td colspan='2'>Sin datos suficientes para mostrar {escape(titulo.lower())}.</td></tr>"
        else:
            filas = "\n".join(
                f"<tr><td>{escape(self._texto_clave_distribucion(clave))}</td><td>{escape(str(valor))}</td></tr>"
                for clave, valor in list(datos.items())[-12:]
            )
        return f"""
    <div class="card">
      <h3>{escape(titulo)}</h3>
      <table>
        <tr><th>{escape(columna)}</th><th>{escape(valor_label)}</th></tr>
        {filas}
      </table>
    </div>
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
        evidencias = evento.get("evidencias", [])
        if isinstance(evidencias, list):
            evidencias_texto = ", ".join(str(item) for item in evidencias)
        else:
            evidencias_texto = str(evidencias)
        return (
            "<tr>"
            f"<td>{escape(ReporteHtmlRenderer._formato_fecha(evento.get('timestamp', '')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._texto_legible(evento.get('estado', '')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._texto_legible(evento.get('nivel_riesgo', evento.get('severidad', ''))))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._formato_duracion(evento.get('duracion_riesgo_segundos')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._formato_pct(evento.get('calidad_deteccion')))}</td>"
            f"<td>{escape(ReporteHtmlRenderer._texto_legible(evidencias_texto))}</td>"
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
