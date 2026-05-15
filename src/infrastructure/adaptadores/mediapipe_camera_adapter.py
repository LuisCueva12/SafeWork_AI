"""
Adaptador de Entrada (Driving Adapter): MediaPipeCameraAdapter.
Única clase que conoce OpenCV y MediaPipe.

Usa la nueva MediaPipe Tasks API (v0.10.x) con PoseLandmarker.
El modelo pose_landmarker_lite.task debe estar en assets/.
"""
from __future__ import annotations
from typing import Optional
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

from ...domain.puertos.puerto_captura_corporal import PuertoCapturaCorporal
from ...domain.entities.postura import CoordenadaCorporal, LecturaCorporal


# Índices estándar de landmarks de MediaPipe Pose
INDICE_NARIZ = 0
INDICE_OREJA_IZQUIERDA = 7
INDICE_OREJA_DERECHA = 8
INDICE_HOMBRO_IZQUIERDO = 11
INDICE_HOMBRO_DERECHO = 12
INDICE_CADERA_IZQUIERDA = 23
INDICE_CADERA_DERECHA = 24


def _resolver_ruta_modelo() -> str:
    ruta = os.path.join(os.getcwd(), "assets", "pose_landmarker_lite.task")
    if os.path.exists(ruta):
        return ruta
    # Fallback: buscar desde la ubicación del archivo hacia la raíz del proyecto
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidato = os.path.join(directorio_actual, "assets", "pose_landmarker_lite.task")
        if os.path.exists(candidato):
            return candidato
        directorio_actual = os.path.dirname(directorio_actual)
    return ruta  # devuelve el path original para que el error sea descriptivo


class MediaPipeCameraAdapter(PuertoCapturaCorporal):

    def __init__(self, indice_camara: int = 0) -> None:
        self._indice_camara = indice_camara
        self._captura_video: Optional[cv2.VideoCapture] = None
        self._ultimo_frame: Optional[np.ndarray] = None
        self._pose_landmarker: Optional[mp_vision.PoseLandmarker] = None
        self._frame_numero = 0
        self._inicializar_pose_landmarker()

    def _inicializar_pose_landmarker(self) -> None:
        ruta_modelo = _resolver_ruta_modelo()
        opciones = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=ruta_modelo),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._pose_landmarker = mp_vision.PoseLandmarker.create_from_options(opciones)

    def iniciar_captura(self) -> None:
        self._captura_video = cv2.VideoCapture(self._indice_camara)
        self._captura_video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._captura_video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def obtener_lectura_corporal(self) -> Optional[LecturaCorporal]:
        if not self._captura_video or not self._captura_video.isOpened():
            return None

        captura_exitosa, frame_bgr = self._captura_video.read()
        if not captura_exitosa:
            return None

        self._ultimo_frame = frame_bgr
        self._frame_numero += 1

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        resultado = self._pose_landmarker.detect(imagen_mp)

        if not resultado.pose_landmarks or len(resultado.pose_landmarks) == 0:
            return None

        return self._extraer_lectura_desde_landmarks(resultado.pose_landmarks[0])

    def obtener_ultimo_frame(self) -> Optional[np.ndarray]:
        return self._ultimo_frame

    def detener_captura(self) -> None:
        if self._captura_video:
            self._captura_video.release()
            self._captura_video = None
        if self._pose_landmarker:
            self._pose_landmarker.close()

    def esta_activo(self) -> bool:
        return self._captura_video is not None and self._captura_video.isOpened()

    def _extraer_lectura_desde_landmarks(self, landmarks) -> LecturaCorporal:
        def lm_a_coordenada(indice: int) -> CoordenadaCorporal:
            lm = landmarks[indice]
            return CoordenadaCorporal(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibilidad=lm.visibility if lm.visibility is not None else 1.0,
            )

        return LecturaCorporal(
            nariz=lm_a_coordenada(INDICE_NARIZ),
            oreja_izquierda=lm_a_coordenada(INDICE_OREJA_IZQUIERDA),
            oreja_derecha=lm_a_coordenada(INDICE_OREJA_DERECHA),
            hombro_izquierdo=lm_a_coordenada(INDICE_HOMBRO_IZQUIERDO),
            hombro_derecho=lm_a_coordenada(INDICE_HOMBRO_DERECHO),
            cadera_izquierda=lm_a_coordenada(INDICE_CADERA_IZQUIERDA),
            cadera_derecha=lm_a_coordenada(INDICE_CADERA_DERECHA),
        )
