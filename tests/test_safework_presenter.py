from __future__ import annotations

import unittest

from src.infrastructure.adaptadores.safework_presenter import (
    construir_estado_error,
    construir_estado_sistema,
    construir_metricas_legibles,
    construir_nivel_riesgo,
    construir_registro_ausencia,
    construir_resumen_incidencias,
    describir_indice_global,
    etiqueta_riesgo,
    formatear_duracion_seg,
    parsear_metricas,
    perfil_requiere_configuracion,
    perfil_resumen_rol,
    resolver_aviso_visible,
)


class ParsearMetricasTest(unittest.TestCase):
    def test_cadena_bien_formada(self) -> None:
        self.assertEqual(parsear_metricas("EAR 0.30|MAR 0.10"), {"EAR": 0.30, "MAR": 0.10})

    def test_bloque_sin_espacio_se_ignora(self) -> None:
        self.assertEqual(parsear_metricas("EAR|MAR 0.10"), {"MAR": 0.10})

    def test_valor_no_numerico_se_ignora(self) -> None:
        self.assertEqual(parsear_metricas("EAR abc|MAR 0.10"), {"MAR": 0.10})

    def test_cadena_vacia(self) -> None:
        self.assertEqual(parsear_metricas(""), {})


class ConstruirMetricasLegiblesTest(unittest.TestCase):
    def test_ojos_cerrados(self) -> None:
        vm = construir_metricas_legibles("EAR 0.10|MAR 0.10|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.ojos.subtexto, "Cerrados")

    def test_ojos_cansados(self) -> None:
        vm = construir_metricas_legibles("EAR 0.25|MAR 0.10|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.ojos.subtexto, "Cansados")

    def test_ojos_relajados(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.ojos.subtexto, "Relajados")

    def test_postura_inclinada(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 28|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.postura.subtexto, "Inclinada")

    def test_postura_por_corregir_por_cuello(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 14|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.postura.subtexto, "Por corregir")

    def test_postura_por_corregir_por_lateral(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 7.5|Prox 0|Calidad 100")
        self.assertEqual(vm.postura.subtexto, "Por corregir")

    def test_postura_correcta(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.postura.subtexto, "Correcta")

    def test_distancia_muy_cerca(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0.72|Calidad 100")
        self.assertEqual(vm.distancia.subtexto, "Muy cerca")

    def test_distancia_leve(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0.35|Calidad 100")
        self.assertEqual(vm.distancia.subtexto, "Leve")

    def test_distancia_optima(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0.0|Calidad 100")
        self.assertEqual(vm.distancia.subtexto, "Optima")

    def test_energia_bostezo(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.46|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.energia.subtexto, "Bostezo")

    def test_energia_variable(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.30|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.energia.subtexto, "Variable")

    def test_energia_estable(self) -> None:
        vm = construir_metricas_legibles("EAR 0.30|MAR 0.10|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.energia.subtexto, "Estable")

    def test_indice_global_optimo_todo_perfecto(self) -> None:
        vm = construir_metricas_legibles("EAR 0.34|MAR 0.0|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.indice_global, 100)

    def test_indice_global_se_recorta_a_0_100(self) -> None:
        vm = construir_metricas_legibles("EAR 0.0|MAR 1.0|Cuello 100|Lateral 50|Prox 2.0|Calidad -50")
        self.assertGreaterEqual(vm.indice_global, 0)
        self.assertLessEqual(vm.indice_global, 100)

    def test_tendencia_indice_formula(self) -> None:
        vm = construir_metricas_legibles("EAR 0.34|MAR 0.0|Cuello 0|Lateral 0|Prox 0|Calidad 100")
        self.assertEqual(vm.tendencia_indice, [0.0, 0.0, 0.0, 0.0])


class DescribirIndiceGlobalTest(unittest.TestCase):
    def test_frontera_85(self) -> None:
        self.assertIn("optima", describir_indice_global(85))
        self.assertIn("estable", describir_indice_global(84))

    def test_frontera_70(self) -> None:
        self.assertIn("estable", describir_indice_global(70))
        self.assertIn("preventiva", describir_indice_global(69))

    def test_frontera_50(self) -> None:
        self.assertIn("preventiva", describir_indice_global(50))
        self.assertIn("prioritaria", describir_indice_global(49))


class EtiquetaRiesgoTest(unittest.TestCase):
    def test_frontera_20(self) -> None:
        self.assertEqual(etiqueta_riesgo(19), "Bajo (19%)")
        self.assertEqual(etiqueta_riesgo(20), "Medio (20%)")

    def test_frontera_45(self) -> None:
        self.assertEqual(etiqueta_riesgo(44), "Medio (44%)")
        self.assertEqual(etiqueta_riesgo(45), "Alto (45%)")

    def test_se_recorta_fuera_de_rango(self) -> None:
        self.assertEqual(etiqueta_riesgo(-10), "Bajo (0%)")
        self.assertEqual(etiqueta_riesgo(150), "Alto (100%)")


class ConstruirResumenIncidenciasTest(unittest.TestCase):
    def test_payload_invalido_retorna_none(self) -> None:
        self.assertIsNone(construir_resumen_incidencias("no es un dict"))
        self.assertIsNone(construir_resumen_incidencias(None))

    def test_periodos_faltantes_default_a_cero(self) -> None:
        vm = construir_resumen_incidencias({})
        self.assertEqual(vm.total_hoy, "0")
        self.assertEqual(vm.total_semana, "0")
        self.assertEqual(vm.total_mes, "0")

    def test_formula_tendencia(self) -> None:
        resumen = {"metricas_agregadas": {"periodos": {"hoy": 4, "ultimos_7_dias": 8, "ultimos_30_dias": 20}}}
        vm = construir_resumen_incidencias(resumen)
        self.assertEqual(vm.tendencia, [5.0, 4.0, 3.2, 4.0])

    def test_sin_incidencias_no_muestra_ultima(self) -> None:
        vm = construir_resumen_incidencias({"ultimas_incidencias": []})
        self.assertFalse(vm.mostrar_ultima_incidencia)

    def test_elemento_no_dict_se_maneja_con_gracia(self) -> None:
        vm = construir_resumen_incidencias({"ultimas_incidencias": ["no es dict"]})
        self.assertTrue(vm.mostrar_ultima_incidencia)
        self.assertIn("Incidencia", vm.ultima_incidencia_texto)

    def test_incidencia_bien_formada(self) -> None:
        resumen = {
            "ultimas_incidencias": [
                {
                    "estado": "MALA POSTURA",
                    "severidad": "media",
                    "descripcion": "Cuello inclinado",
                    "timestamp": "2026-01-01T00:00:00",
                }
            ]
        }
        vm = construir_resumen_incidencias(resumen)
        self.assertTrue(vm.mostrar_ultima_incidencia)
        self.assertEqual(vm.ultima_incidencia_texto, "MALA POSTURA\nCuello inclinado")
        self.assertEqual(vm.log_resumen_texto, "2026-01-01T00:00:00 | Prioridad: MEDIA")


class ConstruirEstadoSistemaTest(unittest.TestCase):
    def test_cooldown_se_refleja_en_texto_auxiliar(self) -> None:
        vm = construir_estado_sistema("MALA POSTURA - Cooldown activo")
        self.assertEqual(vm.estado_base, "MALA POSTURA")
        self.assertEqual(vm.texto_auxiliar, "Pausa temporal entre alertas")

    def test_matching_por_substring(self) -> None:
        vm = construir_estado_sistema("OPTIMO")
        self.assertEqual(vm.color, "#059669")

    def test_estado_desconocido_usa_fallback(self) -> None:
        vm = construir_estado_sistema("XYZ_NO_EXISTE")
        self.assertEqual(vm.color, "#1e293b")
        self.assertEqual(vm.color_fondo, "#f8fafc")


class ConstruirEstadoErrorTest(unittest.TestCase):
    def test_usa_colores_de_error(self) -> None:
        vm = construir_estado_error("ERROR DE SENSOR", "detalle")
        self.assertEqual(vm.color, "#dc2626")
        self.assertEqual(vm.estado_base, "ERROR DE SENSOR")
        self.assertEqual(vm.texto_auxiliar, "detalle")


class ConstruirNivelRiesgoTest(unittest.TestCase):
    def test_niveles_conocidos(self) -> None:
        for nivel in ("OBSERVACION", "RIESGO_LEVE", "RIESGO_CONFIRMADO", "RIESGO_CRITICO"):
            vm = construir_nivel_riesgo(nivel)
            self.assertIsInstance(vm.texto_auxiliar, str)
            self.assertNotEqual(vm.texto_auxiliar, "")

    def test_solo_critico_no_oculta_banner(self) -> None:
        self.assertFalse(construir_nivel_riesgo("RIESGO_CRITICO").ocultar_banner)
        self.assertTrue(construir_nivel_riesgo("OBSERVACION").ocultar_banner)
        self.assertTrue(construir_nivel_riesgo("RIESGO_LEVE").ocultar_banner)

    def test_nivel_desconocido_usa_fallback(self) -> None:
        vm = construir_nivel_riesgo("NO_EXISTE")
        self.assertEqual(vm.texto_auxiliar, "Monitoreo activo")


class FormatearDuracionSegTest(unittest.TestCase):
    def test_menos_de_60_segundos(self) -> None:
        self.assertEqual(formatear_duracion_seg(45), "45 seg")

    def test_60_segundos_exactos(self) -> None:
        self.assertEqual(formatear_duracion_seg(60), "1 min 00 seg")

    def test_minutos_y_segundos(self) -> None:
        self.assertEqual(formatear_duracion_seg(125), "2 min 05 seg")


class ConstruirRegistroAusenciaTest(unittest.TestCase):
    def test_acumula_totales_entre_llamadas(self) -> None:
        vm1 = construir_registro_ausencia(30, 0, 0)
        self.assertEqual(vm1.total_acumulado_seg, 30)
        self.assertEqual(vm1.conteo_acumulado, 1)
        vm2 = construir_registro_ausencia(45, vm1.total_acumulado_seg, vm1.conteo_acumulado)
        self.assertEqual(vm2.total_acumulado_seg, 75)
        self.assertEqual(vm2.conteo_acumulado, 2)

    def test_pluralizacion(self) -> None:
        vm1 = construir_registro_ausencia(10, 0, 0)
        self.assertEqual(vm1.texto_conteo, "1 vez")
        vm2 = construir_registro_ausencia(10, 10, 1)
        self.assertEqual(vm2.texto_conteo, "2 veces")


class ResolverAvisoVisibleTest(unittest.TestCase):
    def test_modelo_yolo_faltante(self) -> None:
        resultado = resolver_aviso_visible(["No se encontro el modelo YOLO de somnolencia."])
        self.assertEqual(resultado, "Monitoreo visual activo y listo para uso.")

    def test_ultralytics_no_disponible(self) -> None:
        resultado = resolver_aviso_visible(["Ultralytics no esta disponible."])
        self.assertEqual(resultado, "Monitoreo visual activo con analisis principal disponible.")

    def test_onnxruntime(self) -> None:
        resultado = resolver_aviso_visible(["Problema con onnxruntime."])
        self.assertEqual(resultado, "Motor visual activo. Ajustando compatibilidad del entorno.")

    def test_fallback_primer_aviso(self) -> None:
        self.assertEqual(resolver_aviso_visible(["Aviso generico"]), "Aviso generico")

    def test_lista_vacia(self) -> None:
        self.assertEqual(resolver_aviso_visible([]), "Sistema activo.")


class PerfilRequiereConfiguracionTest(unittest.TestCase):
    def test_nombre_vacio_o_generico_requiere_configuracion(self) -> None:
        self.assertTrue(perfil_requiere_configuracion(""))
        self.assertTrue(perfil_requiere_configuracion("  Usuario Local  "))
        self.assertTrue(perfil_requiere_configuracion("usuario_local"))

    def test_nombre_real_no_requiere_configuracion(self) -> None:
        self.assertFalse(perfil_requiere_configuracion("Luis"))


class PerfilResumenRolTest(unittest.TestCase):
    def test_formato(self) -> None:
        self.assertEqual(perfil_resumen_rol("Usuario", "empleado"), "Usuario | Empleado")


if __name__ == "__main__":
    unittest.main()
