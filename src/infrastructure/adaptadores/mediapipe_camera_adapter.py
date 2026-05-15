from __future__ import annotations
from typing import Optional, List, Tuple
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from ...domain.puertos.puerto_captura_corporal import PuertoCapturaCorporal
from ...domain.entities.postura import CoordenadaCorporal, LecturaCorporal

INDICE_NARIZ = 0
INDICE_OREJA_IZQUIERDA = 7
INDICE_OREJA_DERECHA = 8
INDICE_HOMBRO_IZQUIERDO = 11
INDICE_HOMBRO_DERECHO = 12
INDICE_CADERA_IZQUIERDA = 23
INDICE_CADERA_DERECHA = 24

CONEXIONES_POSE = [(0, 7), (0, 8), (7, 11), (8, 12), (11, 12), (11, 23), (12, 24), (23, 24)]
PUNTOS_INTERES = [INDICE_NARIZ, INDICE_OREJA_IZQUIERDA, INDICE_OREJA_DERECHA, INDICE_HOMBRO_IZQUIERDO, INDICE_HOMBRO_DERECHO, INDICE_CADERA_IZQUIERDA, INDICE_CADERA_DERECHA]

COLOR_CYAN = (255, 212, 0)
COLOR_VERDE = (145, 185, 16)
COLOR_ROJO = (68, 68, 239)
COLOR_AMARILLO = (11, 158, 245)

def _resolver_ruta_modelo() -> str:
    ruta = os.path.join(os.getcwd(), "assets", "pose_landmarker_lite.task")
    if os.path.exists(ruta):
        return ruta
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidato = os.path.join(directorio_actual, "assets", "pose_landmarker_lite.task")
        if os.path.exists(candidato):
            return candidato
        directorio_actual = os.path.dirname(directorio_actual)
    return ruta

class MediaPipeCameraAdapter(PuertoCapturaCorporal):
    def __init__(self, indice_camara: int = 0) -> None:
        self._indice_camara = indice_camara
        self._captura_video: Optional[cv2.VideoCapture] = None
        self._ultimo_frame: Optional[np.ndarray] = None
        self._ultimo_frame_anotado: Optional[np.ndarray] = None
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
        exito, frame_bgr = self._captura_video.read()
        if not exito:
            return None
        self._ultimo_frame = frame_bgr.copy()
        self._frame_numero += 1
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        resultado = self._pose_landmarker.detect(imagen_mp)
        if not resultado.pose_landmarks:
            self._ultimo_frame_anotado = self._generar_frame_sin_deteccion(frame_bgr)
            return None
        landmarks = resultado.pose_landmarks[0]
        self._ultimo_frame_anotado = self._dibujar_skeleton(frame_bgr, landmarks)
        return self._extraer_lectura_desde_landmarks(landmarks)

    def obtener_ultimo_frame(self) -> Optional[np.ndarray]:
        return self._ultimo_frame

    def obtener_frame_anotado(self) -> Optional[np.ndarray]:
        return self._ultimo_frame_anotado

    def detener_captura(self) -> None:
        if self._captura_video:
            self._captura_video.release()
            self._captura_video = None
        if self._pose_landmarker:
            self._pose_landmarker.close()

    def esta_activo(self) -> bool:
        return self._captura_video is not None and self._captura_video.isOpened()

    def _dibujar_skeleton(self, frame_bgr: np.ndarray, landmarks: list) -> np.ndarray:
        alto, ancho = frame_bgr.shape[:2]
        canvas = cv2.flip(frame_bgr.copy(), 1)
        def coords_px(indice: int) -> Tuple[int, int]:
            lm = landmarks[indice]
            return (int((1.0 - lm.x) * ancho), int(lm.y * alto))
        for idx_a, idx_b in CONEXIONES_POSE:
            try:
                lm_a, lm_b = landmarks[idx_a], landmarks[idx_b]
                if (lm_a.visibility or 0) < 0.4 or (lm_b.visibility or 0) < 0.4: continue
                cv2.line(canvas, coords_px(idx_a), coords_px(idx_b), COLOR_CYAN, 2, cv2.LINE_AA)
            except: continue
        for indice in PUNTOS_INTERES:
            try:
                if (landmarks[indice].visibility or 0) < 0.4: continue
                pt = coords_px(indice)
                cv2.circle(canvas, pt, 7, COLOR_CYAN, -1, cv2.LINE_AA)
                cv2.circle(canvas, pt, 3, (255, 255, 255), -1, cv2.LINE_AA)
            except: continue
        return self._agregar_overlay_texto(canvas, ancho, alto)

    def _agregar_overlay_texto(self, canvas: np.ndarray, ancho: int, alto: int) -> np.ndarray:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (ancho, 32), (10, 14, 26), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)
        cv2.putText(canvas, "SAFEWORK AI | MONITORING", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 212, 255), 1, cv2.LINE_AA)
        return canvas

    def _generar_frame_sin_deteccion(self, frame_bgr: np.ndarray) -> np.ndarray:
        canvas = cv2.flip(frame_bgr.copy(), 1)
        alto, ancho = canvas.shape[:2]
        cv2.putText(canvas, "BUSCANDO PERSONA...", (ancho // 2 - 80, alto // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)
        return canvas

    def _extraer_lectura_desde_landmarks(self, landmarks: list) -> LecturaCorporal:
        def lm_a_co(i: int) -> CoordenadaCorporal:
            lm = landmarks[i]
            return CoordenadaCorporal(lm.x, lm.y, lm.z, lm.visibility if lm.visibility is not None else 1.0)
        return LecturaCorporal(lm_a_co(INDICE_NARIZ), lm_a_co(INDICE_HOMBRO_IZQUIERDO), lm_a_co(INDICE_HOMBRO_DERECHO), lm_a_co(INDICE_OREJA_IZQUIERDA), lm_a_co(INDICE_OREJA_DERECHA), lm_a_co(INDICE_CADERA_IZQUIERDA), lm_a_co(INDICE_CADERA_DERECHA))
