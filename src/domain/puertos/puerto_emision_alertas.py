from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.postura import EstadoFisico

class PuertoEmisionAlertas(ABC):

    @abstractmethod
    def actualizar_estado_visual(self, estado: EstadoFisico) -> None: ...

    @abstractmethod
    def emitir_alerta_bloqueante(self, estado: EstadoFisico) -> None: ...

    @abstractmethod
    def esta_mostrando_alerta(self) -> bool: ...
