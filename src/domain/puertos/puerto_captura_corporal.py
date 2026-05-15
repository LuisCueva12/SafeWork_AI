"""
Puerto de entrada (Driving Port).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.postura import LecturaCorporal


class PuertoCapturaCorporal(ABC):

    @abstractmethod
    def iniciar_captura(self) -> None:
        ...

    @abstractmethod
    def obtener_lectura_corporal(self) -> LecturaCorporal | None:
        ...

    @abstractmethod
    def detener_captura(self) -> None:
        ...

    @abstractmethod
    def esta_activo(self) -> bool:
        ...
