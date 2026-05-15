"""
Punto de entrada de la aplicación SafeWork AI.
Ensambla la arquitectura hexagonal mediante Dependency Injection.

Ejecución: python main.py
"""
from __future__ import annotations
import threading
from src.infrastructure.adaptadores.mediapipe_camera_adapter import MediaPipeCameraAdapter
from src.infrastructure.adaptadores.tkinter_alert_adapter import TkinterAlertAdapter
from src.infrastructure.adaptadores.system_tray_adapter import SystemTrayAdapter
from src.application.casos_de_uso.analizar_postura_use_case import AnalizarPosturaUseCase


def ensamblar_y_ejecutar_aplicacion() -> None:
    # 1. Crear adaptadores (Dependency Injection)
    adaptador_camara  = MediaPipeCameraAdapter(indice_camara=0)
    adaptador_alertas = TkinterAlertAdapter()

    # 2. Inyectar el callback de frame anotado → desacopla UI de cámara
    adaptador_alertas.registrar_fuente_frame(adaptador_camara.obtener_frame_anotado)

    # 3. Ensamblar el caso de uso con los puertos
    caso_de_uso = AnalizarPosturaUseCase(
        captura_corporal=adaptador_camara,
        emision_alertas=adaptador_alertas,
    )

    # 4. Construir la UI
    ventana_principal = adaptador_alertas.construir_ventana_principal()

    # 5. Callbacks del system tray
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

    # 6. Arrancar monitoreo y tray después de que el mainloop inicie
    ventana_principal.after(300, lambda: _iniciar_monitoreo_en_hilo(caso_de_uso))
    ventana_principal.after(800, adaptador_tray.iniciar_tray)

    # 7. Bloquear en el mainloop de Tkinter
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
