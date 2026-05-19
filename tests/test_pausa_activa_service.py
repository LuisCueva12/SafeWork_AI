from __future__ import annotations

import unittest

from src.application.servicios import PausaActivaService
from src.domain.entities.postura import EstadoAlerta


class PausaActivaServiceTest(unittest.TestCase):
    def test_recomienda_pausa_por_tipo_de_riesgo(self) -> None:
        servicio = PausaActivaService()

        postura = servicio.recomendar(EstadoAlerta.MALA_POSTURA)
        distancia = servicio.recomendar(EstadoAlerta.CERCANIA_MONITOR)
        fatiga = servicio.recomendar(EstadoAlerta.ADVERTENCIA_SUENO)

        self.assertEqual(postura.tipo, "ergonomia")
        self.assertEqual(distancia.tipo, "distancia_visual")
        self.assertEqual(fatiga.tipo, "fatiga")
        self.assertGreaterEqual(len(postura.instrucciones), 2)

    def test_aumenta_duracion_con_reincidencia(self) -> None:
        servicio = PausaActivaService()

        inicial = servicio.recomendar(EstadoAlerta.CABECEO, reincidencias=1)
        recurrente = servicio.recomendar(EstadoAlerta.CABECEO, reincidencias=3)

        self.assertLess(inicial.duracion_segundos, recurrente.duracion_segundos)


if __name__ == "__main__":
    unittest.main()
