from __future__ import annotations

import os
import sys
import importlib.util
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SafeWorkSettings:
    calibration_seconds: float
    frame_interval_ms: int
    capture_index: int
    frame_width: int
    frame_height: int
    yolo_inference_stride: int
    yolo_confidence_threshold: float
    mediapipe_inference_stride: int
    debug_hud_enabled: bool
    sensitivity: str
    alert_cooldown_seconds: int
    assets_dir: Path
    app_data_dir: Path
    yolo_config_dir: Path
    profile_path: Path
    events_path: Path
    incidents_summary_path: Path
    session_report_path: Path
    validation_labels_path: Path
    yolo_model_path: Path
    face_model_path: Path
    pose_model_path: Path
    company_name: str
    worker_id: str
    position_profile: str
    risk_profile: str
    camera_profile: str
    lighting_profile: str

    @classmethod
    def from_runtime(cls) -> "SafeWorkSettings":
        project_root = cls._resolver_project_root()
        assets_dir = project_root / "assets"
        app_data_dir = Path(os.getenv("APPDATA", str(project_root / ".runtime_data"))) / "SafeWork AI"
        yolo_config_dir = app_data_dir / "ultralytics_config"

        for directory in (app_data_dir, yolo_config_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        return cls(
            calibration_seconds=5.0,
            frame_interval_ms=66,        
            capture_index=0,
            frame_width=640,
            frame_height=480,
            yolo_inference_stride=8,
            yolo_confidence_threshold=0.55,
            mediapipe_inference_stride=cls._leer_entero_env("SAFEWORK_MEDIAPIPE_STRIDE", 1),
            debug_hud_enabled=os.getenv("SAFEWORK_DEBUG_HUD", "0").strip() == "1",
            sensitivity=os.getenv("SAFEWORK_SENSITIVITY", "media").strip().lower() or "media",
            alert_cooldown_seconds=cls._leer_entero_env("SAFEWORK_ALERT_COOLDOWN_SECONDS", 45),
            assets_dir=assets_dir,
            app_data_dir=app_data_dir,
            yolo_config_dir=yolo_config_dir,
            profile_path=app_data_dir / "user_profile.json",
            events_path=app_data_dir / "event_history.json",
            incidents_summary_path=app_data_dir / "incident_summary.json",
            session_report_path=app_data_dir / "session_report.json",
            validation_labels_path=app_data_dir / "validation_labels.json",
            yolo_model_path=cls._resolver_yolo_model_path(assets_dir, app_data_dir),
            face_model_path=assets_dir / "face_landmarker.task",
            pose_model_path=assets_dir / "pose_landmarker_lite.task",
            company_name=os.getenv("SAFEWORK_COMPANY_NAME", "Softech Peru").strip() or "Softech Peru",
            worker_id=os.getenv("SAFEWORK_WORKER_ID", "usuario_local").strip() or "usuario_local",
            position_profile=os.getenv("SAFEWORK_POSITION_PROFILE", "oficina").strip().lower() or "oficina",
            risk_profile=os.getenv("SAFEWORK_RISK_PROFILE", "estandar").strip().lower() or "estandar",
            camera_profile=os.getenv("SAFEWORK_CAMERA_PROFILE", "webcam_integrada").strip().lower() or "webcam_integrada",
            lighting_profile=os.getenv("SAFEWORK_LIGHTING_PROFILE", "no_especificada").strip().lower() or "no_especificada",
        )

    def contexto_operativo(self) -> dict[str, str]:
        return {
            "empresa": self.company_name,
            "trabajador": self.worker_id,
            "puesto": self.position_profile,
            "perfil_riesgo": self.risk_profile,
            "camara": self.camera_profile,
            "iluminacion": self.lighting_profile,
        }

    def validar_runtime(self) -> tuple[list[str], list[str]]:
        errores: list[str] = []
        avisos: list[str] = []

        if not self.face_model_path.exists():
            errores.append(f"No se encontro el modelo facial: {self.face_model_path.name}")
        if not self.pose_model_path.exists():
            errores.append(f"No se encontro el modelo corporal: {self.pose_model_path.name}")
        if not self.yolo_model_path.exists():
            avisos.append(
                "No se encontro el modelo YOLO de somnolencia. "
                "El monitoreo seguira activo en modo degradado con MediaPipe."
            )
        else:
            sufijo = self.yolo_model_path.suffix.lower()
            if sufijo == ".onnx" and importlib.util.find_spec("onnxruntime") is None:
                avisos.append(
                    "El modelo YOLO esta en formato ONNX, pero onnxruntime no esta instalado. "
                    "El monitoreo YOLO no podra inicializarse."
                )
            if importlib.util.find_spec("ultralytics") is None:
                avisos.append(
                    "Ultralytics no esta instalado en este entorno. "
                    "El monitoreo YOLO no podra inicializarse."
                )

        return errores, avisos

    @staticmethod
    def _resolver_yolo_model_path(assets_dir: Path, app_data_dir: Path) -> Path:
        ruta_env = os.getenv("SAFEWORK_YOLO_MODEL_PATH", "").strip()
        if ruta_env:
            ruta = Path(ruta_env).expanduser()
            if ruta.exists():
                return ruta

        candidatos = (
            assets_dir / "yolov8n-drowsiness.onnx",
            assets_dir / "yolov8n-drowsiness.pt",
            assets_dir / "drowsiness.onnx",
            assets_dir / "drowsiness.pt",
            assets_dir / "best.onnx",
            assets_dir / "best.pt",
            app_data_dir / "yolov8n-drowsiness.onnx",
            app_data_dir / "yolov8n-drowsiness.pt",
            app_data_dir / "drowsiness.onnx",
            app_data_dir / "drowsiness.pt",
            app_data_dir / "best.onnx",
            app_data_dir / "best.pt",
        )
        for candidato in candidatos:
            if candidato.exists():
                return candidato

        return assets_dir / "yolov8n-drowsiness.onnx"

    @staticmethod
    def _resolver_project_root() -> Path:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _leer_entero_env(nombre: str, defecto: int) -> int:
        try:
            return int(os.getenv(nombre, str(defecto)))
        except (TypeError, ValueError):
            return defecto
