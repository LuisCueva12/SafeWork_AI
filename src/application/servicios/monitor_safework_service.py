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
        self._ultimo_estado_confirmado = EstadoAlerta.CALIBRANDO
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
        self._ultimo_estado_confirmado = estado.estado

        if estado.estado == EstadoAlerta.OPTIMO and self._sesion.racha_estable >= 6:
            self._perfilador.actualizar_perfil_operativo(
                lectura,
                self._sesion,
                estado.proximidad_monitor,
                estado.angulo_cuello,
                estado.angulo_lateral,
            )
            if self._sesion.muestras_aprendizaje and self._sesion.muestras_aprendizaje % 12 == 0:
                self._guardar_perfil_base()

        mensaje_alerta = None
        if estado.requiere_bloqueo() and not self._sesion.en_cooldown():
            self._sesion.incrementar_contador_alertas()
            self._sesion.registrar_alerta_disparada()
            mensaje_alerta = self._construir_mensaje_alerta(estado.estado)
            self._registrar_evento(estado, lectura)
            self._guardar_perfil_base()
            self._guardar_reporte_sesion()

        if self._sesion.total_lecturas_validas and self._sesion.total_lecturas_validas % 45 == 0:
            self._guardar_reporte_sesion()

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
        if self._memoria_usuario is None:
            return
        if self._sesion.muestras_calibracion <= 0 and self._sesion.muestras_aprendizaje <= 0:
            return
        self._memoria_usuario.guardar_sesion_base(self._sesion)

    def _guardar_reporte_sesion(self) -> None:
        if self._memoria_usuario is None:
            return
        self._memoria_usuario.guardar_reporte_sesion(self._construir_reporte_sesion())

    def _registrar_evento(self, estado: EstadoFisico, lectura: LecturaHibrida) -> None:
        if self._memoria_usuario is None:
            return
        categoria = self._clasificar_categoria(estado.estado)
        severidad = self._clasificar_severidad(estado.estado)
        validacion = self._clasificar_validacion(estado.estado)
        evento = {
            "timestamp": datetime.now().isoformat(),
            "incident_id": f"{estado.estado.name.lower()}-{int(datetime.now().timestamp() * 1000)}",
            "estado": estado.estado.value,
            "categoria": categoria,
            "severidad": severidad,
            "validacion": validacion,
            "descripcion": self._construir_detalle_estado(estado.estado),
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

    def _construir_reporte_sesion(self) -> dict[str, object]:
        return {
            "updated_at": datetime.now().isoformat(),
            "estado_actual": self._ultimo_estado_confirmado.value,
            "duracion_sesion_segundos": round(self._sesion.duracion_sesion().total_seconds(), 1),
            "lecturas_validas": self._sesion.total_lecturas_validas,
            "alertas_emitidas": self._sesion.total_alertas_emitidas,
            "muestras_calibracion": self._sesion.muestras_calibracion,
            "muestras_aprendizaje": self._sesion.muestras_aprendizaje,
            "indice_fatiga_actual": round(self._sesion.indice_fatiga, 3),
            "perfil_base": {
                "ear": round(self._sesion.base_ear, 4),
                "mar": round(self._sesion.base_mar, 4),
                "ancho_cara": round(self._sesion.base_ancho_cara, 4),
                "ratio_postural": round(self._sesion.base_ratio_y, 4),
                "z_nariz_rel": round(self._sesion.base_z_nariz_rel, 4),
            },
            "rachas_actuales": {
                "estable": self._sesion.racha_estable,
                "cercania_monitor": self._sesion.racha_cercania_monitor,
                "postura_riesgo": self._sesion.racha_postura_riesgo,
                "cabeceo_riesgo": self._sesion.racha_cabeceo_riesgo,
                "sueno_yolo": self._sesion.racha_yolo_sueno,
                "bostezo_yolo": self._sesion.racha_yolo_bostezo,
            },
        }

    @staticmethod
    def _clasificar_categoria(estado: EstadoAlerta) -> str:
        categorias = {
            EstadoAlerta.FATIGA_EXTREMA: "somnolencia",
            EstadoAlerta.ADVERTENCIA_SUENO: "fatiga",
            EstadoAlerta.CABECEO: "somnolencia",
            EstadoAlerta.CERCANIA_MONITOR: "proximidad",
            EstadoAlerta.MALA_POSTURA: "ergonomia",
        }
        return categorias.get(estado, "general")

    @staticmethod
    def _clasificar_severidad(estado: EstadoAlerta) -> str:
        severidades = {
            EstadoAlerta.FATIGA_EXTREMA: "critica",
            EstadoAlerta.CABECEO: "alta",
            EstadoAlerta.CERCANIA_MONITOR: "media",
            EstadoAlerta.MALA_POSTURA: "media",
            EstadoAlerta.ADVERTENCIA_SUENO: "preventiva",
        }
        return severidades.get(estado, "informativa")

    @staticmethod
    def _clasificar_validacion(estado: EstadoAlerta) -> str:
        validaciones = {
            EstadoAlerta.FATIGA_EXTREMA: "critica_confirmada",
            EstadoAlerta.CABECEO: "confirmada_por_patron",
            EstadoAlerta.CERCANIA_MONITOR: "confirmada_por_repeticion",
            EstadoAlerta.MALA_POSTURA: "confirmada_por_sostenimiento",
            EstadoAlerta.ADVERTENCIA_SUENO: "preventiva_validada",
        }
        return validaciones.get(estado, "informativa")

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
