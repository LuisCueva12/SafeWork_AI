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
