"""
Adaptador de System Tray.
Gestiona la presencia en la bandeja del sistema de Windows.

BUG FIXES:
- __future__ annotations para Python 3.10
- pystray necesita correr en hilo daemon para no bloquear la app
- Icono generado correctamente con Pillow
"""
from __future__ import annotations
import threading
from typing import Callable
import pystray
from PIL import Image, ImageDraw


def crear_icono_tray() -> Image.Image:
    imagen = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(imagen)
    # Fondo oscuro circular
    d.ellipse([2, 2, 62, 62], fill="#0A0E1A", outline="#00D4FF", width=3)
    # Punto de estado central
    d.ellipse([22, 22, 42, 42], fill="#10B981")
    return imagen


class SystemTrayAdapter:

    def __init__(
        self,
        al_mostrar_ventana: Callable,
        al_salir: Callable,
    ) -> None:
        self._al_mostrar_ventana = al_mostrar_ventana
        self._al_salir = al_salir
        self._icono_tray: pystray.Icon | None = None

    def iniciar_tray(self) -> None:
        imagen = crear_icono_tray()
        menu = pystray.Menu(
            pystray.MenuItem(
                "Mostrar SafeWork AI",
                self._al_mostrar_ventana,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self._al_salir),
        )
        self._icono_tray = pystray.Icon(
            name="safework_ai",
            icon=imagen,
            title="SafeWork AI · Monitoreando",
            menu=menu,
        )
        hilo = threading.Thread(target=self._icono_tray.run, daemon=True)
        hilo.start()

    def detener_tray(self) -> None:
        if self._icono_tray:
            try:
                self._icono_tray.stop()
            except Exception:
                pass
