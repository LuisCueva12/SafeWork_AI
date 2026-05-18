from __future__ import annotations

from typing import Protocol

from ..entities.trabajador import SesionTrabajador


class PuertoMemoriaUsuario(Protocol):
    def cargar_sesion_base(self) -> dict[str, float]: ...

    def guardar_sesion_base(self, sesion: SesionTrabajador) -> None: ...

    def registrar_evento(self, evento: dict[str, object]) -> None: ...
