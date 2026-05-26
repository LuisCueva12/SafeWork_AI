from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from .reporte_analisis_service import ReporteAnalisisService


class ReportePdfRenderer:
    def renderizar(self, payload: dict[str, object], modo: str = "jornada") -> bytes:
        pdf = _SafeWorkPdf(modo=modo)
        pdf.set_auto_page_break(auto=True, margin=16)
        pdf.set_margins(12, 12, 12)
        pdf.add_page()
        pdf.renderizar(payload)
        salida = pdf.output(dest="S")
        if isinstance(salida, bytes):
            return salida
        return salida.encode("latin-1", errors="replace")


class _SafeWorkPdf(FPDF):
    brand = (15, 32, 64)
    brand_2 = (13, 148, 136)
    ink = (15, 23, 42)
    muted = (100, 116, 139)
    line = (219, 228, 240)
    soft = (248, 251, 255)

    def __init__(self, *, modo: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.modo = modo

    def renderizar(self, payload: dict[str, object]) -> None:
        titulo = "Reporte de Jornada" if self.modo == "jornada" else "Historial Global"
        self._header_documento(payload, titulo)
        self._seccion_identificacion(payload)
        if self.modo == "global":
            self._seccion_historial_global(payload)
        else:
            self._seccion_jornada(payload)
        self._seccion_indicadores(payload)
        self._seccion_recomendaciones(payload)
        self._seccion_eventos(payload, globales=self.modo == "global")
        self._footer_documento()

    def _header_documento(self, payload: dict[str, object], titulo: str) -> None:
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, 38, "F")

        logo = self._logo_path()
        if logo is not None:
            try:
                self.image(str(logo), x=12, y=8, w=42)
            except Exception:
                self._texto(12, 14, "SafeWork AI", size=15, color=self.brand, bold=True)
        else:
            self._texto(12, 14, "SafeWork AI", size=15, color=self.brand, bold=True)

        self._texto(70, 10, titulo, size=18, color=self.ink, bold=True)
        self._texto(
            70,
            20,
            "Monitoreo de postura, fatiga visual y distancia frente al computador",
            size=8.5,
            color=self.muted,
            max_width=82,
        )
        self._pill(154, 10, self._estado_sistema(payload), w=44)
        self.set_y(43)

    def _seccion_identificacion(self, payload: dict[str, object]) -> None:
        sesion = self._dict(payload.get("reporte_sesion"))
        contexto = self._dict(sesion.get("contexto_operativo"))
        self._titulo("Identificacion")
        self._cards(
            [
                ("Persona", contexto.get("nombre", contexto.get("trabajador", "N/D"))),
                ("Rol", self._legible(contexto.get("rol", "N/D"))),
                ("Tipo", self._legible(contexto.get("tipo_usuario", "N/D"))),
                ("Puesto", self._legible(contexto.get("puesto", "N/D"))),
            ]
        )

    def _seccion_jornada(self, payload: dict[str, object]) -> None:
        jornada = self._dict(payload.get("resumen_jornada"))
        self._titulo("Resumen de jornada")
        self._cards(
            [
                ("Fecha", jornada.get("fecha", "N/D")),
                ("Estado", self._legible(jornada.get("estado_jornada", "N/D"))),
                ("Eventos", jornada.get("total_eventos", 0)),
                ("Calidad", self._formato_pct(jornada.get("calidad_promedio"))),
            ]
        )
        self._cards(
            [
                ("Lecturas", jornada.get("lecturas_validas", 0)),
                ("Alertas", jornada.get("alertas_emitidas", 0)),
                ("Duracion", self._formato_duracion(jornada.get("duracion_sesion_segundos"))),
                ("Riesgo dominante", self._riesgo_dominante(jornada)),
            ],
            y_gap=4,
        )

    def _seccion_historial_global(self, payload: dict[str, object]) -> None:
        resumen = self._dict(payload.get("resumen_incidencias"))
        metricas = self._dict(resumen.get("metricas_agregadas"))
        periodos = self._dict(metricas.get("periodos"))
        eventos = self._lista_eventos(payload.get("eventos"))
        self._titulo("Historial general")
        self._cards(
            [
                ("Total eventos", resumen.get("total_incidencias", len(eventos))),
                ("Hoy", periodos.get("hoy", 0)),
                ("7 dias", periodos.get("ultimos_7_dias", 0)),
                ("30 dias", periodos.get("ultimos_30_dias", 0)),
            ]
        )
        self._cards(
            [
                ("Calidad promedio", self._formato_pct(metricas.get("calidad_promedio"))),
                ("Categorias", len(self._dict(resumen.get("por_categoria")))),
                ("Primer registro", self._fecha_extrema(eventos, primero=True)),
                ("Ultimo registro", self._fecha_extrema(eventos, primero=False)),
            ],
            y_gap=4,
        )

        categorias = self._dict(resumen.get("por_categoria"))
        if categorias:
            filas = [
                (self._legible(categoria), cantidad, "Eventos acumulados por tipo de riesgo.")
                for categoria, cantidad in sorted(categorias.items(), key=lambda item: str(item[0]))
            ]
            self._tabla(("Categoria", "Eventos", "Lectura"), filas, widths=(45, 32, 99))

    def _seccion_indicadores(self, payload: dict[str, object]) -> None:
        resumen = self._dict(payload.get("resumen_incidencias"))
        sesion = self._dict(payload.get("reporte_sesion"))
        metricas = self._dict(resumen.get("metricas_agregadas"))
        periodos = self._dict(metricas.get("periodos"))
        contexto = self._dict(sesion.get("contexto_operativo"))

        self._titulo("Indicadores clave")
        filas = [
            ("Estado actual", self._legible(sesion.get("estado_actual", "N/D")), "Ultima lectura confirmada por el sistema."),
            ("Eventos hoy", periodos.get("hoy", 0), "Incidencias registradas en la jornada actual."),
            ("Ultimos 7 dias", periodos.get("ultimos_7_dias", 0), "Carga reciente de eventos."),
            ("Ultimos 30 dias", periodos.get("ultimos_30_dias", 0), "Vista mensual para seguimiento."),
            ("Calidad promedio", self._formato_pct(metricas.get("calidad_promedio")), "Confiabilidad media del sensor."),
            ("Empresa / area", f"{contexto.get('empresa', 'N/D')} / {contexto.get('area', 'N/D')}", "Contexto operativo del usuario."),
        ]
        self._tabla(("Indicador", "Valor", "Lectura"), filas, widths=(42, 48, 86))

    def _seccion_recomendaciones(self, payload: dict[str, object]) -> None:
        analisis = self._dict(payload.get("analisis_calidad_datos"))
        recomendaciones = analisis.get("recomendaciones", [])
        if not isinstance(recomendaciones, list):
            recomendaciones = [recomendaciones]

        self._titulo("Recomendaciones")
        y = self.get_y()
        self.set_fill_color(*self.soft)
        self.set_draw_color(*self.line)
        self.rect(12, y, 186, 28, "DF")
        self.set_xy(16, y + 4)
        self.set_text_color(*self.ink)
        self.set_font("Arial", "", 8.2)
        texto = " | ".join(str(item) for item in recomendaciones[:3]) or "Sin recomendaciones adicionales."
        self.multi_cell(178, 5, self._safe(texto))
        self.set_y(y + 33)

    def _seccion_eventos(self, payload: dict[str, object], *, globales: bool) -> None:
        if globales:
            eventos = self._lista_eventos(payload.get("eventos"))[-14:]
            titulo = "Eventos recientes del historial"
            nota = "No hay eventos registrados en el historial general."
        else:
            jornada = self._dict(payload.get("resumen_jornada"))
            eventos = self._lista_eventos(jornada.get("eventos_relevantes"))[-10:]
            titulo = "Alertas relevantes de la jornada"
            nota = "No hay incidencias registradas para esta jornada."

        self._titulo(titulo)
        if not eventos:
            self._nota(nota)
            return

        filas = []
        for evento in eventos:
            filas.append(
                (
                    self._formato_fecha(evento.get("timestamp", "")),
                    self._legible(evento.get("estado", "")),
                    self._legible(evento.get("nivel_riesgo", evento.get("severidad", ""))),
                    str(evento.get("accion_recomendada", evento.get("descripcion", ""))),
                )
            )
        self._tabla(("Fecha", "Indicador", "Nivel", "Accion"), filas, widths=(31, 44, 32, 69))

    def _footer_documento(self) -> None:
        self.ln(4)
        self.set_text_color(*self.muted)
        self.set_font("Arial", "", 7.5)
        self.multi_cell(
            186,
            4,
            self._safe(
                "Reporte generado localmente por SafeWork AI. No incluye imagenes ni video; contiene metricas e incidencias registradas."
            ),
        )

    def _titulo(self, texto: str) -> None:
        if self.get_y() > 250:
            self.add_page()
        self.set_text_color(*self.brand)
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, self._safe(texto), ln=True)

    def _cards(self, items: list[tuple[str, object]], *, y_gap: int = 6) -> None:
        if self.get_y() > 250:
            self.add_page()
        x0 = 12
        y0 = self.get_y()
        w = 43.5
        h = 24
        gap = 4
        for index, (label, value) in enumerate(items[:4]):
            x = x0 + index * (w + gap)
            self.set_fill_color(*self.soft)
            self.set_draw_color(*self.line)
            self.rect(x, y0, w, h, "DF")
            self._texto(x + 3, y0 + 4, label.upper(), size=6.8, color=self.muted, bold=True)
            self._texto(x + 3, y0 + 12, str(value), size=9.5, color=self.ink, bold=True, max_width=w - 6)
        self.set_y(y0 + h + y_gap)

    def _tabla(self, headers: tuple[str, ...], rows: list[tuple[object, ...]], widths: tuple[int, ...]) -> None:
        if self.get_y() > 236:
            self.add_page()
        x0 = 12
        self.set_x(x0)
        self.set_fill_color(*self.brand)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 8)
        for header, width in zip(headers, widths):
            self.cell(width, 8, self._safe(header), border=0, align="L", fill=True)
        self.ln()
        self.set_font("Arial", "", 7.4)
        for row in rows:
            if self.get_y() > 268:
                self.add_page()
                self.set_x(x0)
            y = self.get_y()
            row_height = 10
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(*self.line)
            self.rect(x0, y, sum(widths), row_height, "D")
            x = x0
            for value, width in zip(row, widths):
                self.set_xy(x + 2, y + 2.5)
                self.set_text_color(*self.ink)
                contenido = self._safe(str(value))
                max_w = width - 4
                while self.get_string_width(contenido) > max_w and len(contenido) > 3:
                    contenido = contenido[:-4].rstrip() + "..."
                self.cell(max_w, 4, contenido, border=0)
                x += width
            self.set_y(y + row_height)
        self.ln(4)

    def _nota(self, texto: str) -> None:
        self.set_fill_color(*self.soft)
        self.set_draw_color(*self.line)
        y = self.get_y()
        self.rect(12, y, 186, 12, "DF")
        self._texto(16, y + 4, texto, size=8.5, color=self.muted)
        self.set_y(y + 16)

    def _pill(self, x: float, y: float, texto: str, *, w: float) -> None:
        self.set_fill_color(219, 234, 254)
        self.rect(x, y, w, 9, "F")
        self._texto(x + 3, y + 2.5, texto, size=6.5, color=(30, 64, 175), bold=True, max_width=w - 6)

    def _texto(
        self,
        x: float,
        y: float,
        texto: str,
        *,
        size: float,
        color: tuple[int, int, int],
        bold: bool = False,
        max_width: float | None = None,
    ) -> None:
        self.set_xy(x, y)
        self.set_text_color(*color)
        self.set_font("Arial", "B" if bold else "", size)
        contenido = self._safe(texto)
        if max_width is not None:
            while self.get_string_width(contenido) > max_width and len(contenido) > 4:
                contenido = contenido[:-4].rstrip() + "..."
        self.cell(0, 4, contenido)

    @staticmethod
    def _dict(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _lista_eventos(value: object) -> list[dict[str, object]]:
        return [evento for evento in value if isinstance(evento, dict)] if isinstance(value, list) else []

    @staticmethod
    def _legible(value: object) -> str:
        return ReporteAnalisisService.texto_legible(value)

    @staticmethod
    def _safe(value: object) -> str:
        return str(value).replace("\n", " ").encode("latin-1", errors="replace").decode("latin-1")

    @staticmethod
    def _estado_sistema(payload: dict[str, object]) -> str:
        analisis = _SafeWorkPdf._dict(payload.get("analisis_calidad_datos"))
        return str(analisis.get("estado_sistema", "SIN DIAGNOSTICO"))

    @staticmethod
    def _riesgo_dominante(jornada: dict[str, object]) -> str:
        categorias = jornada.get("por_categoria", {})
        if not isinstance(categorias, dict) or not categorias:
            return "Bajo"
        return str(max(categorias.items(), key=lambda item: item[1])[0])

    @staticmethod
    def _fecha_extrema(eventos: list[dict[str, object]], *, primero: bool) -> str:
        fechas = [
            fecha for evento in eventos
            if (fecha := ReporteAnalisisService.parsear_fecha(evento.get("timestamp"))) is not None
        ]
        if not fechas:
            return "N/D"
        fecha = min(fechas) if primero else max(fechas)
        return fecha.strftime("%Y-%m-%d")

    @staticmethod
    def _formato_fecha(value: object) -> str:
        fecha = ReporteAnalisisService.parsear_fecha(value)
        if fecha is None:
            return str(value) if value else "N/D"
        return fecha.strftime("%Y-%m-%d %H:%M")

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
    def _formato_pct(value: object) -> str:
        numero = ReporteAnalisisService.normalizar_porcentaje(ReporteAnalisisService.to_float(value, None))
        if numero is None:
            return "N/D"
        return f"{numero:.1f}%"

    @staticmethod
    def _logo_path() -> Path | None:
        root = Path(__file__).resolve().parents[3]
        logo = root / "assets" / "logo.png"
        return logo if logo.exists() else None
