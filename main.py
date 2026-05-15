from __future__ import annotations
import threading
from src.infrastructure.adaptadores.mediapipe_camera_adapter import MediaPipeCameraAdapter
from src.infrastructure.adaptadores.tkinter_alert_adapter import TkinterAlertAdapter
from src.infrastructure.adaptadores.system_tray_adapter import SystemTrayAdapter
from src.application.casos_de_uso.analizar_postura_use_case import AnalizarPosturaUseCase

def ejecutar() -> None:
    cam = MediaPipeCameraAdapter(0)
    ui = TkinterAlertAdapter()
    ui.registrar_fuente_frame(cam.obtener_frame_anotado)
    uc = AnalizarPosturaUseCase(cam, ui)
    v = ui.construir_ventana_principal()
    v.withdraw()

    def mostrar(): v.after(0, v.deiconify)
    def salir():
        uc.detener_monitoreo()
        tray.detener_tray()
        v.after(0, v.destroy)

    tray = SystemTrayAdapter(mostrar, salir)
    v.after(300, lambda: threading.Thread(target=uc.iniciar_monitoreo, daemon=True).start())
    v.after(800, tray.iniciar_tray)
    v.mainloop()

if __name__ == "__main__":
    ejecutar()
