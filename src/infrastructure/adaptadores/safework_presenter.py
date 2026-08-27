from __future__ import annotations

from dataclasses import dataclass

from .safework_styles import LEVEL_COLORS, STATUS_COLORS


@dataclass(frozen=True)
class MetricaCircularVM:
    valor_texto: str
    porcentaje: float
    subtexto: str
    descripcion: str
    color_hex: str


@dataclass(frozen=True)
class MetricasLegiblesVM:
    ojos: MetricaCircularVM
    postura: MetricaCircularVM
    distancia: MetricaCircularVM
    energia: MetricaCircularVM
    indice_global: int
    detalle_indice_global: str
    tendencia_indice: list[float]
    riesgo_postura: str
    riesgo_pantalla: str
    riesgo_fatiga: str
    resumen_texto: str


@dataclass(frozen=True)
class IncidenciasResumenVM:
    total_hoy: str
    total_semana: str
    total_mes: str
    tendencia: list[float]
    mostrar_ultima_incidencia: bool
    ultima_incidencia_texto: str
    log_resumen_texto: str


@dataclass(frozen=True)
class EstadoSistemaVM:
    estado_base: str
    color: str
    color_fondo: str
    texto_auxiliar: str


@dataclass(frozen=True)
class NivelRiesgoVM:
    color_glow_hex: str
    texto_auxiliar: str
    ocultar_banner: bool


@dataclass(frozen=True)
class AusenciaRegistradaVM:
    texto_ultima_ausencia: str
    texto_total_acumulado: str
    texto_conteo: str
    mensaje_status_bar: str
    total_acumulado_seg: float
    conteo_acumulado: int


def parsear_metricas(metricas: str) -> dict[str, float]:
    valores: dict[str, float] = {}
    for bloque in metricas.split("|"):
        partes = bloque.strip().split(" ", 1)
        if len(partes) != 2:
            continue
        clave, valor = partes
        try:
            valores[clave] = float(valor)
        except ValueError:
            continue
    return valores


def describir_indice_global(score: int) -> str:
    if score >= 85:
        return "Indice general\nOperacion optima"
    if score >= 70:
        return "Indice general\nSeguimiento estable"
    if score >= 50:
        return "Indice general\nAtencion preventiva"
    return "Indice general\nCorreccion prioritaria"


def etiqueta_riesgo(valor: float) -> str:
    valor_int = max(0, min(100, int(round(valor))))
    if valor_int < 20:
        return f"Bajo ({valor_int}%)"
    if valor_int < 45:
        return f"Medio ({valor_int}%)"
    return f"Alto ({valor_int}%)"


