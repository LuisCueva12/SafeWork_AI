from __future__ import annotations

import unittest

from src.application.servicios import PerfilBiometricoService
from src.domain.entities.postura import Coordenada, LecturaHibrida
from src.domain.entities.trabajador import SesionTrabajador


class PerfilBiometricoServiceTest(unittest.TestCase):
    def test_registra_promedios_base(self) -> None:
        servicio = PerfilBiometricoService(duracion_segundos=5.0)
        sesion = SesionTrabajador()
        lectura = LecturaHibrida(
            ear=0.32,
            mar=0.21,
            nariz_y=0.2,
            ancho_cara=0.28,
            rostro_detectado=True,
            cuerpo_detectado=True,
        )
        lectura.nariz = Coordenada(0.5, 0.2, -0.1, 1.0)
        lectura.hombro_izquierdo = Coordenada(0.4, 0.5, 0.0, 1.0)
        lectura.hombro_derecho = Coordenada(0.6, 0.5, 0.0, 1.0)

        servicio.registrar_muestra(lectura, sesion)

        self.assertEqual(sesion.muestras_calibracion, 1)
        self.assertGreater(sesion.base_ear, 0.0)
        self.assertGreater(sesion.base_mar, 0.0)
        self.assertNotEqual(sesion.base_z_nariz_rel, 0.0)


if __name__ == "__main__":
    unittest.main()
