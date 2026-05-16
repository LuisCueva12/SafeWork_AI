from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from ..entities.postura import LecturaHibrida
import numpy as np

class PuertoCapturaCorporal(ABC):

    @abstractmethod
    def iniciar_captura(self) -> None: ...

    @abstractmethod
    def obtener_lectura_corporal(self) -> Optional[LecturaHibrida]: ...

    @abstractmethod
    def obtener_ultimo_frame(self) -> Optional[np.ndarray]: ...

    @abstractmethod
    def obtener_frame_anotado(self) -> Optional[np.ndarray]: ...

    @abstractmethod
    def detener_captura(self) -> None: ...

    @abstractmethod
    def esta_activo(self) -> bool: ...
