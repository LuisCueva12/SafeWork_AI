from __future__ import annotations

from ...domain.entities.postura import LecturaHibrida, NivelRiesgo
from ...domain.reglas.normalizacion_yolo import es_clase_bostezo, es_clase_fatiga, normalizar_clase_yolo


class FusionSensoresService:
    def aplicar(self, lectura: LecturaHibrida | None) -> None:
        if lectura is None:
            return

        clase = normalizar_clase_yolo(lectura.yolo_clase)
        es_bostezo = es_clase_bostezo(clase)
        es_fatiga = es_clase_fatiga(clase)
        if not (es_bostezo or es_fatiga):
            lectura.fusion_nivel = None
            lectura.fusion_motivo = ""
            return

        heuristica_bostezo = lectura.mar >= 0.38
        heuristica_fatiga = lectura.ear > 0 and lectura.ear <= 0.18

        if lectura.yolo_confianza < 0.70:
            lectura.fusion_nivel = NivelRiesgo.OBSERVACION
            lectura.fusion_motivo = "YOLO con confianza baja"
            return

        confirma_bostezo = es_bostezo and heuristica_bostezo
        confirma_fatiga = es_fatiga and heuristica_fatiga
        if lectura.yolo_confianza > 0.75 and (confirma_bostezo or confirma_fatiga):
            lectura.fusion_nivel = NivelRiesgo.RIESGO_CONFIRMADO
            lectura.fusion_motivo = "YOLO y MediaPipe coinciden"
            return

        lectura.fusion_nivel = NivelRiesgo.OBSERVACION
        lectura.fusion_motivo = "YOLO sin redundancia suficiente"
