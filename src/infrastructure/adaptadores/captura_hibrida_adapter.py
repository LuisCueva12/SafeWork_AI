from __future__ import annotations

import math
import os
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

from ...domain.entities.postura import Coordenada, LecturaHibrida
from ...domain.puertos import PuertoCapturaCorporal
from ...domain.reglas.normalizacion_yolo import normalizar_clase_yolo
from ..config import SafeWorkSettings

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

OJO_IZQ_PUNTOS = [362, 385, 387, 263, 373, 380]
OJO_DER_PUNTOS = [33, 160, 158, 133, 153, 144]
BOCA_PUNTOS = [78, 81, 13, 311, 308, 402, 14, 178]
INDICE_NARIZ_FACE = 1


class CapturaHibridaAdapter(PuertoCapturaCorporal):
    def __init__(self, settings: SafeWorkSettings) -> None:
        self._settings = settings
        self._captura_video: cv2.VideoCapture | None = None
        self._ultimo_frame: np.ndarray | None = None
        self._ultimo_timestamp_ms = 0
        self._face_landmarker: mp_vision.FaceLandmarker | None = None
        self._pose_landmarker: mp_vision.PoseLandmarker | None = None
        self._modelo_yolo = None
        self._contador_frames = 0
        self._ultima_clase_yolo = "normal"
        self._ultima_confianza_yolo = 0.0
        self._configurar_ultralytics()
        self._inicializar_modelos()

    def iniciar_captura(self) -> None:
        self._captura_video = cv2.VideoCapture(self._settings.capture_index)
        self._captura_video.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.frame_width)
        self._captura_video.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.frame_height)

    def capturar_lectura(self) -> LecturaHibrida | None:
        if self._captura_video is None or not self._captura_video.isOpened():
            return None

        ok, frame_bgr = self._captura_video.read()
        if not ok:
            return None

        frame_bgr = cv2.flip(frame_bgr, 1)
        self._ultimo_frame = frame_bgr.copy()
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        timestamp_ms = self._nuevo_timestamp()
        res_face = self._face_landmarker.detect_for_video(imagen_mp, timestamp_ms)
        res_pose = self._pose_landmarker.detect_for_video(imagen_mp, timestamp_ms)

        rostro_detectado = bool(res_face.face_landmarks)
        cuerpo_detectado = bool(res_pose.pose_landmarks)
        lectura = LecturaHibrida(
            ear=0.0,
            mar=0.0,
            nariz_y=0.0,
            ancho_cara=0.0,
            rostro_detectado=rostro_detectado,
            cuerpo_detectado=cuerpo_detectado,
            yolo_clase="normal",
            yolo_confianza=0.0,
        )

        face_lms = None
        if rostro_detectado:
            face_lms = res_face.face_landmarks[0]
            self._mapear_rostro(lectura, face_lms)
        if cuerpo_detectado:
            pose_lms = res_pose.pose_landmarks[0]
            self._mapear_cuerpo(lectura, pose_lms)
        if face_lms is not None:
            lectura.yolo_clase, lectura.yolo_confianza = self._clasificar_rostro(frame_rgb, face_lms)

        return lectura

    def obtener_ultimo_frame(self) -> np.ndarray | None:
        return self._ultimo_frame

    def detener_captura(self) -> None:
        if self._captura_video is not None:
            try:
                self._captura_video.release()
            except Exception:
                pass
            self._captura_video = None
        for resource in (self._face_landmarker, self._pose_landmarker):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass

    def esta_activo(self) -> bool:
        return self._captura_video is not None and self._captura_video.isOpened()

    def _configurar_ultralytics(self) -> None:
        os.environ["YOLO_CONFIG_DIR"] = str(self._settings.yolo_config_dir)
        try:
            Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _inicializar_modelos(self) -> None:
        face_opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(self._settings.face_model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._face_landmarker = mp_vision.FaceLandmarker.create_from_options(face_opts)

        pose_opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(self._settings.pose_model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._pose_landmarker = mp_vision.PoseLandmarker.create_from_options(pose_opts)

        if YOLO is not None and self._settings.yolo_model_path.exists():
            try:
                self._modelo_yolo = YOLO(str(self._settings.yolo_model_path), task="classify")
            except Exception:
                self._modelo_yolo = None

    def _nuevo_timestamp(self) -> int:
        import time

        timestamp_ms = int(time.time() * 1000)
        if timestamp_ms <= self._ultimo_timestamp_ms:
            timestamp_ms = self._ultimo_timestamp_ms + 1
        self._ultimo_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _mapear_rostro(self, lectura: LecturaHibrida, face_landmarks) -> None:
        lectura.ear = (self._calcular_ear(face_landmarks, OJO_IZQ_PUNTOS) + self._calcular_ear(face_landmarks, OJO_DER_PUNTOS)) / 2.0
        lectura.mar = self._calcular_mar(face_landmarks, BOCA_PUNTOS)
        lectura.nariz_y = face_landmarks[INDICE_NARIZ_FACE].y
        if len(face_landmarks) > 454:
            p_izq = face_landmarks[234]
            p_der = face_landmarks[454]
            lectura.ancho_cara = math.sqrt((p_der.x - p_izq.x) ** 2 + (p_der.y - p_izq.y) ** 2)
        lectura.mirando_abajo = self._detectar_mirada_abajo(face_landmarks)

    def _mapear_cuerpo(self, lectura: LecturaHibrida, pose_landmarks) -> None:
        def point_to_coord(index: int) -> Coordenada:
            point = pose_landmarks[index]
            visibility = point.visibility if hasattr(point, "visibility") else 1.0
            return Coordenada(point.x, point.y, point.z, visibility)

        lectura.nariz = point_to_coord(0)
        lectura.oreja_izquierda = point_to_coord(7)
        lectura.oreja_derecha = point_to_coord(8)
        lectura.hombro_izquierdo = point_to_coord(11)
        lectura.hombro_derecho = point_to_coord(12)
        lectura.mano_sobre_rostro = self._mano_sobre_rostro(lectura.nariz, point_to_coord)

    def _clasificar_rostro(self, frame_rgb: np.ndarray, face_landmarks) -> tuple[str, float]:
        if self._modelo_yolo is None:
            return "normal", 0.0

        self._contador_frames += 1
        stride = max(1, self._settings.yolo_inference_stride)
        if self._contador_frames % stride != 0:
            return self._ultima_clase_yolo, self._ultima_confianza_yolo

        try:
            rostro = self._recortar_rostro(frame_rgb, face_landmarks)
            if rostro is None:
                return "normal", 0.0

            resultados = self._modelo_yolo.predict(rostro, verbose=False)
            if not resultados:
                return "normal", 0.0
            probs = getattr(resultados[0], "probs", None)
            if probs is None:
                return "normal", 0.0

            top1 = int(probs.top1)
            confianza = float(getattr(probs, "top1conf", 0.0))
            if confianza < self._settings.yolo_confidence_threshold:
                self._ultima_clase_yolo = "normal"
                self._ultima_confianza_yolo = confianza
                return self._ultima_clase_yolo, self._ultima_confianza_yolo

            nombres = self._modelo_yolo.names
            if isinstance(nombres, dict):
                self._ultima_clase_yolo = normalizar_clase_yolo(str(nombres.get(top1, "normal")))
                self._ultima_confianza_yolo = confianza
                return self._ultima_clase_yolo, self._ultima_confianza_yolo
            if isinstance(nombres, (list, tuple)) and 0 <= top1 < len(nombres):
                self._ultima_clase_yolo = normalizar_clase_yolo(str(nombres[top1]))
                self._ultima_confianza_yolo = confianza
                return self._ultima_clase_yolo, self._ultima_confianza_yolo
        except Exception:
            self._ultima_clase_yolo = "normal"
            self._ultima_confianza_yolo = 0.0
            return self._ultima_clase_yolo, self._ultima_confianza_yolo
        self._ultima_clase_yolo = "normal"
        self._ultima_confianza_yolo = 0.0
        return self._ultima_clase_yolo, self._ultima_confianza_yolo

    @staticmethod
    def _recortar_rostro(frame_rgb: np.ndarray, face_landmarks) -> np.ndarray | None:
        alto, ancho = frame_rgb.shape[:2]
        if not face_landmarks:
            return None

        x_coords = [p.x for p in face_landmarks]
        y_coords = [p.y for p in face_landmarks]
        x_min_f = max(0.0, min(x_coords))
        y_min_f = max(0.0, min(y_coords))
        x_max_f = min(1.0, max(x_coords))
        y_max_f = min(1.0, max(y_coords))

        rostro_ancho = max(0.01, x_max_f - x_min_f)
        rostro_alto = max(0.01, y_max_f - y_min_f)
        pad_x = rostro_ancho * 0.18
        pad_y = rostro_alto * 0.22

        x_min = max(0, int((x_min_f - pad_x) * ancho))
        y_min = max(0, int((y_min_f - pad_y) * alto))
        x_max = min(ancho, int((x_max_f + pad_x) * ancho))
        y_max = min(alto, int((y_max_f + pad_y) * alto))
        if x_max - x_min < 40 or y_max - y_min < 40:
            return None
        return frame_rgb[y_min:y_max, x_min:x_max]

    def _detectar_mirada_abajo(self, face_landmarks) -> bool:
        if len(face_landmarks) < 478:
            return False

        iris_izq_y = face_landmarks[468].y
        ojo_izq_top_y = face_landmarks[386].y
        ojo_izq_bot_y = face_landmarks[374].y
        iris_der_y = face_landmarks[473].y
        ojo_der_top_y = face_landmarks[159].y
        ojo_der_bot_y = face_landmarks[145].y

        alto_izq = ojo_izq_bot_y - ojo_izq_top_y
        alto_der = ojo_der_bot_y - ojo_der_top_y
        if alto_izq <= 0 or alto_der <= 0:
            return False

        pos_izq = (iris_izq_y - ojo_izq_top_y) / alto_izq
        pos_der = (iris_der_y - ojo_der_top_y) / alto_der
        return pos_izq > 0.75 or pos_der > 0.75

    def _mano_sobre_rostro(self, nariz: Coordenada, point_to_coord) -> bool:
        if not nariz.es_confiable():
            return False

        puntos = [point_to_coord(15), point_to_coord(16), point_to_coord(19), point_to_coord(20)]
        for punto in puntos:
            if punto.es_confiable() and self._distancia(punto, nariz) < 0.22:
                return True
        return False

    @staticmethod
    def _distancia(p1, p2) -> float:
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)

    def _calcular_ear(self, landmarks, indices) -> float:
        v1 = self._distancia(landmarks[indices[1]], landmarks[indices[5]])
        v2 = self._distancia(landmarks[indices[2]], landmarks[indices[4]])
        h = self._distancia(landmarks[indices[0]], landmarks[indices[3]])
        return (v1 + v2) / (2.0 * h) if h > 0 else 0.0

    def _calcular_mar(self, landmarks, indices) -> float:
        h = self._distancia(landmarks[indices[0]], landmarks[indices[4]])
        v = self._distancia(landmarks[indices[2]], landmarks[indices[6]])
        return v / h if h > 0 else 0.0
