from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.application.servicios import ReporteExportService


class ReporteExportServiceTest(unittest.TestCase):
    def test_exporta_reporte_html_y_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "user_profile.json"
            events = root / "event_history.json"
            summary = root / "incident_summary.json"
            session = root / "session_report.json"
            labels = root / "validation_labels.json"
            output = root / "exports"

            profile.write_text(json.dumps({"base_ear": 0.31}), encoding="utf-8")
            events.write_text(
                json.dumps(
                    [
                        {
                            "timestamp": "2026-05-18T10:00:00",
                            "estado": "CERCANIA AL MONITOR",
                            "nivel_riesgo": "RIESGO_LEVE",
                            "duracion_riesgo_segundos": 11.0,
                            "calidad_deteccion": 96,
                            "evidencias": ["rostro_mas_grande", "nariz_z_cercana"],
                            "accion_recomendada": "Alejate un poco del monitor.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            labels.write_text(
                json.dumps(
                    [
                        {
                            "incident_id": "cercania-1",
                            "resultado": "correcto",
                            "observacion": "Incidencia validada por supervisor.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            summary.write_text(
                json.dumps(
                    {
                        "total_incidencias": 1,
                        "metricas_agregadas": {
                            "periodos": {"hoy": 1, "ultimos_7_dias": 1, "ultimos_30_dias": 1},
                            "por_dia": {"2026-05-18": 1},
                            "por_semana": {"2026-W21": 1},
                            "por_mes": {"2026-05": 1},
                            "por_severidad": {"leve": 1},
                            "calidad_promedio": 96,
                        },
                    }
                ),
                encoding="utf-8",
            )
            session.write_text(
                json.dumps(
                    {
                        "estado_actual": "CERCANIA AL MONITOR",
                        "lecturas_validas": 180,
                        "alertas_emitidas": 1,
                        "calidad_ultima_lectura": 94,
                        "duracion_sesion_segundos": 240,
                        "sensibilidad": "normal",
                        "muestras_aprendizaje": 60,
                        "contexto_operativo": {
                            "empresa": "Softech Peru",
                            "trabajador": "demo",
                            "puesto": "oficina",
                            "perfil_riesgo": "estandar",
                            "camara": "webcam_integrada",
                            "iluminacion": "media",
                        },
                    }
                ),
                encoding="utf-8",
            )

            exportador = ReporteExportService(profile, events, summary, session, output, validation_labels_path=labels)
            reporte = exportador.exportar()

            self.assertTrue(reporte.html_path.exists())
            self.assertTrue(reporte.json_path.exists())
            self.assertIsNotNone(reporte.pdf_path)
            self.assertTrue(reporte.pdf_path.exists())
            html = reporte.html_path.read_text(encoding="utf-8")
            data = json.loads(reporte.json_path.read_text(encoding="utf-8"))
            self.assertIn("Reporte SafeWork AI", html)
            self.assertIn("Analisis de calidad de datos", html)
            self.assertIn("Contexto de validacion", html)
            self.assertIn("Historico agregado", html)
            self.assertIn("Validacion del modelo", html)
            self.assertIn("Rostro Mas Grande", html)
            self.assertIn("Puntaje de datos", html)
            self.assertIn("Muestras revisadas", html)
            self.assertEqual(data["resumen_incidencias"]["total_incidencias"], 1)
            self.assertIn("analisis_calidad_datos", data)
            self.assertGreaterEqual(data["analisis_calidad_datos"]["puntaje_calidad_datos"], 85)
            self.assertEqual(data["analisis_calidad_datos"]["estado_sistema"], "CONFIABILIDAD ALTA")
            self.assertEqual(data["validacion_modelo"]["verdaderos_positivos"], 1)
            self.assertEqual(data["validacion_modelo"]["falsos_positivos"], 0)

    def test_analisis_reconoce_sesion_sin_incidencias_como_valida(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "user_profile.json"
            events = root / "event_history.json"
            summary = root / "incident_summary.json"
            session = root / "session_report.json"
            output = root / "exports"

            profile.write_text(json.dumps({"base_ear": 0.31}), encoding="utf-8")
            events.write_text(json.dumps([]), encoding="utf-8")
            summary.write_text(json.dumps({"total_incidencias": 0}), encoding="utf-8")
            session.write_text(
                json.dumps(
                    {
                        "estado_actual": "OPTIMO",
                        "lecturas_validas": 300,
                        "alertas_emitidas": 0,
                        "calidad_ultima_lectura": 92,
                    }
                ),
                encoding="utf-8",
            )

            exportador = ReporteExportService(profile, events, summary, session, output)
            reporte = exportador.exportar()
            data = json.loads(reporte.json_path.read_text(encoding="utf-8"))
            analisis = data["analisis_calidad_datos"]

            self.assertEqual(analisis["estado_sistema"], "OPERATIVO SIN INCIDENTES")
            self.assertGreaterEqual(analisis["puntaje_calidad_datos"], 90)
            self.assertIn("sesion sin incidentes", analisis["recomendaciones"][0].lower())


if __name__ == "__main__":
    unittest.main()
