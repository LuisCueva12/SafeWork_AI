from __future__ import annotations

import os
from pathlib import Path

os.environ["YOLO_CONFIG_DIR"] = str(Path.cwd() / "ultralytics_config")

from ultralytics import YOLO


def exportar_modelo() -> None:
    try:
        Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
        modelo = YOLO("yolov8n-cls.pt")
        ruta_exportada = Path(
            modelo.export(
                format="onnx",
                imgsz=224,
                dynamic=True,
            )
        )
        destino = ruta_exportada.with_name("yolov8n-drowsiness.onnx")
        if destino.exists():
            destino.unlink()
        ruta_exportada.replace(destino)
        print(f"Exportacion exitosa: {destino}")
    except Exception as exc:
        print(f"Error en la exportacion: {exc}")


if __name__ == "__main__":
    exportar_modelo()
