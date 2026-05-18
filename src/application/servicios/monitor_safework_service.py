from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ...domain.entities.postura import EstadoAlerta, EstadoFisico, LecturaHibrida
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.puertos import PuertoMemoriaUsuario
from ...domain.reglas.calculo_postural import analizar_lectura_hibrida
from .perfil_biometrico_service import PerfilBiometricoService


@dataclass
class ResultadoMonitoreo:
    estado_fisico: EstadoFisico
    mensaje_estado: str
    detalle_estado: str
    mensaje_alerta: str | None = None
    resumen_metricas: str = ""


class MonitorSafeWorkService:
    def __init__(
        self,
        calibracion_segundos: float = 5.0,
        min_muestras_calibracion: int = 20,
        max_duracion_calibracion_segundos: float = 12.0,
        memoria_usuario: PuertoMemoriaUsuario | None = None,
    ) -> None:
        self._sesion = SesionTrabajador()
        self._memoria_usuario = memoria_usuario
        self._perfilador = PerfilBiometricoService(
            calibracion_segundos,
            min_muestras=min_muestras_calibracion,
            max_duracion_segundos=max_duracion_calibracion_segundos,
        )
        self._cargar_perfil_base()

    @property
    def sesion(self) -> SesionTrabajador:
        return self._sesion

    def procesar_lectura(self, lectura: LecturaHibrida | None) -> ResultadoMonitoreo:
        if self._perfilador.en_calibracion(self._sesion):
            if lectura is not None:
                self._perfilador.registrar_muestra(lectura, self._sesion)
                if self._sesion.muestras_calibracion and self._sesion.muestras_calibracion % 5 == 0:
                    self._guardar_perfil_base()
            return ResultadoMonitoreo(
                estado_fisico=EstadoFisico(0.0, 0.0, 0.0, 0.0, 0.0, EstadoAlerta.CALIBRANDO),
                mensaje_estado="CALIBRANDO",
                detalle_estado="Construyendo el perfil biometrico inicial del usuario.",
                resumen_metricas=self._perfilador.resumen_calibracion(self._sesion),
            )

        if lectura is None or (not lectura.rostro_detectado and not lectura.cuerpo_detectado):
            estado = EstadoFisico(0.0, 0.0, 0.0, 0.0, 0.0, EstadoAlerta.AUSENTE)
            return ResultadoMonitoreo(
                estado_fisico=estado,
                mensaje_estado=estado.estado.value,
                detalle_estado="No se detecta rostro o cuerpo con confianza suficiente.",
                resumen_metricas="Sin lectura corporal valida.",
            )

        self._sesion.registrar_deteccion()
        estado = analizar_lectura_hibrida(lectura, self._sesion)
        mensaje_alerta = None
        if estado.requiere_bloqueo() and not self._sesion.en_cooldown():
            self._sesion.incrementar_contador_alertas()
            self._sesion.registrar_alerta_disparada()
            mensaje_alerta = self._construir_mensaje_alerta(estado.estado)
            self._registrar_evento(estado, lectura)
            self._guardar_perfil_base()

        mensaje_estado = estado.estado.value
        if self._sesion.en_cooldown() and estado.estado != EstadoAlerta.AUSENTE:
            mensaje_estado = f"{estado.estado.value} - Cooldown activo"

        return ResultadoMonitoreo(
            estado_fisico=estado,
            mensaje_estado=mensaje_estado,
            detalle_estado=self._construir_detalle_estado(estado.estado),
            mensaje_alerta=mensaje_alerta,
            resumen_metricas=self._construir_resumen_metricas(estado),
        )

    def _cargar_perfil_base(self) -> None:
        if self._memoria_usuario is None:
            return
        payload = self._memoria_usuario.cargar_sesion_base()
        for campo in (
            "base_ancho_hombros",
            "base_ratio_y",
            "base_z_nariz_rel",
            "base_ancho_cara",
            "base_ear",
            "base_mar",
        ):
            valor = payload.get(campo)
            if not isinstance(valor, (int, float)):
                continue
            if campo == "base_z_nariz_rel":
                setattr(self._sesion, campo, float(valor))
                continue
            if valor > 0:
                setattr(self._sesion, campo, float(valor))

    def _guardar_perfil_base(self) -> None:
        if self._memoria_usuario is None or self._sesion.muestras_calibracion <= 0:
            return
        self._memoria_usuario.guardar_sesion_base(self._sesion)

    def _registrar_evento(self, estado: EstadoFisico, lectura: LecturaHibrida) -> None:
        if self._memoria_usuario is None:
            return
        evento = {
            "timestamp": datetime.now().isoformat(),
            "estado": estado.estado.value,
            "ear": round(estado.ear, 4),
            "mar": round(estado.mar, 4),
            "angulo_cuello": round(estado.angulo_cuello, 2),
            "angulo_lateral": round(estado.angulo_lateral, 2),
            "proximidad_monitor": round(estado.proximidad_monitor, 3),
            "yolo_clase": lectura.yolo_clase,
            "mirando_abajo": lectura.mirando_abajo,
            "mano_sobre_rostro": lectura.mano_sobre_rostro,
            "muestras_calibracion": self._sesion.muestras_calibracion,
            "indice_fatiga": round(self._sesion.indice_fatiga, 3),
        }
        self._memoria_usuario.registrar_evento(evento)

    @staticmethod
    def _construir_mensaje_alerta(estado: EstadoAlerta) -> str:
        mensajes = {
            EstadoAlerta.FATIGA_EXTREMA: "Fatiga extrema detectada. Toma una pausa breve y rehidratate.",
            EstadoAlerta.CABECEO: "Cabeceo detectado. Es recomendable detenerte y descansar unos minutos.",
            EstadoAlerta.CERCANIA_MONITOR: "Estas demasiado cerca de la pantalla. Alejate un poco y manten la postura.",
            EstadoAlerta.MALA_POSTURA: "Mala postura sostenida. Alinea espalda, cuello y hombros.",
            EstadoAlerta.ADVERTENCIA_SUENO: "Bostezo validado. Realiza una pausa activa para recuperar enfoque.",
        }
        return mensajes.get(estado, estado.value)

    @staticmethod
    def _construir_detalle_estado(estado: EstadoAlerta) -> str:
        detalles = {
            EstadoAlerta.OPTIMO: "Monitoreo activo y sin riesgo inmediato.",
            EstadoAlerta.CALIBRANDO: "Construyendo el perfil biometrico inicial del usuario.",
            EstadoAlerta.AUSENTE: "No se detecta rostro o cuerpo con confianza suficiente.",
            EstadoAlerta.CERCANIA_MONITOR: "Se detecta una cercania excesiva al monitor.",
            EstadoAlerta.MALA_POSTURA: "Se detecto un patron ergonomico de riesgo sostenido.",
            EstadoAlerta.CABECEO: "Se detecta cabeceo compatible con somnolencia.",
            EstadoAlerta.FATIGA_EXTREMA: "El patron ocular indica posible microsueno.",
            EstadoAlerta.ADVERTENCIA_SUENO: "Se detectaron bostezos compatibles con fatiga.",
        }
        return detalles.get(estado, "")

    @staticmethod
    def _construir_resumen_metricas(estado: EstadoFisico) -> str:
        return (
            f"EAR {estado.ear:.2f} | MAR {estado.mar:.2f} | "
            f"Cuello {estado.angulo_cuello:.1f} | Lateral {estado.angulo_lateral:.1f} | "
            f"Prox {estado.proximidad_monitor:.2f}"
        )
