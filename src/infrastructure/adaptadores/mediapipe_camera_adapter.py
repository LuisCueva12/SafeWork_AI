from __future__ import annotations
from typing import Optional, Tuple
import os
import math
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from ...domain.puertos.puerto_captura_corporal import PuertoCapturaCorporal
from ...domain.entities.postura import LecturaHibrida, Coordenada

OJO_IZQ_PUNTOS = [362, 385, 387, 263, 373, 380]
OJO_DER_PUNTOS = [33, 160, 158, 133, 153, 144]
BOCA_PUNTOS = [78, 81, 13, 311, 308, 402, 14, 178]
INDICE_NARIZ_FACE = 1

INDICE_NARIZ_POSE = 0
INDICE_OREJA_IZQ_POSE = 7
INDICE_OREJA_DER_POSE = 8
INDICE_HOMBRO_IZQ_POSE = 11
INDICE_HOMBRO_DER_POSE = 12

def _resolver_ruta_modelo(nombre: str) -> str:
    ruta = os.path.join(os.getcwd(), "assets", nombre)
    if os.path.exists(ruta): return ruta
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidato = os.path.join(directorio_actual, "assets", nombre)
        if os.path.exists(candidato): return candidato
        directorio_actual = os.path.dirname(directorio_actual)
    return ruta

