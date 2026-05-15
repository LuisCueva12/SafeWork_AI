"""
Puerto de salida (Driven Port).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.postura import Postura


class PuertoEmisionAlertas(ABC):

    @abstractmethod
    def emitir_alerta_postura_critica(self, postura: Postura) -> None:
        ...

    @abstractmethod
    def emitir_alerta_inactividad(self, minutos_inactivo: float) -> None:
        ...

    @abstractmethod
    def actualizar_estado_visual(self, postura: Postura) -> None:
        ...

    @abstractmethod
    def esta_mostrando_alerta(self) -> bool:
        ...
