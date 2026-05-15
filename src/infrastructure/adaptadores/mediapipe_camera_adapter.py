"""
Adaptador de Entrada (Driving Adapter): MediaPipeCameraAdapter.
Única clase que conoce OpenCV y MediaPipe.

Usa la nueva MediaPipe Tasks API (v0.10.x) con PoseLandmarker.
El modelo pose_landmarker_lite.task debe estar en assets/.

FEATURE: obtener_frame_anotado() retorna el último frame con el
skeleton de pose dibujado encima, listo para mostrar en la UI.
"""
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


# Índices estándar de landmarks de MediaPipe Pose
INDICE_NARIZ = 0
INDICE_OREJA_IZQUIERDA = 7
INDICE_OREJA_DERECHA = 8
INDICE_HOMBRO_IZQUIERDO = 11
INDICE_HOMBRO_DERECHO = 12
INDICE_CADERA_IZQUIERDA = 23
INDICE_CADERA_DERECHA = 24

# Conexiones a dibujar: (índice_a, índice_b)
CONEXIONES_POSE = [
    (0, 7),   # nariz → oreja izq
    (0, 8),   # nariz → oreja der
    (7, 11),  # oreja izq → hombro izq
    (8, 12),  # oreja der → hombro der
    (11, 12), # hombro izq → hombro der
    (11, 23), # hombro izq → cadera izq
    (12, 24), # hombro der → cadera der
    (23, 24), # cadera izq → cadera der
]

# Puntos de interés para dibujar su estado
PUNTOS_INTERES = [
    INDICE_NARIZ,
    INDICE_OREJA_IZQUIERDA,
    INDICE_OREJA_DERECHA,
    INDICE_HOMBRO_IZQUIERDO,
    INDICE_HOMBRO_DERECHO,
    INDICE_CADERA_IZQUIERDA,
    INDICE_CADERA_DERECHA,
]

# Colores BGR para el overlay
COLOR_CYAN        = (255, 212, 0)    # BGR de #00D4FF
COLOR_VERDE       = (145, 185, 16)   # BGR de #10B981
COLOR_ROJO        = (68, 68, 239)    # BGR de #EF4444
COLOR_AMARILLO    = (11, 158, 245)   # BGR de #F59E0B
COLOR_GRIS_TENUE  = (100, 100, 100)
COLOR_FONDO_SCAN  = (26, 14, 10)     # BGR de #0A0E1A


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
        self._ultimos_landmarks: Optional[list] = None
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

        self._ultimo_frame = frame_bgr.copy()
        self._frame_numero += 1

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        resultado = self._pose_landmarker.detect(imagen_mp)

        if not resultado.pose_landmarks or len(resultado.pose_landmarks) == 0:
            self._ultimos_landmarks = None
            self._ultimo_frame_anotado = self._generar_frame_sin_deteccion(frame_bgr)
            return None

        landmarks = resultado.pose_landmarks[0]
        self._ultimos_landmarks = landmarks
        self._ultimo_frame_anotado = self._dibujar_skeleton(frame_bgr, landmarks)

        return self._extraer_lectura_desde_landmarks(landmarks)

    def obtener_ultimo_frame(self) -> Optional[np.ndarray]:
        return self._ultimo_frame

    def obtener_frame_anotado(self) -> Optional[np.ndarray]:
        """Retorna el último frame con el skeleton de pose dibujado (BGR)."""
        return self._ultimo_frame_anotado

    def detener_captura(self) -> None:
        if self._captura_video:
            self._captura_video.release()
            self._captura_video = None
        if self._pose_landmarker:
            self._pose_landmarker.close()

    def esta_activo(self) -> bool:
        return self._captura_video is not None and self._captura_video.isOpened()

    # -------------------------------------------------------------------------
    # Dibujo del Skeleton sobre el frame
    # -------------------------------------------------------------------------

    def _dibujar_skeleton(self, frame_bgr: np.ndarray, landmarks: list) -> np.ndarray:
        alto, ancho = frame_bgr.shape[:2]
        canvas = frame_bgr.copy()

        # Voltear horizontalmente (efecto espejo natural para el usuario)
        canvas = cv2.flip(canvas, 1)

        def coords_px(indice: int) -> Tuple[int, int]:
            lm = landmarks[indice]
            # Al voltear, invertimos X
            px = int((1.0 - lm.x) * ancho)
            py = int(lm.y * alto)
            return (px, py)

        # 1. Dibujar conexiones (líneas del skeleton)
        for idx_a, idx_b in CONEXIONES_POSE:
            try:
                lm_a = landmarks[idx_a]
                lm_b = landmarks[idx_b]
                vis_min = min(
                    lm_a.visibility if lm_a.visibility else 0,
                    lm_b.visibility if lm_b.visibility else 0,
                )
                if vis_min < 0.4:
                    continue
                alpha = int(min(vis_min, 1.0) * 220)
                pt_a = coords_px(idx_a)
                pt_b = coords_px(idx_b)
                cv2.line(canvas, pt_a, pt_b, COLOR_CYAN, 2, cv2.LINE_AA)
            except (IndexError, AttributeError):
                continue

        # 2. Dibujar puntos de interés
        for indice in PUNTOS_INTERES:
            try:
                lm = landmarks[indice]
                vis = lm.visibility if lm.visibility else 0
                if vis < 0.4:
                    continue
                pt = coords_px(indice)
                # Círculo exterior (glow)
                cv2.circle(canvas, pt, 7, COLOR_CYAN, -1, cv2.LINE_AA)
                # Punto interior blanco
                cv2.circle(canvas, pt, 3, (255, 255, 255), -1, cv2.LINE_AA)
            except (IndexError, AttributeError):
                continue

        # 3. Overlay de información en el frame
        canvas = self._agregar_overlay_texto(canvas, landmarks, ancho, alto)

        return canvas

    def _agregar_overlay_texto(
        self,
        canvas: np.ndarray,
        landmarks: list,
        ancho: int,
        alto: int,
    ) -> np.ndarray:
        # Panel semi-transparente superior
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (ancho, 32), (10, 14, 26), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        # Texto de estado
        cv2.putText(
            canvas,
            "SafeWork AI  |  POSE DETECTION ACTIVE",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 212, 255),
            1,
            cv2.LINE_AA,
        )

        # Indicador de frame número (esquina inf derecha)
        cv2.putText(
            canvas,
            f"#{self._frame_numero}",
            (ancho - 70, alto - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (80, 80, 80),
            1,
            cv2.LINE_AA,
        )

        return canvas

    def _generar_frame_sin_deteccion(self, frame_bgr: np.ndarray) -> np.ndarray:
        canvas = cv2.flip(frame_bgr.copy(), 1)
        alto, ancho = canvas.shape[:2]

        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (ancho, 32), (10, 14, 26), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        cv2.putText(
            canvas,
            "SafeWork AI  |  Buscando persona...",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (100, 100, 100),
            1,
            cv2.LINE_AA,
        )
        return canvas

    # -------------------------------------------------------------------------
    # Extracción de lectura de dominio
    # -------------------------------------------------------------------------

    def _extraer_lectura_desde_landmarks(self, landmarks: list) -> LecturaCorporal:
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
