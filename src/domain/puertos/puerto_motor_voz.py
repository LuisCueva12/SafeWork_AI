from __future__ import annotations

from typing import Protocol


class PuertoMotorVoz(Protocol):
    def emitir_mensaje(self, mensaje: str) -> None: ...

    def detener(self) -> None: ...