def construir_metricas_legibles(metricas: str) -> MetricasLegiblesVM:
    valores = parsear_metricas(metricas)
    ear = valores.get("EAR", 0.0)
    mar = valores.get("MAR", 0.0)
    cuello = valores.get("Cuello", 0.0)
    lateral = valores.get("Lateral", 0.0)
    proximidad = valores.get("Prox", 0.0)
    calidad = valores.get("Calidad", 100.0)

    ear_pct = min(100.0, max(0.0, (ear / 0.34) * 100.0))
    if ear < 0.22:
        ojos_sub, ojos_color, ojos_desc = "Cerrados", "#dc2626", "Nivel de alerta alto"
    elif ear < 0.28:
        ojos_sub, ojos_color, ojos_desc = "Cansados", "#d97706", "Descansa la vista"
    else:
        ojos_sub, ojos_color, ojos_desc = "Relajados", "#059669", "Estado ocular normal"

    severidad_postural = max(cuello / 32.0, lateral / 10.0)
    postura_pct = max(0.0, min(100.0, 100.0 - severidad_postural * 100.0))
    if cuello >= 28.0:
        pos_sub, pos_color, pos_desc = "Inclinada", "#dc2626", "Corrige la posicion"
    elif cuello >= 14.0 or lateral >= 7.5:
        pos_sub, pos_color, pos_desc = "Por corregir", "#d97706", "Ajusta tu postura"
    else:
        pos_sub, pos_color, pos_desc = "Correcta", "#059669", "Manten la espalda recta"

    dist_pct = max(0.0, min(100.0, 100.0 - (proximidad / 0.9) * 100.0))
    if proximidad >= 0.72:
        dist_sub, dist_color, dist_desc = "Muy cerca", "#dc2626", "Aleja el monitor"
    elif proximidad >= 0.35:
        dist_sub, dist_color, dist_desc = "Leve", "#d97706", "Rango recomendado"
    else:
        dist_sub, dist_color, dist_desc = "Optima", "#059669", "Rango recomendado"

    mar_pct = max(0.0, min(100.0, 100.0 - (mar / 0.6) * 100.0))
    if mar > 0.45:
        ene_sub, ene_color, ene_desc = "Bostezo", "#d97706", "Posible fatiga"
    elif mar > 0.20:
        ene_sub, ene_color, ene_desc = "Variable", "#d97706", "Atencion baja"
    else:
        ene_sub, ene_color, ene_desc = "Estable", "#059669", "Concentracion normal"

    indice_global = int(
        round(
            postura_pct * 0.30
            + ear_pct * 0.24
            + dist_pct * 0.18
            + mar_pct * 0.18
            + max(0.0, min(100.0, calidad)) * 0.10
        )
    )
    indice_global = max(0, min(100, indice_global))

    return MetricasLegiblesVM(
        ojos=MetricaCircularVM(f"{int(ear_pct)}%", ear_pct, ojos_sub, ojos_desc, ojos_color),
        postura=MetricaCircularVM(f"{int(postura_pct)}%", postura_pct, pos_sub, pos_desc, pos_color),
        distancia=MetricaCircularVM(f"{int(dist_pct)}%", dist_pct, dist_sub, dist_desc, dist_color),
        energia=MetricaCircularVM(f"{int(mar_pct)}%", mar_pct, ene_sub, ene_desc, ene_color),
        indice_global=indice_global,
        detalle_indice_global=describir_indice_global(indice_global),
        tendencia_indice=[
            max(0.0, 100.0 - postura_pct),
            max(0.0, 100.0 - dist_pct),
            max(0.0, 100.0 - ear_pct),
            max(0.0, 100.0 - mar_pct),
        ],
        riesgo_postura=etiqueta_riesgo(100.0 - postura_pct),
        riesgo_pantalla=etiqueta_riesgo(100.0 - dist_pct),
        riesgo_fatiga=etiqueta_riesgo(max(100.0 - ear_pct, 100.0 - mar_pct)),
        resumen_texto=f"{ojos_sub.lower()}, postura {pos_sub.lower()}, distancia {dist_sub.lower()}.",
    )


def construir_resumen_incidencias(resumen: object) -> IncidenciasResumenVM | None:
    if not isinstance(resumen, dict):
        return None

    metricas = resumen.get("metricas_agregadas", {})
    periodos = metricas.get("periodos", {}) if isinstance(metricas, dict) else {}
    if not isinstance(periodos, dict):
        periodos = {}

    hoy = float(int(periodos.get("hoy", 0) or 0))
    sem = float(int(periodos.get("ultimos_7_dias", 0) or 0))
    mes = float(int(periodos.get("ultimos_30_dias", 0) or 0))

    ultimas = resumen.get("ultimas_incidencias", [])
    if isinstance(ultimas, list) and ultimas:
        ultima = ultimas[0] if isinstance(ultimas[0], dict) else {}
        estado_str = str(ultima.get("estado", "Incidencia"))
        severidad = str(ultima.get("severidad", "informativa")).upper()
        descripcion = str(ultima.get("descripcion", "Sin descripcion"))
        timestamp = str(ultima.get("timestamp", ""))
        mostrar_ultima_incidencia = True
        ultima_incidencia_texto = f"{estado_str}\n{descripcion}"
        log_resumen_texto = f"{timestamp} | Prioridad: {severidad}"
    else:
        mostrar_ultima_incidencia = False
        ultima_incidencia_texto = ""
        log_resumen_texto = "El historial mostrara la ultima incidencia validada."

    return IncidenciasResumenVM(
        total_hoy=str(int(hoy)),
        total_semana=str(int(sem)),
        total_mes=str(int(mes)),
        tendencia=[mes / 4.0, sem / 2.0, hoy * 0.8, hoy],
        mostrar_ultima_incidencia=mostrar_ultima_incidencia,
        ultima_incidencia_texto=ultima_incidencia_texto,
        log_resumen_texto=log_resumen_texto,
    )


