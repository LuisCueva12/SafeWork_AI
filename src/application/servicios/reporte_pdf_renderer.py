from __future__ import annotations

import json

from .reporte_html_renderer import ReporteHtmlRenderer


class ReportePdfRenderer:
    def renderizar(self, payload: dict[str, object]) -> bytes:
        lineas = self._lineas_pdf(payload)
        return self._crear_pdf_texto(lineas)

    def _lineas_pdf(self, payload: dict[str, object]) -> list[str]:
        resumen = payload.get("resumen_incidencias", {})
        if not isinstance(resumen, dict):
            resumen = {}
        sesion = payload.get("reporte_sesion", {})
        if not isinstance(sesion, dict):
            sesion = {}
        analisis = payload.get("analisis_calidad_datos", {})
        if not isinstance(analisis, dict):
            analisis = {}
        validacion = payload.get("validacion_modelo", {})
        if not isinstance(validacion, dict):
            validacion = {}
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

        lineas = [
            "Reporte SafeWork AI",
            f"Exportado: {payload.get('exportado_en', '')}",
            "",
            "Identificacion",
            f"Persona analizada: {contexto.get('nombre', contexto.get('trabajador', 'N/D'))}",
            f"Rol: {contexto.get('rol', 'N/D')}",
            f"Tipo de usuario: {contexto.get('tipo_usuario', 'N/D')}",
            f"Puesto: {contexto.get('puesto', 'N/D')}",
            "",
            "Resumen principal",
            f"Estado final: {sesion.get('estado_actual', 'N/D')}",
            f"Incidencias: {resumen.get('total_incidencias', 0)}",
            f"Alertas emitidas: {sesion.get('alertas_emitidas', 0)}",
            f"Lecturas validas: {sesion.get('lecturas_validas', 0)}",
            f"Calidad de lectura: {ReporteHtmlRenderer._formato_pct(sesion.get('calidad_ultima_lectura'))}",
            f"Duracion: {ReporteHtmlRenderer._formato_duracion(sesion.get('duracion_sesion_segundos'))}",
            f"Incidencias hoy: {periodos.get('hoy', 0)}",
            f"Incidencias 7 dias: {periodos.get('ultimos_7_dias', 0)}",
            "",
            "Indicadores clave",
            f"Empresa: {contexto.get('empresa', 'N/D')}",
            f"Area: {contexto.get('area', 'N/D')}",
            f"Perfil de riesgo: {contexto.get('perfil_riesgo', 'N/D')}",
            f"Sensibilidad: {sesion.get('sensibilidad', 'N/D')}",
            f"Calidad promedio: {ReporteHtmlRenderer._formato_pct(metricas.get('calidad_promedio'))}",
            "",
            "Recomendaciones",
        ]
        lineas.extend(f"- {item}" for item in recomendaciones[:5])
        lineas.extend(
            [
                "",
                "Alertas relevantes",
            ]
        )
        eventos = payload.get("eventos", [])
        if isinstance(eventos, list) and eventos:
            for evento in eventos[-12:]:
                if not isinstance(evento, dict):
                    continue
                lineas.append(
                    f"- {evento.get('timestamp', '')} | {evento.get('estado', '')} | "
                    f"{evento.get('nivel_riesgo', evento.get('severidad', ''))} | "
                    f"{evento.get('accion_recomendada', evento.get('descripcion', ''))}"
                )
        else:
            lineas.append("- No hay incidencias registradas.")
        lineas.extend(
            [
                "",
                "Perfil base del usuario",
                f"Ojos base: {ReporteHtmlRenderer._formato_numero(payload.get('perfil_usuario', {}).get('base_ear'))}",
                f"Boca base: {ReporteHtmlRenderer._formato_numero(payload.get('perfil_usuario', {}).get('base_mar'))}",
                f"Referencia facial: {ReporteHtmlRenderer._formato_numero(payload.get('perfil_usuario', {}).get('base_ancho_cara'))}",
                f"Muestras de calibracion: {ReporteHtmlRenderer._formato_numero(payload.get('perfil_usuario', {}).get('muestras_calibracion'))}",
            ]
        )
        return lineas

    def _crear_pdf_texto(self, lineas: list[str]) -> bytes:
        lineas_por_pagina = 42
        paginas = [lineas[i : i + lineas_por_pagina] for i in range(0, len(lineas), lineas_por_pagina)] or [[]]
        objetos: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        kids: list[str] = []

        for pagina in paginas:
            page_id = len(objetos) + 1
            content_id = page_id + 1
            kids.append(f"{page_id} 0 R")
            contenido = self._contenido_pagina_pdf(pagina)
            objetos.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
            objetos.append(
                b"<< /Length " + str(len(contenido)).encode("ascii") + b" >>\nstream\n" + contenido + b"\nendstream"
            )

        objetos[1] = (
            f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(paginas)} >>"
        ).encode("ascii")

        partes = [b"%PDF-1.4\n"]
        offsets: list[int] = []
        posicion = len(partes[0])
        for indice, objeto in enumerate(objetos, start=1):
            offsets.append(posicion)
            bloque = f"{indice} 0 obj\n".encode("ascii") + objeto + b"\nendobj\n"
            partes.append(bloque)
            posicion += len(bloque)

        xref_pos = posicion
        xref = [f"xref\n0 {len(objetos) + 1}\n", "0000000000 65535 f \n"]
        xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets)
        trailer = (
            "".join(xref)
            + f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
            + f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
        partes.append(trailer)
        return b"".join(partes)

    @staticmethod
    def _contenido_pagina_pdf(lineas: list[str]) -> bytes:
        comandos = ["BT", "/F1 10 Tf", "50 760 Td", "14 TL"]
        for linea in lineas:
            comandos.append(f"({ReportePdfRenderer._escape_pdf_text(linea[:105])}) Tj")
            comandos.append("T*")
        comandos.append("ET")
        return "\n".join(comandos).encode("latin-1", errors="replace")

    @staticmethod
    def _escape_pdf_text(texto: object) -> str:
        return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
