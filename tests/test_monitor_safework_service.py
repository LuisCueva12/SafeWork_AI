from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.application.servicios import MonitorSafeWorkService
from src.domain.entities.postura import Coordenada, EstadoAlerta, LecturaHibrida, NivelRiesgo
from src.infrastructure.adaptadores.motor_vision_hibrido_qthread import MotorVisionIA


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


def construir_lectura(
    ear: float = 0.3,
    mar: float = 0.2,
    yolo_clase: str = "normal",
    yolo_confianza: float = 0.0,
) -> LecturaHibrida:
    lectura = LecturaHibrida(
        ear=ear,
        mar=mar,
        nariz_y=0.2,
        ancho_cara=0.3,
        rostro_detectado=True,
        cuerpo_detectado=True,
        yolo_clase=yolo_clase,
        yolo_confianza=yolo_confianza,
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


def construir_lectura_cercana_con_inclinacion_aparente() -> LecturaHibrida:
    lectura = construir_lectura_cercana()
    lectura.nariz = Coordenada(0.5, 0.30, -0.22, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.30, -0.19, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.30, -0.19, 1.0)
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


def construir_lectura_mirando_abajo_sin_sueno() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.34, mar=0.10, yolo_clase="normal")
    lectura.nariz = Coordenada(0.5, 0.32, -0.10, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.31, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.31, -0.08, 1.0)
    lectura.mirando_abajo = True
    return lectura


def construir_lectura_cabeceo_real() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.12, mar=0.10, yolo_clase="normal")
    lectura.nariz = Coordenada(0.5, 0.32, -0.10, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.31, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.31, -0.08, 1.0)
    lectura.mirando_abajo = False
    return lectura


def construir_lectura_teclado_con_yolo_debil() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.22, mar=0.12, yolo_clase="drowsy", yolo_confianza=0.64)
    lectura.nariz = Coordenada(0.5, 0.32, -0.10, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.31, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.31, -0.08, 1.0)
    lectura.mirando_abajo = True
    return lectura


def construir_lectura_movimiento_normal() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.30, mar=0.12, yolo_clase="normal")
    lectura.nariz = Coordenada(0.5, 0.32, -0.10, 1.0)
    lectura.oreja_izquierda = Coordenada(0.42, 0.31, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.58, 0.31, -0.08, 1.0)
    return lectura


def construir_lectura_fuera_encuadre() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.10, mar=0.10, yolo_clase="normal")
    lectura.nariz = Coordenada(0.02, 0.32, -0.10, 1.0)
    lectura.hombro_izquierdo = Coordenada(0.01, 0.52, 0.0, 1.0)
    lectura.hombro_derecho = Coordenada(0.18, 0.52, 0.0, 1.0)
    lectura.oreja_izquierda = Coordenada(0.02, 0.31, -0.08, 1.0)
    lectura.oreja_derecha = Coordenada(0.15, 0.31, -0.08, 1.0)
    return lectura


