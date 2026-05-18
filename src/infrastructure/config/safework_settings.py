from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SafeWorkSettings:
    calibration_seconds: float
    frame_interval_ms: int
    capture_index: int
    frame_width: int
    frame_height: int
    assets_dir: Path
    app_data_dir: Path
    yolo_config_dir: Path
    profile_path: Path
    events_path: Path
    incidents_summary_path: Path
    session_report_path: Path
    yolo_model_path: Path
    face_model_path: Path
    pose_model_path: Path

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
            frame_interval_ms=33,
            capture_index=0,
            frame_width=640,
            frame_height=480,
            assets_dir=assets_dir,
            app_data_dir=app_data_dir,
            yolo_config_dir=yolo_config_dir,
            profile_path=app_data_dir / "user_profile.json",
            events_path=app_data_dir / "event_history.json",
            incidents_summary_path=app_data_dir / "incident_summary.json",
            session_report_path=app_data_dir / "session_report.json",
            yolo_model_path=assets_dir / "yolov8n-drowsiness.onnx",
            face_model_path=assets_dir / "face_landmarker.task",
            pose_model_path=assets_dir / "pose_landmarker_lite.task",
        )

    @staticmethod
    def _resolver_project_root() -> Path:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parents[3]
