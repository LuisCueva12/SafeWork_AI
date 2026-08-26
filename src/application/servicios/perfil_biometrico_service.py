from __future__ import annotations

import time

from ...domain.entities.postura import LecturaHibrida
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.reglas.calculo_postural import calcular_ratio_postural


class PerfilBiometricoService:
    def __init__(self, duracion_segundos: float = 5.0, min_muestras: int = 20, max_duracion_segundos: float = 12.0) -> None:
        self._duracion_segundos = duracion_segundos
        self._min_muestras = min_muestras
        self._max_duracion_segundos = max_duracion_segundos
        self._inicio = time.monotonic()

    def en_calibracion(self, sesion: SesionTrabajador) -> bool:
        transcurrido = time.monotonic() - self._inicio
        if transcurrido < self._duracion_segundos:
            return True
        if sesion.muestras_calibracion < self._min_muestras and transcurrido < self._max_duracion_segundos:
            return True
        return False

    def resumen_calibracion(self, sesion: SesionTrabajador) -> str:
        transcurrido = time.monotonic() - self._inicio
        return f"Muestras base: {sesion.muestras_calibracion}/{self._min_muestras} | Tiempo: {transcurrido:.1f}s"

    def registrar_muestra(self, lectura: LecturaHibrida, sesion: SesionTrabajador) -> None:
        if not (lectura.rostro_detectado and lectura.cuerpo_detectado):
            return

        if lectura.ear > 0 and lectura.ear < 0.15:
            return
        if lectura.mar > 0.45:
            return  

        ancho_hombros, ratio_y = calcular_ratio_postural(lectura)
        if ancho_hombros <= 0:
            return

        n = sesion.muestras_calibracion
        z_hombro_medio = (lectura.hombro_izquierdo.z + lectura.hombro_derecho.z) / 2.0
        z_nariz_rel = lectura.nariz.z - z_hombro_medio

        sesion.base_ancho_hombros = (sesion.base_ancho_hombros * n + ancho_hombros) / (n + 1)
        sesion.base_ratio_y = (sesion.base_ratio_y * n + ratio_y) / (n + 1)
        sesion.base_z_nariz_rel = (sesion.base_z_nariz_rel * n + z_nariz_rel) / (n + 1)
        sesion.base_ancho_cara = (sesion.base_ancho_cara * n + lectura.ancho_cara) / (n + 1)
        sesion.base_ear = (sesion.base_ear * n + lectura.ear) / (n + 1)
        sesion.base_mar = (sesion.base_mar * n + lectura.mar) / (n + 1)
        sesion.muestras_calibracion += 1

    def actualizar_perfil_operativo(
        self,
        lectura: LecturaHibrida,
        sesion: SesionTrabajador,
        proximidad_monitor: float,
        angulo_cuello: float,
        angulo_lateral: float,
    ) -> None:
        if not (lectura.rostro_detectado and lectura.cuerpo_detectado):
            return
        if lectura.mirando_abajo or lectura.mano_sobre_rostro:
            return
        if proximidad_monitor >= 0.35 or angulo_cuello >= 12.0 or angulo_lateral >= 6.0:
            return
        if sesion.racha_boca_abierta > 0 or sesion.bostezo_actual_activo:
            return
        if lectura.ear <= 0 or lectura.mar <= 0:
            return

        ancho_hombros, ratio_y = calcular_ratio_postural(lectura)
        if ancho_hombros <= 0:
            return

        z_hombro_medio = (lectura.hombro_izquierdo.z + lectura.hombro_derecho.z) / 2.0
        z_nariz_rel = lectura.nariz.z - z_hombro_medio
        tasa = 0.015

        sesion.base_ancho_hombros = self._mezclar_base(sesion.base_ancho_hombros, ancho_hombros, tasa)
        sesion.base_ratio_y = self._mezclar_base(sesion.base_ratio_y, ratio_y, tasa)
        sesion.base_z_nariz_rel = self._mezclar_base(sesion.base_z_nariz_rel, z_nariz_rel, tasa)
        sesion.base_ancho_cara = self._mezclar_base(sesion.base_ancho_cara, lectura.ancho_cara, tasa)
        sesion.base_ear = self._mezclar_base(sesion.base_ear, lectura.ear, tasa)
        sesion.base_mar = self._mezclar_base(sesion.base_mar, lectura.mar, tasa)
        sesion.muestras_aprendizaje += 1

    @staticmethod
    def _mezclar_base(actual: float, nuevo: float, tasa: float) -> float:
        if actual == 0.0:
            return nuevo
        return actual * (1.0 - tasa) + nuevo * tasa
