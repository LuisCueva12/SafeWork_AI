from __future__ import annotations
import threading
from typing import Callable
import pystray
from PIL import Image, ImageDraw

def crear_icono_tray() -> Image.Image:
    i = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(i)
    d.ellipse([2, 2, 62, 62], fill="#0A0E1A", outline="#00D4FF", width=3)
    d.ellipse([22, 22, 42, 42], fill="#10B981")
    return i

class SystemTrayAdapter:
    def __init__(self, al_mostrar: Callable, al_salir: Callable) -> None:
        self._al_mostrar = al_mostrar
        self._al_salir = al_salir
        self._icono: pystray.Icon | None = None

    def iniciar_tray(self) -> None:
        m = pystray.Menu(pystray.MenuItem("Mostrar SafeWork AI", self._al_mostrar, default=True), pystray.Menu.SEPARATOR, pystray.MenuItem("Salir", self._al_salir))
        self._icono = pystray.Icon("safework_ai", crear_icono_tray(), "SafeWork AI", m)
        threading.Thread(target=self._icono.run, daemon=True).start()

    def detener_tray(self) -> None:
        if self._icono:
            try: self._icono.stop()
            except: pass