class MediaPipeCameraAdapter(PuertoCapturaCorporal):
    def __init__(self, indice_camara: int = 0) -> None:
        self._indice_camara = indice_camara
        self._captura_video: Optional[cv2.VideoCapture] = None
        self._ultimo_frame: Optional[np.ndarray] = None
        self._ultimo_frame_anotado: Optional[np.ndarray] = None
        self._face_landmarker: Optional[mp_vision.FaceLandmarker] = None
        self._pose_landmarker: Optional[mp_vision.PoseLandmarker] = None
        self._inicializar_modelos()

    def _inicializar_modelos(self) -> None:
        face_path = _resolver_ruta_modelo("face_landmarker.task")
        pose_path = _resolver_ruta_modelo("pose_landmarker_lite.task")
        
        face_opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=face_path),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1
        )
        self._face_landmarker = mp_vision.FaceLandmarker.create_from_options(face_opts)
        
        pose_opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=pose_path),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_poses=1
        )
        self._pose_landmarker = mp_vision.PoseLandmarker.create_from_options(pose_opts)

    def iniciar_captura(self) -> None:
        self._captura_video = cv2.VideoCapture(self._indice_camara)
        self._captura_video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._captura_video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def obtener_lectura_corporal(self) -> Optional[LecturaHibrida]:
        if not self._captura_video or not self._captura_video.isOpened():
            return None
        exito, frame_bgr = self._captura_video.read()
        if not exito:
            return None
        self._ultimo_frame = frame_bgr.copy()
        
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        res_face = self._face_landmarker.detect(imagen_mp)
        res_pose = self._pose_landmarker.detect(imagen_mp)
        
        rostro_detectado = bool(res_face.face_landmarks)
        cuerpo_detectado = bool(res_pose.pose_landmarks)
        face_lms = res_face.face_landmarks
        pose_lms = res_pose.pose_landmarks
        
        lectura = LecturaHibrida(ear=0, mar=0, nariz_y=0, ancho_cara=0, rostro_detectado=rostro_detectado, cuerpo_detectado=cuerpo_detectado)
        
        if rostro_detectado:
            f_lms = res_face.face_landmarks[0]
            ear_izq = self._calcular_ear(f_lms, OJO_IZQ_PUNTOS)
            ear_der = self._calcular_ear(f_lms, OJO_DER_PUNTOS)
            lectura.ear = (ear_izq + ear_der) / 2.0
            lectura.mar = self._calcular_mar(f_lms, BOCA_PUNTOS)
            lectura.nariz_y = f_lms[INDICE_NARIZ_FACE].y
            
            if 234 < len(f_lms) and 454 < len(f_lms):
                p_izq = f_lms[234]
                p_der = f_lms[454]
                lectura.ancho_cara = math.sqrt((p_der.x - p_izq.x)**2 + (p_der.y - p_izq.y)**2)
            
        if cuerpo_detectado:
            p_lms = res_pose.pose_landmarks[0]
            
            def mpc_a_c(i):
                if i < len(p_lms):
                    l = p_lms[i]
                    return Coordenada(l.x, l.y, l.z, l.visibility if l.visibility else 1.0)
                return Coordenada(0,0,0,0)
            
            lectura.nariz = mpc_a_c(INDICE_NARIZ_POSE)
            lectura.hombro_izquierdo = mpc_a_c(INDICE_HOMBRO_IZQ_POSE)
            lectura.hombro_derecho = mpc_a_c(INDICE_HOMBRO_DER_POSE)
            lectura.oreja_izquierda = mpc_a_c(INDICE_OREJA_IZQ_POSE)
            lectura.oreja_derecha = mpc_a_c(INDICE_OREJA_DER_POSE)

        self._ultimo_frame_anotado = self._dibujar(frame_bgr, res_face.face_landmarks if rostro_detectado else None, res_pose.pose_landmarks if cuerpo_detectado else None, lectura)
        return lectura

    def obtener_ultimo_frame(self) -> Optional[np.ndarray]:
        return self._ultimo_frame

    def obtener_frame_anotado(self) -> Optional[np.ndarray]:
        return self._ultimo_frame_anotado

    def detener_captura(self) -> None:
        if self._captura_video:
            self._captura_video.release()
            self._captura_video = None
        if self._face_landmarker: self._face_landmarker.close()
        if self._pose_landmarker: self._pose_landmarker.close()

    def esta_activo(self) -> bool:
        return self._captura_video is not None and self._captura_video.isOpened()

    def _dibujar(self, frame_bgr: np.ndarray, face_lms, pose_lms, lectura: LecturaHibrida) -> np.ndarray:
        ancho = frame_bgr.shape[1]
        alto = frame_bgr.shape[0]
        canvas = cv2.flip(frame_bgr.copy(), 1)
        
        def proyectar(lm) -> Tuple[int, int]:
            return int((1.0 - lm.x) * ancho), int(lm.y * alto)

        if pose_lms and len(pose_lms[0]) > max(INDICE_HOMBRO_IZQ_POSE, INDICE_HOMBRO_DER_POSE):
            sh_l = pose_lms[0][INDICE_HOMBRO_IZQ_POSE]
            sh_r = pose_lms[0][INDICE_HOMBRO_DER_POSE]
            if sh_l.visibility >= 0.5 and sh_r.visibility >= 0.5:
                p_l = proyectar(sh_l)
                p_r = proyectar(sh_r)
                
                dy = abs(p_r[1] - p_l[1])
                dx = abs(p_r[0] - p_l[0])
                dist = math.sqrt(dx**2 + dy**2)
                is_tilted = (dy / dist > 0.08) if dist > 0 else False
                
                color_linea = (68, 68, 239) if is_tilted else (129, 185, 16)
                
                cv2.line(canvas, p_l, p_r, color_linea, 2, cv2.LINE_AA)
                for p in (p_l, p_r):
                    cv2.circle(canvas, p, 5, (255, 212, 0), -1)
                    cv2.circle(canvas, p, 8, (255, 212, 0), 1, cv2.LINE_AA)
                
                if len(pose_lms[0]) > INDICE_NARIZ_POSE:
                    nz = pose_lms[0][INDICE_NARIZ_POSE]
                    if nz.visibility >= 0.5:
                        p_nz = proyectar(nz)
                        p_mid = ((p_l[0] + p_r[0]) // 2, (p_l[1] + p_r[1]) // 2)
                        cv2.line(canvas, p_nz, p_mid, (255, 255, 255), 1, cv2.LINE_AA)

        if face_lms and len(face_lms[0]) > 0:
            f_lms = face_lms[0]
            
            color_ojos = (68, 68, 239) if lectura.ear <= 0.15 else (255, 212, 0)
            
            izq_pts = [proyectar(f_lms[i]) for i in OJO_IZQ_PUNTOS if i < len(f_lms)]
            if len(izq_pts) > 1:
                cv2.polylines(canvas, [np.array(izq_pts, dtype=np.int32)], True, color_ojos, 1, cv2.LINE_AA)
                
            der_pts = [proyectar(f_lms[i]) for i in OJO_DER_PUNTOS if i < len(f_lms)]
            if len(der_pts) > 1:
                cv2.polylines(canvas, [np.array(der_pts, dtype=np.int32)], True, color_ojos, 1, cv2.LINE_AA)
                
            color_boca = (68, 68, 239) if lectura.mar >= 0.40 else (129, 185, 16)
            
            boca_pts = [proyectar(f_lms[i]) for i in BOCA_PUNTOS if i < len(f_lms)]
            if len(boca_pts) > 1:
                cv2.polylines(canvas, [np.array(boca_pts, dtype=np.int32)], True, color_boca, 1, cv2.LINE_AA)

        cv2.rectangle(canvas, (0, 0), (ancho, 32), (10, 14, 26), -1)
        cv2.putText(canvas, "⬡ SAFEWORK AI | MONITOR ACTIVO", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 212, 0), 1, cv2.LINE_AA)
        
        overlay_y = 55
        if lectura.rostro_detectado:
            cv2.putText(canvas, f"EAR: {lectura.ear:.2f}", (ancho - 90, overlay_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 212, 0), 1, cv2.LINE_AA)
            cv2.putText(canvas, f"MAR: {lectura.mar:.2f}", (ancho - 90, overlay_y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 212, 0), 1, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "SIN ROSTRO", (ancho - 95, overlay_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (68, 68, 239), 1, cv2.LINE_AA)

        if lectura.cuerpo_detectado:
            cv2.putText(canvas, "ESQUELETO: OK", (10, overlay_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (129, 185, 16), 1, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "SIN CUERPO", (10, overlay_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (68, 68, 239), 1, cv2.LINE_AA)

        return canvas

    def _distancia(self, p1, p2) -> float:
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def _calcular_ear(self, landmarks, indices) -> float:
        v1 = self._distancia(landmarks[indices[1]], landmarks[indices[5]])
        v2 = self._distancia(landmarks[indices[2]], landmarks[indices[4]])
        h = self._distancia(landmarks[indices[0]], landmarks[indices[3]])
        return (v1 + v2) / (2.0 * h) if h > 0 else 0.0

    def _calcular_mar(self, landmarks, indices) -> float:
        h = self._distancia(landmarks[indices[0]], landmarks[indices[4]])
        v = self._distancia(landmarks[indices[2]], landmarks[indices[6]])
        return v / h if h > 0 else 0.0