def construir_estado_sistema(estado_bruto: str) -> EstadoSistemaVM:
    estado_base = estado_bruto.replace(" - Cooldown activo", "")
    clave = next((k for k in STATUS_COLORS if k in estado_base.upper()), None)
    color, bg = STATUS_COLORS.get(clave, ("#1e293b", "#f8fafc"))
    texto_auxiliar = (
        "Pausa temporal entre alertas" if "Cooldown activo" in estado_bruto else "Monitoreo activo"
    )
    return EstadoSistemaVM(estado_base, color, bg, texto_auxiliar)


def construir_estado_error(titulo: str, aux: str) -> EstadoSistemaVM:
    color, bg = STATUS_COLORS.get("ERROR", ("#ef4444", "#1f0202"))
    return EstadoSistemaVM(titulo, color, bg, aux)


def construir_nivel_riesgo(nivel: str) -> NivelRiesgoVM:
    etiquetas = {
        "OBSERVACION":       "Observacion preventiva",
        "RIESGO_LEVE":       "Riesgo leve",
        "RIESGO_CONFIRMADO": "Riesgo confirmado",
        "RIESGO_CRITICO":    "Riesgo critico",
    }
    return NivelRiesgoVM(
        color_glow_hex=LEVEL_COLORS.get(nivel, "#0f2040"),
        texto_auxiliar=etiquetas.get(nivel, "Monitoreo activo"),
        ocultar_banner=nivel != "RIESGO_CRITICO",
    )


def formatear_duracion_seg(segundos: float) -> str:
    if segundos < 60:
        return f"{int(segundos)} seg"
    minutos = int(segundos) // 60
    resto = int(segundos) % 60
    return f"{minutos} min {resto:02d} seg"


def construir_registro_ausencia(
    duracion_seg: float,
    total_previo_seg: float,
    conteo_previo: int,
) -> AusenciaRegistradaVM:
    conteo = conteo_previo + 1
    total = total_previo_seg + duracion_seg
    duracion_fmt = formatear_duracion_seg(duracion_seg)
    total_fmt = formatear_duracion_seg(total)
    conteo_texto = f"{conteo} vez" if conteo == 1 else f"{conteo} veces"
    return AusenciaRegistradaVM(
        texto_ultima_ausencia=f"Ultima ausencia: {duracion_fmt}\nEl usuario regreso al puesto de trabajo.",
        texto_total_acumulado=total_fmt,
        texto_conteo=conteo_texto,
        mensaje_status_bar=f"Retorno registrado - ausencia de {duracion_fmt}",
        total_acumulado_seg=total,
        conteo_acumulado=conteo,
    )


def resolver_aviso_visible(avisos: list[str]) -> str:
    for aviso in avisos:
        aviso_up = aviso.upper()
        if "NO SE ENCONTRO EL MODELO YOLO" in aviso_up:
            return "Monitoreo visual activo y listo para uso."
        if "ULTRALYTICS NO ESTA DISPONIBLE" in aviso_up:
            return "Monitoreo visual activo con analisis principal disponible."
        if "ONNXRUNTIME" in aviso_up:
            return "Motor visual activo. Ajustando compatibilidad del entorno."
    return avisos[0] if avisos else "Sistema activo."


def perfil_requiere_configuracion(nombre: str) -> bool:
    return nombre.strip().lower() in {"", "usuario local", "usuario_local"}


def perfil_resumen_rol(rol: str, tipo_usuario: str) -> str:
    return f"{rol} | {tipo_usuario.title()}"
