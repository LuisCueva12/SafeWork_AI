from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.infrastructure.adaptadores.memoria_usuario_json_adapter import MemoriaUsuarioJsonAdapter


class MemoriaUsuarioJsonAdapterTest(unittest.TestCase):
    def test_construye_resumen_de_incidencias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = MemoriaUsuarioJsonAdapter(
                root / "profile.json",
                root / "events.json",
                root / "summary.json",
            )

            adapter.registrar_evento(
                {
                    "timestamp": "2026-05-18T10:00:00",
                    "estado": "MALA POSTURA (Inclinacion)",
                    "categoria": "ergonomia",
                    "severidad": "media",
                    "descripcion": "Se detecto un patron ergonomico de riesgo sostenido.",
                }
            )
            adapter.registrar_evento(
                {
                    "timestamp": "2026-05-18T10:05:00",
                    "estado": "CERCANIA AL MONITOR",
                    "categoria": "proximidad",
                    "severidad": "media",
                    "descripcion": "Se detecta una cercania excesiva al monitor.",
                    "nivel_riesgo": "RIESGO_LEVE",
                    "duracion_riesgo_segundos": 11.0,
                    "calidad_deteccion": 98,
                    "accion_recomendada": "Alejate un poco del monitor.",
                    "evidencias": ["rostro_mas_grande"],
                }
            )

            resumen = adapter.obtener_resumen_incidencias()
            self.assertEqual(resumen["total_incidencias"], 2)
            self.assertEqual(resumen["por_categoria"]["ergonomia"], 1)
            self.assertEqual(resumen["por_categoria"]["proximidad"], 1)
            self.assertEqual(resumen["ultimas_incidencias"][0]["estado"], "CERCANIA AL MONITOR")
            self.assertEqual(resumen["ultimas_incidencias"][0]["nivel_riesgo"], "RIESGO_LEVE")
            self.assertIn("rostro_mas_grande", resumen["ultimas_incidencias"][0]["evidencias"])


if __name__ == "__main__":
    unittest.main()
