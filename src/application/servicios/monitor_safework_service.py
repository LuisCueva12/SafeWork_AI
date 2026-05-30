from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ...domain.entities.postura import EstadoAlerta, EstadoFisico, LecturaHibrida, NivelRiesgo
from ...domain.entities.trabajador import SesionTrabajador
from ...domain.puertos import PuertoMemoriaUsuario
from ...domain.reglas.calculo_postural import analizar_lectura_hibrida
from .pausa_activa_service import PausaActiva, PausaActivaService
from .perfil_biometrico_service import PerfilBiometricoService


@dataclass
class ResultadoMonitoreo:
    estado_fisico: EstadoFisico
    mensaje_estado: str
    detalle_estado: str
    mensaje_alerta: str | None = None
    pausa_activa: PausaActiva | None = None
    resumen_metricas: str = ""


class MonitorSafeWorkService:
    def __init__(
        self,
        calibracion_segundos: float = 5.0,
        min_muestras_calibracion: int = 20,
        max_duracion_calibracion_segundos: float = 12.0,
        memoria_usuario: PuertoMemoriaUsuario | None = None,
        sensibilidad: str = "media",
        cooldown_alerta_segundos: int = 45,
        contexto_operativo: dict[str, str] | None = None,
    ) -> None:
        self._sesion = SesionTrabajador()
        self._sesion.sensibilidad = sensibilidad
        self._sesion.cooldown_alerta_segundos = cooldown_alerta_segundos
        self._sesion.contexto_operativo = contexto_operativo or {}
        self._memoria_usuario = memoria_usuario
        self._ultimo_estado_confirmado = EstadoAlerta.CALIBRANDO
        self._ultima_calidad_deteccion = 100.0
        self._pausas = PausaActivaService()
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
            self._sesion.registrar_ausencia()
            estado = EstadoFisico(
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                EstadoAlerta.AUSENTE,
                calidad_deteccion=0.0,
                puntajes_riesgo={"calidad": 0, "cercania": 0, "postura": 0, "fatiga": 0},
                evidencias=("sin_lectura_valida",),
                accion_recomendada="Ubicate nuevamente frente a la camara.",
            )
            self._ultima_calidad_deteccion = estado.calidad_deteccion
            return ResultadoMonitoreo(
                estado_fisico=estado,
                mensaje_estado=estado.estado.value,
                detalle_estado="No se detecta rostro o cuerpo con confianza suficiente.",
                resumen_metricas="Sin lectura corporal valida.",
            )

        self._sesion.registrar_deteccion()
        if self._sesion.en_ventana_reingreso():
            estado = EstadoFisico(
                lectura.ear,
                lectura.mar,
                0.0,
                0.0,
                0.0,
                EstadoAlerta.LECTURA_INESTABLE,
                calidad_deteccion=max(60.0, self._ultima_calidad_deteccion),
                puntajes_riesgo={"calidad": int(round(max(60.0, self._ultima_calidad_deteccion))), "cercania": 0, "postura": 0, "fatiga": 0},
                evidencias=("reingreso_estabilizando",),
                accion_recomendada="Permanece estable un instante mientras se normaliza la lectura.",
            )
            self._ultima_calidad_deteccion = estado.calidad_deteccion
            self._ultimo_estado_confirmado = estado.estado
            return ResultadoMonitoreo(
                estado_fisico=estado,
                mensaje_estado=estado.estado.value,
                detalle_estado="Reingreso detectado: estabilizando la lectura antes de evaluar riesgos.",
                resumen_metricas="Reingreso detectado. Esperando estabilidad de postura y rostro.",
            )

        estado = analizar_lectura_hibrida(lectura, self._sesion)
        self._ultima_calidad_deteccion = estado.calidad_deteccion
        self._ultimo_estado_confirmado = estado.estado
        self._actualizar_registro_nivel(estado)

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
        pausa_activa = None
        if estado.requiere_alerta_voz() and not self._sesion.en_cooldown():
            self._sesion.incrementar_contador_alertas()
            self._sesion.registrar_alerta_disparada()
            pausa_activa = self._pausas.recomendar(estado.estado, self._sesion.total_alertas_emitidas)
            mensaje_alerta = self._construir_mensaje_alerta(estado.estado, pausa_activa)
            self._registrar_evento(estado, lectura, pausa_activa)
            self._guardar_perfil_base()
            self._guardar_reporte_sesion()

        # Reducir la frecuencia de escritura a disco (de 45 a 150 frames = 10s a 15fps)
        # Esto evita bloqueos de I/O en el hilo de visión, haciéndolo más rápido.
        if self._sesion.total_lecturas_validas and self._sesion.total_lecturas_validas % 150 == 0:
            self._guardar_reporte_sesion()

        mensaje_estado = estado.estado.value
        if self._sesion.en_cooldown() and estado.estado != EstadoAlerta.AUSENTE:
            mensaje_estado = f"{estado.estado.value} - Cooldown activo"

        return ResultadoMonitoreo(
            estado_fisico=estado,
            mensaje_estado=mensaje_estado,
            detalle_estado=self._construir_detalle_estado(estado.estado),
            mensaje_alerta=mensaje_alerta,
            pausa_activa=pausa_activa,
            resumen_metricas=self._construir_resumen_metricas(estado),
        )

    def _actualizar_registro_nivel(self, estado: EstadoFisico) -> None:
        if estado.estado in {
            EstadoAlerta.OPTIMO,
            EstadoAlerta.CALIBRANDO,
            EstadoAlerta.AUSENTE,
            EstadoAlerta.LECTURA_INESTABLE,
        }:
            return
        self._sesion.actualizar_nivel_riesgo(
            estado.estado.value,
            estado.nivel_riesgo,
            estado.duracion_riesgo_segundos,
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

    def guardar_reporte_actual(self) -> None:
        self._guardar_reporte_sesion()

    def _registrar_evento(
        self,
        estado: EstadoFisico,
        lectura: LecturaHibrida,
        pausa_activa: PausaActiva | None,
    ) -> None:
        if self._memoria_usuario is None:
            return
        categoria = self._clasificar_categoria(estado.estado)
        severidad = self._clasificar_severidad_por_nivel(estado.nivel_riesgo)
        validacion = self._clasificar_validacion(estado.estado)
        evento = {
            "timestamp": datetime.now().isoformat(),
            "incident_id": f"{estado.estado.name.lower()}-{int(datetime.now().timestamp() * 1000)}",
            "estado": estado.estado.value,
            "nivel_riesgo": estado.nivel_riesgo.value,
            "duracion_riesgo_segundos": round(estado.duracion_riesgo_segundos, 2),
            "categoria": categoria,
            "severidad": severidad,
            "validacion": validacion,
            "descripcion": self._construir_detalle_estado(estado.estado),
            "accion_recomendada": estado.accion_recomendada,
            "calidad_deteccion": round(estado.calidad_deteccion, 2),
            "puntajes_riesgo": dict(estado.puntajes_riesgo),
            "evidencias": list(estado.evidencias),
            "ear": round(estado.ear, 4),
            "mar": round(estado.mar, 4),
            "angulo_cuello": round(estado.angulo_cuello, 2),
            "angulo_lateral": round(estado.angulo_lateral, 2),
            "proximidad_monitor": round(estado.proximidad_monitor, 3),
            "yolo_clase": lectura.yolo_clase,
            "yolo_confianza": round(lectura.yolo_confianza, 3),
            "mirando_abajo": lectura.mirando_abajo,
            "mano_sobre_rostro": lectura.mano_sobre_rostro,
            "muestras_calibracion": self._sesion.muestras_calibracion,
            "indice_fatiga": round(self._sesion.indice_fatiga, 3),
            "pausa_activa": pausa_activa.to_dict() if pausa_activa is not None else None,
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
            "sensibilidad": self._sesion.sensibilidad,
            "contexto_operativo": dict(self._sesion.contexto_operativo),
            "calidad_ultima_lectura": self._obtener_calidad_actual(),
            "niveles_riesgo_actuales": dict(self._sesion.niveles_riesgo_actuales),
            "incidentes_criticos": self._sesion.incidentes,
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
            EstadoAlerta.LECTURA_INESTABLE: "calidad_deteccion",
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
            EstadoAlerta.LECTURA_INESTABLE: "observacion",
        }
        return severidades.get(estado, "informativa")

    @staticmethod
    def _clasificar_severidad_por_nivel(nivel: NivelRiesgo) -> str:
        severidades = {
            NivelRiesgo.OBSERVACION: "observacion",
            NivelRiesgo.RIESGO_LEVE: "leve",
            NivelRiesgo.RIESGO_CONFIRMADO: "confirmada",
            NivelRiesgo.RIESGO_CRITICO: "critica",
        }
        return severidades[nivel]

    @staticmethod
    def _clasificar_validacion(estado: EstadoAlerta) -> str:
        validaciones = {
            EstadoAlerta.FATIGA_EXTREMA: "critica_confirmada",
            EstadoAlerta.CABECEO: "confirmada_por_patron",
            EstadoAlerta.CERCANIA_MONITOR: "confirmada_por_repeticion",
            EstadoAlerta.MALA_POSTURA: "confirmada_por_sostenimiento",
            EstadoAlerta.ADVERTENCIA_SUENO: "preventiva_validada",
            EstadoAlerta.LECTURA_INESTABLE: "lectura_no_confiable",
        }
        return validaciones.get(estado, "informativa")

    @staticmethod
    def _construir_mensaje_alerta(estado: EstadoAlerta, pausa_activa: PausaActiva | None = None) -> str:
        mensajes = {
            EstadoAlerta.FATIGA_EXTREMA: "Fatiga extrema detectada. Toma una pausa breve y rehidratate.",
            EstadoAlerta.CABECEO: "Cabeceo detectado. Es recomendable detenerte y descansar unos minutos.",
            EstadoAlerta.CERCANIA_MONITOR: "Estas demasiado cerca de la pantalla. Alejate un poco y manten la postura.",
            EstadoAlerta.MALA_POSTURA: "Mala postura sostenida. Alinea espalda, cuello y hombros.",
            EstadoAlerta.ADVERTENCIA_SUENO: "Bostezo validado. Realiza una pausa activa para recuperar enfoque.",
            EstadoAlerta.LECTURA_INESTABLE: "Ajusta tu posicion frente a la camara para mejorar la lectura.",
        }
        mensaje = mensajes.get(estado, estado.value)
        if pausa_activa is not None:
            return f"{mensaje} {pausa_activa.texto_corto()}"
        return mensaje

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
            EstadoAlerta.LECTURA_INESTABLE: "La lectura de camara no es suficientemente estable para registrar incidentes.",
        }
        return detalles.get(estado, "")

    @staticmethod
    def _construir_resumen_metricas(estado: EstadoFisico) -> str:
        return (
            f"EAR {estado.ear:.2f} | MAR {estado.mar:.2f} | "
            f"Cuello {estado.angulo_cuello:.1f} | Lateral {estado.angulo_lateral:.1f} | "
            f"Prox {estado.proximidad_monitor:.2f} | Calidad {estado.calidad_deteccion:.0f}"
        )

    def _obtener_calidad_actual(self) -> float:
        return self._ultima_calidad_deteccion
