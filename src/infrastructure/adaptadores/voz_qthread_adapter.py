from __future__ import annotations

import queue

import pyttsx3
from PyQt6.QtCore import QThread, pyqtSignal


class VozQThreadAdapter(QThread):
    error_senal = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cola: queue.Queue[str | None] = queue.Queue(maxsize=2)
        self._engine = None

    def emitir_mensaje(self, mensaje: str) -> None:
        if mensaje:
            try:
                self._cola.put_nowait(mensaje)
            except queue.Full:
                pass

    def limpiar_cola(self) -> None:
        with self._cola.mutex:
            self._cola.queue.clear()

    def detener(self) -> None:
        self.limpiar_cola()
        self._cola.put(None)
        self.wait(3000)

    def run(self) -> None:
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 155)
        except Exception as exc:
            self.error_senal.emit(str(exc))
            self._engine = None

        while True:
            mensaje = self._cola.get()
            if mensaje is None:
                break
            if self._engine is None:
                continue
            try:
                self._engine.say(mensaje)
                self._engine.runAndWait()
            except Exception as exc:
                self.error_senal.emit(str(exc))
