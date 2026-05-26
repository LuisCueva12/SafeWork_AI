from __future__ import annotations

import unittest

from src.application.servicios import FusionSensoresService
from src.domain.entities.postura import LecturaHibrida, NivelRiesgo


class FusionSensoresServiceTest(unittest.TestCase):
    def test_confirma_bostezo_cuando_yolo_y_heuristica_coinciden(self) -> None:
        servicio = FusionSensoresService()
        lectura = LecturaHibrida(
            ear=0.30,
            mar=0.45,
            nariz_y=0.2,
            ancho_cara=0.3,
            rostro_detectado=True,
            cuerpo_detectado=True,
            yolo_clase="yawn",
            yolo_confianza=0.84,
        )

        servicio.aplicar(lectura)

        self.assertEqual(lectura.fusion_nivel, NivelRiesgo.RIESGO_CONFIRMADO)
        self.assertIn("coinciden", lectura.fusion_motivo.lower())

    def test_mantiene_observacion_con_confianza_baja(self) -> None:
        servicio = FusionSensoresService()
        lectura = LecturaHibrida(
            ear=0.16,
            mar=0.20,
            nariz_y=0.2,
            ancho_cara=0.3,
            rostro_detectado=True,
            cuerpo_detectado=True,
            yolo_clase="drowsy",
            yolo_confianza=0.62,
        )

        servicio.aplicar(lectura)

        self.assertEqual(lectura.fusion_nivel, NivelRiesgo.OBSERVACION)
        self.assertIn("confianza baja", lectura.fusion_motivo.lower())


if __name__ == "__main__":
    unittest.main()
