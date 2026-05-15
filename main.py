"""
Punto de entrada de la aplicación SafeWork AI.
Ensambla la arquitectura hexagonal mediante Dependency Injection
y lanza la aplicación en modo de escritorio.

Ejecución: python main.py
"""
from __future__ import annotations
import threading
import sys
from src.infrastructure.adaptadores.mediapipe_camera_adapter import MediaPipeCameraAdapter
from src.infrastructure.adaptadores.tkinter_alert_adapter import TkinterAlertAdapter
from src.infrastructure.adaptadores.system_tray_adapter import SystemTrayAdapter
from src.application.casos_de_uso.analizar_postura_use_case import AnalizarPosturaUseCase


def ensamblar_y_ejecutar_aplicacion() -> None:
    adaptador_camara = MediaPipeCameraAdapter(indice_camara=0)
    adaptador_alertas = TkinterAlertAdapter()

    caso_de_uso = AnalizarPosturaUseCase(
        captura_corporal=adaptador_camara,
        emision_alertas=adaptador_alertas,
    )

    ventana_principal = adaptador_alertas.construir_ventana_principal()

    def al_mostrar_ventana():
        ventana_principal.after(0, ventana_principal.deiconify)

    def al_salir_aplicacion():
        caso_de_uso.detener_monitoreo()
        adaptador_tray.detener_tray()
        ventana_principal.after(0, ventana_principal.destroy)

    adaptador_tray = SystemTrayAdapter(
        al_mostrar_ventana=al_mostrar_ventana,
        al_salir=al_salir_aplicacion,
    )

    ventana_principal.after(300, lambda: _iniciar_monitoreo_en_hilo(caso_de_uso))
    ventana_principal.after(800, adaptador_tray.iniciar_tray)

    ventana_principal.mainloop()


def _iniciar_monitoreo_en_hilo(caso_de_uso: AnalizarPosturaUseCase) -> None:
    hilo = threading.Thread(
        target=caso_de_uso.iniciar_monitoreo,
        daemon=True,
        name="SafeWork-Monitor",
    )
    hilo.start()


if __name__ == "__main__":
    ensamblar_y_ejecutar_aplicacion()
