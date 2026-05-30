from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.domain.entities.postura import Coordenada, EstadoAlerta, EstadoFisico, LecturaHibrida
from src.domain.entities.trabajador import SesionTrabajador
from src.domain.reglas.calculo_postural import (
    UMBRAL_CABECEO_TIEMPO_SEGUNDOS,
    UMBRAL_EAR_CERRADO,
    UMBRAL_OJOS_CERRADOS_SEGUNDOS,
    analizar_lectura_hibrida,
)


def crear_lectura_mock(
    ear: float = 0.35,
    mar: float = 0.1,
    yolo_clase: str = "normal",
    yolo_confianza: float = 0.85,
    rostro_detectado: bool = True,
    cuerpo_detectado: bool = True,
    mirando_abajo: bool = False,
    mano_sobre_rostro: bool = False,
) -> LecturaHibrida:
    lectura = LecturaHibrida(
        ear=ear,
        mar=mar,
        nariz_y=0.2,
        ancho_cara=0.2,
        rostro_detectado=rostro_detectado,
        cuerpo_detectado=cuerpo_detectado,
        yolo_clase=yolo_clase,
        yolo_confianza=yolo_confianza,
    )
    lectura.mirando_abajo = mirando_abajo
    lectura.mano_sobre_rostro = mano_sobre_rostro

    lectura.nariz = Coordenada(0.5, 0.2, -0.1, 1.0)
    lectura.hombro_izquierdo = Coordenada(0.4, 0.5, 0.0, 1.0)
    lectura.hombro_derecho = Coordenada(0.6, 0.5, 0.0, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.2, -0.1, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.2, -0.1, 1.0)
    return lectura


class CalculoPosturalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sesion = SesionTrabajador()
        # Calibramos al instante para evitar el estado CALIBRANDO
        self.sesion.base_ear = 0.35
        self.sesion.base_mar = 0.1
        self.sesion.base_ancho_hombros = 0.2
        self.sesion.base_ratio_y = 1.5
        self.sesion.base_z_nariz_rel = -0.1
        self.sesion.muestras_calibracion = 25

    def test_estado_optimo(self) -> None:
        lectura = crear_lectura_mock()
        estado = analizar_lectura_hibrida(lectura, self.sesion)
        self.assertEqual(estado.estado, EstadoAlerta.OPTIMO)

    def test_filtro_ema_suaviza_picos_espurios(self) -> None:
        # EAR normal
        analizar_lectura_hibrida(crear_lectura_mock(ear=0.35), self.sesion)
        self.assertAlmostEqual(self.sesion.ultimo_ear_filtrado, 0.35, places=2)

        # Un frame espurio con EAR bajísimo
        analizar_lectura_hibrida(crear_lectura_mock(ear=0.01), self.sesion)
        # Por EMA alpha=0.42, el nuevo valor debería ser: 0.42*0.01 + 0.58*0.35 = 0.2072
        # Todavía por encima del umbral de ojo cerrado (0.18) para evitar falso positivo
        self.assertGreater(self.sesion.ultimo_ear_filtrado, UMBRAL_EAR_CERRADO)

    def test_fatiga_extrema_por_ojos_cerrados(self) -> None:
        # Simulamos que cierra los ojos durante el tiempo umbral
        now = datetime.now()
        self.sesion.inicio_ojos_cerrados = now - timedelta(seconds=(UMBRAL_OJOS_CERRADOS_SEGUNDOS + 0.5))
        self.sesion.ultimo_registro_ojos_cerrados = now
        # Proveemos múltiples lecturas para bajar el EMA a < 0.18
        for _ in range(5):
            estado = analizar_lectura_hibrida(crear_lectura_mock(ear=0.10), self.sesion)
        self.assertEqual(estado.estado, EstadoAlerta.FATIGA_EXTREMA)

    def test_cabeceo_por_tiempo_prolongado(self) -> None:
        now = datetime.now()
        self.sesion.inicio_cabeceo = now - timedelta(seconds=(UMBRAL_CABECEO_TIEMPO_SEGUNDOS + 0.5))
        self.sesion.ultimo_registro_cabeceo = now
        for _ in range(5):
            # ear 0.35 para evitar FATIGA EXTREMA por ojos cerrados
            lectura = crear_lectura_mock(ear=0.35, yolo_clase="drowsy", yolo_confianza=0.90)
            lectura.fusion_nivel = 3
            estado = analizar_lectura_hibrida(lectura, self.sesion)
        self.assertEqual(estado.estado, EstadoAlerta.CABECEO)

    def test_racha_cercania_se_activa(self) -> None:
        for i in range(7):
            lectura = crear_lectura_mock()
            # z muy positivo simulando cercanía (nariz muy al frente de hombros)
            lectura.nariz.z = -1.0
            estado = analizar_lectura_hibrida(lectura, self.sesion)
            if i < 5:
                self.assertEqual(estado.estado, EstadoAlerta.OPTIMO)
        self.assertEqual(estado.estado, EstadoAlerta.CERCANIA_MONITOR)

    def test_fatiga_por_bostezos_recurrentes(self) -> None:
        self.sesion.indice_fatiga = 0.90
        for _ in range(5):
            estado = analizar_lectura_hibrida(crear_lectura_mock(mar=0.10), self.sesion)
        # La lógica actual puede bajar índice fatiga si no hay bostezo. Forzamos bostezo recurrente.
        self.sesion.cantidad_bostezos_recientes = lambda: 3
        estado = analizar_lectura_hibrida(crear_lectura_mock(mar=0.10), self.sesion)
        self.assertEqual(estado.estado, EstadoAlerta.ADVERTENCIA_SUENO)

    def test_ausente_si_no_hay_deteccion(self) -> None:
        lectura = crear_lectura_mock(rostro_detectado=False, cuerpo_detectado=False)
        estado = analizar_lectura_hibrida(lectura, self.sesion)
        self.assertLess(estado.calidad_deteccion, 55.0)

if __name__ == "__main__":
    unittest.main()
