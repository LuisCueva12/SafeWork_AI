from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ...domain.entities.trabajador import SesionTrabajador


class MemoriaUsuarioJsonAdapter:
    def __init__(self, profile_path: Path, events_path: Path) -> None:
        self._profile_path = profile_path
        self._events_path = events_path
        for path in (self._profile_path.parent, self._events_path.parent):
            path.mkdir(parents=True, exist_ok=True)

    def cargar_sesion_base(self) -> dict[str, float]:
        try:
            data = json.loads(self._profile_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}

    def guardar_sesion_base(self, sesion: SesionTrabajador) -> None:
        payload = {
            "base_ancho_hombros": sesion.base_ancho_hombros,
            "base_ratio_y": sesion.base_ratio_y,
            "base_z_nariz_rel": sesion.base_z_nariz_rel,
            "base_ancho_cara": sesion.base_ancho_cara,
            "base_ear": sesion.base_ear,
            "base_mar": sesion.base_mar,
            "muestras_calibracion": float(sesion.muestras_calibracion),
            "updated_at": datetime.now().timestamp(),
        }
        self._profile_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def registrar_evento(self, evento: dict[str, object]) -> None:
        eventos = []
        try:
            eventos = json.loads(self._events_path.read_text(encoding="utf-8"))
            if not isinstance(eventos, list):
                eventos = []
        except Exception:
            eventos = []
        eventos.append(evento)
        self._events_path.write_text(json.dumps(eventos[-300:], ensure_ascii=False, indent=2), encoding="utf-8")
