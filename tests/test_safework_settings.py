from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.config.safework_settings import SafeWorkSettings


class SafeWorkSettingsTest(unittest.TestCase):
    def test_reporta_aviso_cuando_falta_modelo_yolo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            (assets / "face_landmarker.task").write_text("face", encoding="utf-8")
            (assets / "pose_landmarker_lite.task").write_text("pose", encoding="utf-8")

            with patch.object(SafeWorkSettings, "_resolver_project_root", return_value=root):
                settings = SafeWorkSettings.from_runtime()

            errores, avisos = settings.validar_runtime()

            self.assertFalse(errores)
            self.assertEqual(len(avisos), 1)
            self.assertIn("modo degradado", avisos[0].lower())

    def test_construye_contexto_operativo_desde_variables_de_entorno(self) -> None:
        env = {
            "SAFEWORK_COMPANY_NAME": "Empresa Demo",
            "SAFEWORK_WORKER_ID": "user-42",
            "SAFEWORK_POSITION_PROFILE": "oficina",
            "SAFEWORK_RISK_PROFILE": "alto",
            "SAFEWORK_CAMERA_PROFILE": "webcam_externa",
            "SAFEWORK_LIGHTING_PROFILE": "alta",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            (assets / "face_landmarker.task").write_text("face", encoding="utf-8")
            (assets / "pose_landmarker_lite.task").write_text("pose", encoding="utf-8")

            with patch.dict(os.environ, env, clear=False):
                with patch.object(SafeWorkSettings, "_resolver_project_root", return_value=root):
                    settings = SafeWorkSettings.from_runtime()

            contexto = settings.contexto_operativo()

            self.assertEqual(contexto["empresa"], "Empresa Demo")
            self.assertEqual(contexto["trabajador"], "user-42")
            self.assertEqual(contexto["perfil_riesgo"], "alto")
            self.assertEqual(contexto["camara"], "webcam_externa")

    def test_detecta_modelo_yolo_con_nombre_alternativo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            (assets / "face_landmarker.task").write_text("face", encoding="utf-8")
            (assets / "pose_landmarker_lite.task").write_text("pose", encoding="utf-8")
            (assets / "best.pt").write_text("fake-model", encoding="utf-8")

            with patch.object(SafeWorkSettings, "_resolver_project_root", return_value=root):
                settings = SafeWorkSettings.from_runtime()

            self.assertEqual(settings.yolo_model_path.name, "best.pt")
            errores, avisos = settings.validar_runtime()
            self.assertFalse(errores)
            self.assertFalse(avisos)


if __name__ == "__main__":
    unittest.main()
