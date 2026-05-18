from __future__ import annotations

import unittest

from src.application.servicios import MonitorSafeWorkService
from src.domain.entities.postura import Coordenada, EstadoAlerta, LecturaHibrida


class MemoriaFalsa:
    def __init__(self) -> None:
        self.base = {}
        self.eventos = []
        self.reportes = []

    def cargar_sesion_base(self) -> dict[str, float]:
        return self.base

    def guardar_sesion_base(self, sesion) -> None:
        self.base = {
            "base_ear": sesion.base_ear,
            "base_mar": sesion.base_mar,
            "base_ancho_cara": sesion.base_ancho_cara,
        }

    def registrar_evento(self, evento: dict[str, object]) -> None:
        self.eventos.append(evento)

    def obtener_resumen_incidencias(self) -> dict[str, object]:
        return {}

    def guardar_reporte_sesion(self, reporte: dict[str, object]) -> None:
        self.reportes.append(reporte)


def construir_lectura(ear: float = 0.3, mar: float = 0.2, yolo_clase: str = "normal") -> LecturaHibrida:
    lectura = LecturaHibrida(
        ear=ear,
        mar=mar,
        nariz_y=0.2,
        ancho_cara=0.3,
        rostro_detectado=True,
        cuerpo_detectado=True,
        yolo_clase=yolo_clase,
    )
    lectura.nariz = Coordenada(0.5, 0.2, -0.1, 1.0)
    lectura.hombro_izquierdo = Coordenada(0.4, 0.5, 0.0, 1.0)
    lectura.hombro_derecho = Coordenada(0.6, 0.5, 0.0, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.22, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.22, -0.08, 1.0)
    return lectura


def construir_lectura_cercana() -> LecturaHibrida:
    lectura = construir_lectura()
    lectura.ancho_cara = 0.38
    lectura.nariz = Coordenada(0.5, 0.21, -0.22, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.23, -0.19, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.23, -0.19, 1.0)
    return lectura


def construir_lectura_ocluida() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.33, mar=0.10, yolo_clase="normal")
    lectura.nariz = Coordenada(0.5, 0.31, -0.10, 1.0)
    lectura.hombro_izquierdo = Coordenada(0.4, 0.5, 0.0, 1.0)
    lectura.hombro_derecho = Coordenada(0.6, 0.5, 0.0, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.28, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.30, -0.08, 1.0)
    lectura.mano_sobre_rostro = True
    lectura.mirando_abajo = False
    return lectura


class MonitorSafeWorkServiceTest(unittest.TestCase):
    def test_permanece_calibrando_en_ventana_inicial(self) -> None:
        servicio = MonitorSafeWorkService(calibracion_segundos=999.0)
        resultado = servicio.procesar_lectura(construir_lectura())
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.CALIBRANDO)
        self.assertEqual(servicio.sesion.muestras_calibracion, 1)

    def test_reporta_ausencia_sin_lectura(self) -> None:
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
        )
        resultado = servicio.procesar_lectura(None)
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.AUSENTE)

    def test_emite_alerta_de_sueno_por_clase_yolo(self) -> None:
        memoria = MemoriaFalsa()
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )
        lectura = construir_lectura(yolo_clase="yawn")
        resultado = servicio.procesar_lectura(lectura)
        if resultado.estado_fisico.estado != EstadoAlerta.ADVERTENCIA_SUENO:
            resultado = servicio.procesar_lectura(lectura)
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.ADVERTENCIA_SUENO)
        self.assertIsNotNone(resultado.mensaje_alerta)
        self.assertGreaterEqual(len(memoria.eventos), 1)

    def test_carga_bases_previas_del_usuario(self) -> None:
        memoria = MemoriaFalsa()
        memoria.base = {"base_ear": 0.31, "base_mar": 0.19, "base_ancho_cara": 0.27}
        servicio = MonitorSafeWorkService(memoria_usuario=memoria)
        self.assertAlmostEqual(servicio.sesion.base_ear, 0.31)
        self.assertAlmostEqual(servicio.sesion.base_mar, 0.19)

    def test_distingue_cercania_al_monitor_de_mala_postura(self) -> None:
        memoria = MemoriaFalsa()
        memoria.base = {
            "base_ear": 0.31,
            "base_mar": 0.19,
            "base_ancho_cara": 0.30,
            "base_ratio_y": 1.50,
            "base_z_nariz_rel": -0.10,
        }
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )

        resultado = None
        mensaje_alerta = ""
        estados = []
        for _ in range(4):
            resultado = servicio.procesar_lectura(construir_lectura_cercana())
            estados.append(resultado.estado_fisico.estado)
            if resultado.mensaje_alerta:
                mensaje_alerta = resultado.mensaje_alerta

        self.assertIsNotNone(resultado)
        self.assertIn(EstadoAlerta.CERCANIA_MONITOR, estados)
        self.assertGreaterEqual(resultado.estado_fisico.proximidad_monitor, 0.72)
        self.assertIn("Alejate un poco", mensaje_alerta)

    def test_no_confunde_mano_en_rostro_con_cabeceo(self) -> None:
        memoria = MemoriaFalsa()
        memoria.base = {
            "base_ear": 0.31,
            "base_mar": 0.19,
            "base_ancho_cara": 0.30,
            "base_ratio_y": 1.50,
            "base_z_nariz_rel": -0.10,
        }
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )

        resultado = None
        for _ in range(4):
            resultado = servicio.procesar_lectura(construir_lectura_ocluida())

        self.assertIsNotNone(resultado)
        self.assertNotEqual(resultado.estado_fisico.estado, EstadoAlerta.CABECEO)
        self.assertLess(resultado.estado_fisico.angulo_cuello, 18.0)

    def test_aprende_perfil_en_lecturas_estables(self) -> None:
        memoria = MemoriaFalsa()
        memoria.base = {
            "base_ear": 0.30,
            "base_mar": 0.20,
            "base_ancho_cara": 0.30,
            "base_ratio_y": 1.50,
            "base_z_nariz_rel": -0.10,
        }
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )

        for _ in range(12):
            servicio.procesar_lectura(construir_lectura(ear=0.34, mar=0.18, yolo_clase="normal"))

        self.assertGreater(servicio.sesion.muestras_aprendizaje, 0)
        self.assertNotEqual(servicio.sesion.base_ear, 0.30)

    def test_evento_guarda_validacion_y_reporte(self) -> None:
        memoria = MemoriaFalsa()
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )

        lectura = construir_lectura(yolo_clase="yawn")
        resultado = servicio.procesar_lectura(lectura)
        if resultado.estado_fisico.estado != EstadoAlerta.ADVERTENCIA_SUENO:
            resultado = servicio.procesar_lectura(lectura)

        self.assertTrue(memoria.eventos)
        self.assertIn("validacion", memoria.eventos[-1])
        self.assertTrue(memoria.reportes)
        self.assertIn("perfil_base", memoria.reportes[-1])


if __name__ == "__main__":
    unittest.main()
