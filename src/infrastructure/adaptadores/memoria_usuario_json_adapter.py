from __future__ import annotations

import json
from datetime import datetime, timedelta
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

    @staticmethod
    def _obfuscar(texto: str) -> str:
        try:
            import base64
            key = 0x5A
            encoded = bytearray(texto.encode("utf-8"))
            for i in range(len(encoded)):
                encoded[i] ^= key
            return base64.b64encode(encoded).decode("utf-8")
        except Exception:
            return texto

    @staticmethod
    def _desobfuscar(texto_obfuscado: str) -> str:
        texto_limpio = texto_obfuscado.strip()
        if not texto_limpio:
            return ""
        if texto_limpio.startswith(("{", "[")):
            return texto_obfuscado
        try:
            import base64
            key = 0x5A
            decoded = base64.b64decode(texto_limpio.encode("utf-8"))
            decoded_array = bytearray(decoded)
            for i in range(len(decoded_array)):
                decoded_array[i] ^= key
            return decoded_array.decode("utf-8")
        except Exception:
            return texto_obfuscado

    def _escribir_archivo_seguro(self, ruta: Path, datos: object) -> None:
        try:
            texto_json = json.dumps(datos, ensure_ascii=False, indent=2)
            texto_obfuscado = self._obfuscar(texto_json)
            ruta.write_text(texto_obfuscado, encoding="utf-8")
        except Exception:
            try:
                ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

    def _leer_archivo_seguro(self, ruta: Path) -> object | None:
        if not ruta.exists():
            return None
        try:
            contenido_original = ruta.read_text(encoding="utf-8")
            contenido_desobfuscado = self._desobfuscar(contenido_original)
            return json.loads(contenido_desobfuscado)
        except Exception:
            try:
                ruta_corrupta = ruta.with_suffix(ruta.suffix + ".corrupted")
                if ruta.exists():
                    if ruta_corrupta.exists():
                        ruta_corrupta.unlink()
                    ruta.rename(ruta_corrupta)
            except Exception:
                pass
            return None

    def cargar_sesion_base(self) -> dict[str, float]:
        data = self._leer_archivo_seguro(self._profile_path)
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
        self._escribir_archivo_seguro(self._profile_path, payload)

    def registrar_evento(self, evento: dict[str, object]) -> None:
        eventos = self._leer_eventos()
        eventos.append(evento)
        eventos = eventos[-300:]
        self._escribir_archivo_seguro(self._events_path, eventos)
        self._escribir_archivo_seguro(self._summary_path, self._construir_resumen_incidencias(eventos))

    def obtener_resumen_incidencias(self) -> dict[str, object]:
        resumen = self._leer_archivo_seguro(self._summary_path)
        if isinstance(resumen, dict):
            return resumen
        eventos = self._leer_eventos()
        resumen = self._construir_resumen_incidencias(eventos)
        self._escribir_archivo_seguro(self._summary_path, resumen)
        return resumen

    def guardar_reporte_sesion(self, reporte: dict[str, object]) -> None:
        self._escribir_archivo_seguro(self._session_report_path, reporte)

    def _leer_eventos(self) -> list[dict[str, object]]:
        eventos = self._leer_archivo_seguro(self._events_path)
        if isinstance(eventos, list):
            return [evento for evento in eventos if isinstance(evento, dict)]
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
            "metricas_agregadas": self._construir_metricas_agregadas(eventos),
            "ultimas_incidencias": recientes,
            "updated_at": datetime.now().isoformat(),
        }

    def _construir_metricas_agregadas(self, eventos: list[dict[str, object]]) -> dict[str, object]:
        ahora = datetime.now()
        hace_7_dias = ahora - timedelta(days=7)
        hace_30_dias = ahora - timedelta(days=30)
        por_dia: dict[str, int] = {}
        por_semana: dict[str, int] = {}
        por_mes: dict[str, int] = {}
        por_severidad: dict[str, int] = {}
        calidades: list[float] = []
        hoy = 0
        ultimos_7_dias = 0
        ultimos_30_dias = 0

        for evento in eventos:
            fecha = self._parsear_fecha_evento(evento.get("timestamp"))
            if fecha is not None:
                dia = fecha.date().isoformat()
                semana = f"{fecha.isocalendar().year}-W{fecha.isocalendar().week:02d}"
                mes = f"{fecha.year:04d}-{fecha.month:02d}"
                por_dia[dia] = por_dia.get(dia, 0) + 1
                por_semana[semana] = por_semana.get(semana, 0) + 1
                por_mes[mes] = por_mes.get(mes, 0) + 1
                if fecha.date() == ahora.date():
                    hoy += 1
                if fecha >= hace_7_dias:
                    ultimos_7_dias += 1
                if fecha >= hace_30_dias:
                    ultimos_30_dias += 1

            severidad = str(evento.get("severidad", "informativa"))
            por_severidad[severidad] = por_severidad.get(severidad, 0) + 1
            try:
                calidades.append(float(evento.get("calidad_deteccion", 0)))
            except (TypeError, ValueError):
                pass

        promedio_calidad = round(sum(calidades) / len(calidades), 2) if calidades else None
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
            "calidad_promedio": promedio_calidad,
        }

    @staticmethod
    def _parsear_fecha_evento(valor: object) -> datetime | None:
        if not isinstance(valor, str) or not valor:
            return None
        try:
            return datetime.fromisoformat(valor)
        except ValueError:
            return None
