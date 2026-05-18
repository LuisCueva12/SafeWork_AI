from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from ..entities.postura import LecturaHibrida


class PuertoCapturaCorporal(ABC):
    @abstractmethod
    def iniciar_captura(self) -> None: ...

    @abstractmethod
    def capturar_lectura(self) -> Optional[LecturaHibrida]: ...

    @abstractmethod
    def obtener_ultimo_frame(self) -> Optional[np.ndarray]: ...

    @abstractmethod
    def detener_captura(self) -> None: ...

    @abstractmethod
    def esta_activo(self) -> bool: ...
