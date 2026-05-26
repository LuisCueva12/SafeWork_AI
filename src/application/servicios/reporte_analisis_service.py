from __future__ import annotations

from datetime import datetime


class ReporteAnalisisService:
    def preparar_payload(self, payload: dict[str, object]) -> dict[str, object]:
        enriquecido = dict(payload)
        enriquecido["resumen_incidencias"] = self.normalizar_resumen_incidencias(enriquecido)
        enriquecido["analisis_calidad_datos"] = self.analizar_calidad_datos(enriquecido)
        enriquecido["validacion_modelo"] = self.analizar_validacion_modelo(enriquecido)
        return enriquecido

    def normalizar_resumen_incidencias(self, payload: dict[str, object]) -> dict[str, object]:
        resumen = payload.get("resumen_incidencias", {})
        if not isinstance(resumen, dict):
            resumen = {}
        eventos = self._eventos_validos(payload.get("eventos", []))

        resumen = dict(resumen)
        if eventos:
            resumen["total_incidencias"] = len(eventos)
        else:
            resumen.setdefault("total_incidencias", 0)
        if "por_categoria" not in resumen or not isinstance(resumen.get("por_categoria"), dict):
            por_categoria: dict[str, int] = {}
            for evento in eventos:
                categoria = str(evento.get("categoria", "general"))
                por_categoria[categoria] = por_categoria.get(categoria, 0) + 1
            resumen["por_categoria"] = por_categoria
        metricas = resumen.get("metricas_agregadas")
        if not isinstance(metricas, dict) or "periodos" not in metricas:
            resumen["metricas_agregadas"] = self.construir_metricas_desde_eventos(eventos)
        return resumen

    def construir_metricas_desde_eventos(self, eventos: list[dict[str, object]]) -> dict[str, object]:
        ahora = datetime.now()
        por_dia: dict[str, int] = {}
        por_semana: dict[str, int] = {}
        por_mes: dict[str, int] = {}
        por_severidad: dict[str, int] = {}
        calidades: list[float] = []
        hoy = 0
        ultimos_7_dias = 0
        ultimos_30_dias = 0

        for evento in eventos:
            fecha = self.parsear_fecha(evento.get("timestamp"))
            if fecha is not None:
                dia = fecha.date().isoformat()
                semana = f"{fecha.isocalendar().year}-W{fecha.isocalendar().week:02d}"
                mes = f"{fecha.year:04d}-{fecha.month:02d}"
                por_dia[dia] = por_dia.get(dia, 0) + 1
                por_semana[semana] = por_semana.get(semana, 0) + 1
                por_mes[mes] = por_mes.get(mes, 0) + 1
                dias = (ahora.date() - fecha.date()).days
                if dias == 0:
                    hoy += 1
                if 0 <= dias <= 7:
                    ultimos_7_dias += 1
                if 0 <= dias <= 30:
                    ultimos_30_dias += 1

            severidad = str(evento.get("severidad", evento.get("nivel_riesgo", "informativa")))
            severidad = self.texto_legible(severidad).lower()
            por_severidad[severidad] = por_severidad.get(severidad, 0) + 1
            calidad = self.normalizar_porcentaje(self.to_float(evento.get("calidad_deteccion"), None))
            if calidad is not None:
                calidades.append(calidad)

        return {
            "periodos": {
                "hoy": hoy,
                "ultimos_7_dias": ultimos_7_dias,
                "ultimos_30_dias": ultimos_30_dias,
            },
            "por_dia": dict(sorted(por_dia.items())[-30:]),
            "por_semana": dict(sorted(por_semana.items())[-12:]),
            "por_mes": dict(sorted(por_mes.items())[-12:]),
            "por_severidad": por_severidad,
            "calidad_promedio": round(sum(calidades) / len(calidades), 1) if calidades else None,
        }

    def analizar_calidad_datos(self, payload: dict[str, object]) -> dict[str, object]:
        eventos = self._eventos_validos(payload.get("eventos", []))
        sesion = payload.get("reporte_sesion", {})
        if not isinstance(sesion, dict):
            sesion = {}

        lecturas_validas = self.to_float(sesion.get("lecturas_validas"), 0.0) or 0.0
        alertas_emitidas = self.to_float(sesion.get("alertas_emitidas"), 0.0) or 0.0
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
                self.normalizar_porcentaje(self.to_float(evento.get("calidad_deteccion"), None))
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
            calidad_promedio = self.normalizar_porcentaje(self.to_float(sesion.get("calidad_ultima_lectura"), None))

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

    def analizar_validacion_modelo(self, payload: dict[str, object]) -> dict[str, object]:
        etiquetas_raw = payload.get("validacion_humana", [])
        etiquetas = [item for item in etiquetas_raw if isinstance(item, dict)] if isinstance(etiquetas_raw, list) else []
        if not etiquetas:
            return {
                "estado": "PENDIENTE_VALIDACION_HUMANA",
                "muestras_etiquetadas": 0,
                "verdaderos_positivos": 0,
                "falsos_positivos": 0,
                "falsos_negativos": 0,
                "precision": None,
                "sensibilidad": None,
                "recomendacion": "Etiquetar sesiones reales para medir falsos positivos y falsos negativos.",
            }

        verdaderos_positivos = 0
        falsos_positivos = 0
        falsos_negativos = 0
        pendientes = 0
        for etiqueta in etiquetas:
            resultado = str(etiqueta.get("resultado", etiqueta.get("validacion", ""))).strip().lower()
            resultado = resultado.replace("-", "_").replace(" ", "_")
            if resultado in {"correcto", "verdadero_positivo", "true_positive", "tp"}:
                verdaderos_positivos += 1
            elif resultado in {"falso_positivo", "false_positive", "fp"}:
                falsos_positivos += 1
            elif resultado in {"falso_negativo", "false_negative", "fn"}:
                falsos_negativos += 1
            else:
                pendientes += 1

        precision = self.ratio(verdaderos_positivos, verdaderos_positivos + falsos_positivos)
        sensibilidad = self.ratio(verdaderos_positivos, verdaderos_positivos + falsos_negativos)
        estado = "VALIDACION_BUENA"
        recomendacion = "Continuar validando en sesiones largas con diferentes usuarios y camaras."
        if pendientes:
            estado = "VALIDACION_PARCIAL"
            recomendacion = "Completar etiquetas pendientes para obtener metricas finales."
        if falsos_positivos or falsos_negativos:
            estado = "REQUIERE_AJUSTE"
            recomendacion = "Revisar umbrales y evidencias de los casos marcados como falsos positivos o falsos negativos."

        return {
            "estado": estado,
            "muestras_etiquetadas": len(etiquetas),
            "verdaderos_positivos": verdaderos_positivos,
            "falsos_positivos": falsos_positivos,
            "falsos_negativos": falsos_negativos,
            "pendientes": pendientes,
            "precision": precision,
            "sensibilidad": sensibilidad,
            "recomendacion": recomendacion,
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

    @staticmethod
    def _eventos_validos(value: object) -> list[dict[str, object]]:
        return [evento for evento in value if isinstance(evento, dict)] if isinstance(value, list) else []

    @staticmethod
    def _campo_util(evento: dict[str, object], campo: str) -> bool:
        if campo not in evento:
            return False
        valor = evento.get(campo)
        return valor is not None and valor != "" and valor != [] and valor != {}

    @staticmethod
    def parsear_fecha(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def to_float(value: object, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def normalizar_porcentaje(value: float | None) -> float | None:
        if value is None:
            return None
        if 0 < value <= 1:
            value *= 100
        return round(max(0.0, min(100.0, value)), 1)

    @staticmethod
    def ratio(numerador: int, denominador: int) -> float | None:
        if denominador <= 0:
            return None
        return round((numerador / denominador) * 100, 1)

    @staticmethod
    def texto_legible(value: object) -> str:
        if value is None:
            return "N/D"
        texto = str(value).strip()
        if not texto:
            return "N/D"
        if texto.upper() == "N/D":
            return "N/D"
        texto = texto.replace("_", " ").replace("-", " ")
        palabras_minusculas = {"al", "de", "del", "la", "las", "los", "y", "por"}
        partes = []
        for indice, palabra in enumerate(texto.lower().split()):
            if indice > 0 and palabra in palabras_minusculas:
                partes.append(palabra)
            else:
                partes.append(palabra.capitalize())
        return " ".join(partes)