def construir_lectura_inestable() -> LecturaHibrida:
    lectura = construir_lectura(ear=0.0, mar=0.0)
    lectura.cuerpo_detectado = False
    lectura.nariz = Coordenada(0.0, 0.0, 0.0, 0.0)
    lectura.hombro_izquierdo = Coordenada(0.0, 0.0, 0.0, 0.0)
    lectura.hombro_derecho = Coordenada(0.0, 0.0, 0.0, 0.0)
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
        self.assertEqual(resultado.estado_fisico.calidad_deteccion, 0.0)

    def test_quality_gate_evita_incidentes_con_lectura_inestable(self) -> None:
        memoria = MemoriaFalsa()
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )

        resultado = servicio.procesar_lectura(construir_lectura_inestable())

        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.LECTURA_INESTABLE)
        self.assertLess(resultado.estado_fisico.calidad_deteccion, 42.0)
        self.assertIsNone(resultado.mensaje_alerta)
        self.assertFalse(memoria.eventos)

    def test_emite_alerta_de_sueno_por_clase_yolo(self) -> None:
        memoria = MemoriaFalsa()
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            memoria_usuario=memoria,
        )
        lectura = construir_lectura(mar=0.45, yolo_clase="yawn", yolo_confianza=0.82)
        lectura.fusion_nivel = NivelRiesgo.RIESGO_CONFIRMADO
        resultado = servicio.procesar_lectura(lectura)
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.ADVERTENCIA_SUENO)
        self.assertEqual(resultado.estado_fisico.nivel_riesgo, NivelRiesgo.RIESGO_CONFIRMADO)
        self.assertIsNotNone(resultado.mensaje_alerta)
        self.assertIsNotNone(resultado.pausa_activa)
        self.assertIn("Pausa activa", resultado.mensaje_alerta or "")
        self.assertGreaterEqual(len(memoria.eventos), 1)
        self.assertIn("puntajes_riesgo", memoria.eventos[-1])
        self.assertIn("evidencias", memoria.eventos[-1])
        self.assertIn("accion_recomendada", memoria.eventos[-1])

    def test_carga_bases_previas_del_usuario(self) -> None:
        memoria = MemoriaFalsa()
        memoria.base = {"base_ear": 0.31, "base_mar": 0.19, "base_ancho_cara": 0.27}
        servicio = MonitorSafeWorkService(memoria_usuario=memoria)
        self.assertAlmostEqual(servicio.sesion.base_ear, 0.31)
        self.assertAlmostEqual(servicio.sesion.base_mar, 0.19)

    def test_configura_sensibilidad_y_cooldown_por_servicio(self) -> None:
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
            sensibilidad="alta",
            cooldown_alerta_segundos=12,
        )

        self.assertEqual(servicio.sesion.sensibilidad, "alta")
        self.assertEqual(servicio.sesion.cooldown_alerta_segundos, 12)
        self.assertLess(servicio.sesion.factor_sensibilidad(), 1.0)

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

        now = datetime.now()
        servicio.sesion.inicio_cercania_monitor = now - timedelta(seconds=11)
        servicio.sesion.ultimo_registro_cercania_monitor = now

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
        self.assertEqual(resultado.estado_fisico.nivel_riesgo, NivelRiesgo.RIESGO_LEVE)
        self.assertGreaterEqual(resultado.estado_fisico.proximidad_monitor, 0.72)
        self.assertIn("Alejate un poco", mensaje_alerta)

    def test_yolo_baja_confianza_es_solo_observacion(self) -> None:
        servicio = MonitorSafeWorkService(
            calibracion_segundos=0.0,
            min_muestras_calibracion=0,
            max_duracion_calibracion_segundos=0.0,
        )
        lectura = construir_lectura(mar=0.45, yolo_clase="yawn", yolo_confianza=0.62)

        MotorVisionIA._aplicar_fusion_sensores(lectura)
        resultado = servicio.procesar_lectura(lectura)

        self.assertEqual(lectura.fusion_nivel, NivelRiesgo.OBSERVACION)
        self.assertEqual(resultado.estado_fisico.nivel_riesgo, NivelRiesgo.OBSERVACION)
        self.assertIsNone(resultado.mensaje_alerta)

    def test_bostezo_sostenido_sin_yolo_se_detecta_por_mediapipe(self) -> None:
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
            resultado = servicio.procesar_lectura(construir_lectura(mar=0.46, yolo_clase="normal"))

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.ADVERTENCIA_SUENO)
        self.assertIn("bostezo_por_apertura_sostenida", resultado.estado_fisico.evidencias)

    def test_sensor_fusion_confirma_yolo_y_mediapipe(self) -> None:
        lectura = construir_lectura(mar=0.46, yolo_clase="Yawning", yolo_confianza=0.86)

        MotorVisionIA._aplicar_fusion_sensores(lectura)

        self.assertEqual(lectura.fusion_nivel, NivelRiesgo.RIESGO_CONFIRMADO)
        self.assertIn("coinciden", lectura.fusion_motivo.lower())

    def test_yolo_normalizado_no_confunde_no_yawn(self) -> None:
        lectura = construir_lectura(mar=0.46, yolo_clase="no_yawn", yolo_confianza=0.92)

        MotorVisionIA._aplicar_fusion_sensores(lectura)

        self.assertIsNone(lectura.fusion_nivel)

    def test_yolo_fatiga_no_confirma_solo_por_mirar_abajo(self) -> None:
        lectura = construir_lectura(ear=0.34, mar=0.10, yolo_clase="drowsy", yolo_confianza=0.86)
        lectura.mirando_abajo = True

        MotorVisionIA._aplicar_fusion_sensores(lectura)

        self.assertEqual(lectura.fusion_nivel, NivelRiesgo.OBSERVACION)

    def test_cercania_domina_sobre_inclinacion_aparente(self) -> None:
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
        now = datetime.now()
        servicio.sesion.inicio_cercania_monitor = now - timedelta(seconds=4)
        servicio.sesion.ultimo_registro_cercania_monitor = now

        resultado = servicio.procesar_lectura(construir_lectura_cercana_con_inclinacion_aparente())

        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.CERCANIA_MONITOR)
        self.assertNotEqual(resultado.estado_fisico.estado, EstadoAlerta.MALA_POSTURA)
        self.assertGreaterEqual(resultado.estado_fisico.proximidad_monitor, 0.72)
        self.assertIn("cercania_monitor", resultado.estado_fisico.evidencias)

    def test_histeresis_evita_parpadeo_al_volver_a_optimo(self) -> None:
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
        servicio.sesion.estado_estable_actual = EstadoAlerta.CERCANIA_MONITOR.name
        servicio.sesion.ultimo_riesgo_observado = datetime.now()

        resultado = servicio.procesar_lectura(construir_lectura())

        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.CERCANIA_MONITOR)
        self.assertEqual(resultado.estado_fisico.nivel_riesgo, NivelRiesgo.OBSERVACION)
        self.assertIn("histeresis_salida", resultado.estado_fisico.evidencias)

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

    def test_no_confunde_mirar_abajo_con_cabeceo(self) -> None:
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
            resultado = servicio.procesar_lectura(construir_lectura_mirando_abajo_sin_sueno())

        self.assertIsNotNone(resultado)
        self.assertNotEqual(resultado.estado_fisico.estado, EstadoAlerta.CABECEO)
        self.assertIn("mirada_abajo_sin_somnolencia_confirmada", resultado.estado_fisico.evidencias)

    def test_detecta_cabeceo_con_ojos_cerrados_y_cabeza_caida(self) -> None:
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
        for _ in range(5):
            resultado = servicio.procesar_lectura(construir_lectura_cabeceo_real())

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.CABECEO)
        self.assertIn("cabeza_inclinada_con_somnolencia", resultado.estado_fisico.evidencias)

    def test_mirada_al_teclado_con_yolo_debil_no_escala_a_cabeceo(self) -> None:
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
        for _ in range(5):
            resultado = servicio.procesar_lectura(construir_lectura_teclado_con_yolo_debil())

        self.assertIsNotNone(resultado)
        self.assertNotEqual(resultado.estado_fisico.estado, EstadoAlerta.CABECEO)
        self.assertNotIn("cabeza_inclinada_con_somnolencia", resultado.estado_fisico.evidencias)

    def test_movimiento_normal_no_escala_a_cabeceo(self) -> None:
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
        for _ in range(6):
            resultado = servicio.procesar_lectura(construir_lectura_movimiento_normal())

        self.assertIsNotNone(resultado)
        self.assertNotEqual(resultado.estado_fisico.estado, EstadoAlerta.CABECEO)
        self.assertNotIn("cabeza_inclinada_con_somnolencia", resultado.estado_fisico.evidencias)

    def test_salir_del_encuadre_no_escala_a_cabeceo(self) -> None:
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

        resultado = servicio.procesar_lectura(construir_lectura_fuera_encuadre())

        self.assertEqual(resultado.estado_fisico.estado, EstadoAlerta.LECTURA_INESTABLE)
        self.assertIn("encuadre_incompleto", resultado.estado_fisico.evidencias)

    def test_reingreso_no_dispara_cabeceo_al_sentarse(self) -> None:
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

        resultado_ausencia = servicio.procesar_lectura(None)
        resultado_reingreso = servicio.procesar_lectura(construir_lectura_cabeceo_real())

        self.assertEqual(resultado_ausencia.estado_fisico.estado, EstadoAlerta.AUSENTE)
        self.assertEqual(resultado_reingreso.estado_fisico.estado, EstadoAlerta.LECTURA_INESTABLE)
        self.assertIn("reingreso_estabilizando", resultado_reingreso.estado_fisico.evidencias)

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
            contexto_operativo={"empresa": "Softech Peru", "puesto": "oficina"},
        )

        lectura = construir_lectura(mar=0.45, yolo_clase="yawn", yolo_confianza=0.82)
        lectura.fusion_nivel = NivelRiesgo.RIESGO_CONFIRMADO
        resultado = servicio.procesar_lectura(lectura)

        self.assertTrue(memoria.eventos)
        self.assertIn("validacion", memoria.eventos[-1])
        self.assertEqual(memoria.eventos[-1]["nivel_riesgo"], NivelRiesgo.RIESGO_CONFIRMADO.value)
        self.assertIn("pausa_activa", memoria.eventos[-1])
        self.assertIsNotNone(memoria.eventos[-1]["pausa_activa"])
        self.assertTrue(memoria.reportes)
        self.assertIn("perfil_base", memoria.reportes[-1])
        self.assertIn("incidentes_criticos", memoria.reportes[-1])
        self.assertEqual(memoria.reportes[-1]["contexto_operativo"]["empresa"], "Softech Peru")

    def test_registra_incidente_al_escalar_de_leve_a_critico(self) -> None:
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

        now = datetime.now()
        tipo = EstadoAlerta.CERCANIA_MONITOR.value
        servicio.sesion.niveles_riesgo_actuales[tipo] = NivelRiesgo.RIESGO_LEVE.name
        servicio.sesion.inicio_cercania_monitor = now - timedelta(seconds=21)
        servicio.sesion.ultimo_registro_cercania_monitor = now

        resultado = servicio.procesar_lectura(construir_lectura_cercana())

        self.assertEqual(resultado.estado_fisico.nivel_riesgo, NivelRiesgo.RIESGO_CRITICO)
        self.assertIn(tipo, servicio.sesion.incidentes)
        self.assertEqual(servicio.sesion.incidentes[tipo][-1]["nivel"], NivelRiesgo.RIESGO_CRITICO.name)


if __name__ == "__main__":
    unittest.main()
