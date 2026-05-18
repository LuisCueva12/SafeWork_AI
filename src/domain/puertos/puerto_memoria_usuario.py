from __future__ import annotations

from typing import Protocol

from ..entities.trabajador import SesionTrabajador


class PuertoMemoriaUsuario(Protocol):
    def cargar_sesion_base(self) -> dict[str, float]: ...

    def guardar_sesion_base(self, sesion: SesionTrabajador) -> None: ...

    def registrar_evento(self, evento: dict[str, object]) -> None: ...

    def obtener_resumen_incidencias(self) -> dict[str, object]: ...

    def guardar_reporte_sesion(self, reporte: dict[str, object]) -> None: ...
