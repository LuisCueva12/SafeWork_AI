from __future__ import annotations
import os
import json
import threading
import subprocess
from datetime import datetime
from typing import Optional, Callable
import time
import customtkinter as ctk
from PIL import Image
import cv2
import pyttsx3

from ...domain.puertos.puerto_emision_alertas import PuertoEmisionAlertas
from ...domain.entities.postura import EstadoFisico, EstadoAlerta

PALETA = {
    "fondo_oscuro": "#0A0E1A", "fondo_panel": "#111827", "fondo_card": "#1C2333",
    "borde_card": "#2D3748", "acento_primario": "#00D4FF", "estado_optimo": "#10B981",
    "estado_advertencia": "#F59E0B", "estado_critico": "#EF4444",
    "texto_primario": "#F1F5F9", "texto_secundario": "#94A3B8", "texto_tenue": "#475569",
}
CARPETA_DATOS = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SafeWork AI")
RUTA_HISTORIAL = os.path.join(CARPETA_DATOS, "historial_sueno_postura.json")


class HistorialAlertas:
    def __init__(self) -> None:
        os.makedirs(CARPETA_DATOS, exist_ok=True)

    def registrar(self, tipo: str, detalle: str = "") -> None:
        entrada = {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "hora": datetime.now().strftime("%H:%M:%S"),
            "tipo": tipo,
            "detalle": detalle,
        }
        datos = self._cargar()
        datos.append(entrada)
        with open(RUTA_HISTORIAL, "w", encoding="utf-8") as f:
            json.dump(datos[-500:], f, ensure_ascii=False, indent=2)

    def total(self) -> int:
        return len(self._cargar())

    def ultimas(self, n: int = 8) -> list:
        datos = self._cargar()
        return list(reversed(datos[-n:]))

    def _cargar(self) -> list:
        try:
            with open(RUTA_HISTORIAL, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


def _hablar(mensaje: str) -> None:
    def worker():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(mensaje)
            engine.runAndWait()
        except Exception as e:
            print("Error TTS:", e)
    threading.Thread(target=worker, daemon=True).start()


class TkinterAlertAdapter(PuertoEmisionAlertas):
    def __init__(self) -> None:
        self._ventana: Optional[ctk.CTk] = None
        self._alerta_win: Optional[ctk.CTkToplevel] = None
        self._mostrando_alerta = False
        self._lock = threading.Lock()
        self._label_estado: Optional[ctk.CTkLabel] = None
        self._label_desc: Optional[ctk.CTkLabel] = None
        self._label_sesion: Optional[ctk.CTkLabel] = None
        self._label_contador: Optional[ctk.CTkLabel] = None
        self._label_camara: Optional[ctk.CTkLabel] = None
        self._frame_camara: Optional[ctk.CTkFrame] = None
        self._frame_items_historial: Optional[ctk.CTkFrame] = None
        self._fuente_frame: Optional[Callable] = None
        self._historial = HistorialAlertas()
        self._total_alertas = self._historial.total()
        self._ultimo_total_mostrado = -1
        self._sesion_inicio = time.time()
        self._estado_actual = EstadoAlerta.CALIBRANDO

    def registrar_fuente_frame(self, cb: Callable) -> None:
        self._fuente_frame = cb

    def registrar_callback_cierre(self, cb: Callable) -> None:
        self._al_cerrar_callback = cb

    def construir_ventana_principal(self) -> ctk.CTk:
        ctk.set_appearance_mode("dark")
        self._ventana = ctk.CTk()
        self._ventana.title("SafeWork AI")
        self._ventana.geometry("340x640")
        self._ventana.minsize(320, 580)
        self._ventana.configure(fg_color=PALETA["fondo_oscuro"])
        self._al_cerrar_callback = None
        
        def _cerrar():
            if self._al_cerrar_callback:
                self._al_cerrar_callback()
            else:
                self._ventana.destroy()
                
        self._ventana.protocol("WM_DELETE_WINDOW", _cerrar)

        self._scroll = ctk.CTkScrollableFrame(
            self._ventana, fg_color=PALETA["fondo_oscuro"],
            scrollbar_fg_color=PALETA["fondo_panel"],
            scrollbar_button_color=PALETA["borde_card"],
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

        self._construir_header()
        self._construir_panel_camara()
        self._construir_metricas()
        self._construir_estado()
        self._construir_historial_panel()
        self._construir_footer()
        self._ventana.after(100, self._loop)
        return self._ventana

    def _construir_header(self) -> None:
        f = ctk.CTkFrame(self._scroll, fg_color=PALETA["fondo_panel"], corner_radius=12)
        f.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(f, text="⬡  SAFEWORK AI", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"), text_color=PALETA["acento_primario"]).pack(anchor="w", padx=20, pady=(14, 2))
        ctk.CTkLabel(f, text="Softech Perú  ·  Híbrido (Sueño y Postura)", font=ctk.CTkFont(size=11), text_color=PALETA["texto_secundario"]).pack(anchor="w", padx=20, pady=(0, 14))

    def _construir_panel_camara(self) -> None:
        outer = ctk.CTkFrame(self._scroll, fg_color=PALETA["fondo_card"], corner_radius=12, border_width=1, border_color=PALETA["borde_card"])
        outer.pack(fill="x", pady=4)
        ctk.CTkLabel(outer, text="MONITOR EN TIEMPO REAL", font=ctk.CTkFont(family="Consolas", size=8, weight="bold"), text_color=PALETA["texto_tenue"]).pack(pady=(10, 4))
        self._frame_camara = ctk.CTkFrame(outer, fg_color=PALETA["acento_primario"], corner_radius=8)
        self._frame_camara.pack(fill="x", padx=6, pady=(0, 10))
        self._label_camara = ctk.CTkLabel(self._frame_camara, text="Iniciando cámara...", fg_color=PALETA["fondo_oscuro"], corner_radius=7, text_color=PALETA["texto_tenue"])
        self._label_camara.pack(fill="both", expand=True, padx=1, pady=1)

    def _construir_metricas(self) -> None:
        fg = ctk.CTkFrame(self._scroll, fg_color="transparent")
        fg.pack(fill="x", pady=4)
        fg.columnconfigure(0, weight=1)
        fg.columnconfigure(1, weight=1)
        self._label_sesion = self._card(fg, "SESIÓN", "00:00:00", 0, 0)
        self._label_contador = self._card(fg, "ALERTAS EVENTOS", str(self._total_alertas), 0, 1)

    def _card(self, p, titulo, valor, fila, col) -> ctk.CTkLabel:
        c = ctk.CTkFrame(p, fg_color=PALETA["fondo_card"], corner_radius=12, border_width=1, border_color=PALETA["borde_card"])
        c.grid(row=fila, column=col, padx=(0, 4) if col == 0 else (4, 0), pady=4, sticky="nsew")
        ctk.CTkLabel(c, text=titulo, font=ctk.CTkFont(family="Consolas", size=8, weight="bold"), text_color=PALETA["texto_tenue"]).pack(pady=(10, 2))
        lv = ctk.CTkLabel(c, text=valor, font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color=PALETA["texto_primario"])
        lv.pack(pady=(0, 10))
        return lv

    def _construir_estado(self) -> None:
        f = ctk.CTkFrame(self._scroll, fg_color=PALETA["fondo_card"], corner_radius=16, border_width=1, border_color=PALETA["borde_card"])
        f.pack(fill="x", pady=4)
        ctk.CTkLabel(f, text="ESTADO DE RIESGO", font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color=PALETA["texto_tenue"]).pack(pady=(12, 6))
        self._label_estado = ctk.CTkLabel(f, text="◌ CALIBRANDO...", font=ctk.CTkFont(size=16, weight="bold"), text_color=PALETA["acento_primario"])
        self._label_estado.pack(pady=(0, 4))
        self._label_desc = ctk.CTkLabel(f, text="Analizando base...", font=ctk.CTkFont(size=11), text_color=PALETA["texto_secundario"], wraplength=360)
        self._label_desc.pack(pady=(0, 12))

    def _construir_historial_panel(self) -> None:
        outer = ctk.CTkFrame(self._scroll, fg_color=PALETA["fondo_card"], corner_radius=16, border_width=1, border_color=PALETA["borde_card"])
        outer.pack(fill="x", pady=4)

        header_row = ctk.CTkFrame(outer, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(header_row, text="HISTORIAL DE RIESGOS", font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color=PALETA["texto_tenue"]).pack(side="left")
        ctk.CTkButton(
            header_row, text="📂 Abrir carpeta", width=110, height=22,
            font=ctk.CTkFont(size=10), fg_color=PALETA["fondo_panel"],
            hover_color=PALETA["borde_card"], text_color=PALETA["texto_secundario"],
            corner_radius=6, command=self._abrir_carpeta_datos,
        ).pack(side="right")

        self._frame_items_historial = ctk.CTkFrame(outer, fg_color="transparent")
        self._frame_items_historial.pack(fill="x", padx=10, pady=(0, 12))

    def _refrescar_historial_panel(self) -> None:
        if not self._frame_items_historial: return
        for w in self._frame_items_historial.winfo_children(): w.destroy()

        entradas = self._historial.ultimas(8)
        if not entradas:
            ctk.CTkLabel(self._frame_items_historial, text="Sin alertas registradas aún.", font=ctk.CTkFont(size=11), text_color=PALETA["texto_tenue"]).pack(pady=6)
            return

        for entrada in entradas:
            tipo = entrada.get("tipo", "")
            icono, color = "◆", PALETA["estado_critico"]
            if "ADVERTENCIA" in tipo:
                icono, color = "⚠", PALETA["estado_advertencia"]
            desc = tipo

            fila = ctk.CTkFrame(self._frame_items_historial, fg_color=PALETA["fondo_panel"], corner_radius=8)
            fila.pack(fill="x", pady=2)

            ctk.CTkLabel(fila, text=icono, font=ctk.CTkFont(size=13), text_color=color, width=28).pack(side="left", padx=(8, 2), pady=6)
            ctk.CTkLabel(fila, text=desc, font=ctk.CTkFont(size=10), text_color=PALETA["texto_primario"]).pack(side="left", padx=4)
            hora = f"{entrada.get('fecha', '')}  {entrada.get('hora', '')}"
            ctk.CTkLabel(fila, text=hora, font=ctk.CTkFont(family="Consolas", size=9), text_color=PALETA["texto_tenue"]).pack(side="right", padx=10)

    def _abrir_carpeta_datos(self) -> None:
        try: subprocess.Popen(f'explorer "{CARPETA_DATOS}"')
        except: pass

    def _construir_footer(self) -> None:
        f = ctk.CTkFrame(self._scroll, fg_color="transparent")
        f.pack(fill="x", pady=(4, 16))
        ctk.CTkLabel(f, text="Softech Perú · SafeWork AI v2.0 · Híbrido", font=ctk.CTkFont(size=9), text_color=PALETA["texto_tenue"]).pack()

    def _loop(self) -> None:
        if not self._ventana: return
        try:
            self._refrescar()
            self._camara()
            if self._total_alertas != self._ultimo_total_mostrado:
                self._refrescar_historial_panel()
                self._ultimo_total_mostrado = self._total_alertas
        except: pass
        self._ventana.after(50, self._loop)

    def _camara(self) -> None:
        if not self._fuente_frame or not self._label_camara or not self._frame_camara: return
        frame = self._fuente_frame()
        if frame is None: return
        try:
            w = max(100, self._frame_camara.winfo_width() - 4)
            h = int(w * 9 / 16)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2.resize(rgb, (w, h)))
            ci = ctk.CTkImage(img, img, (w, h))
            self._label_camara.configure(image=ci, text="")
            self._label_camara._current_image = ci
        except: pass

    def _refrescar(self) -> None:
        s = int(time.time() - self._sesion_inicio)
        if self._label_sesion:
            self._label_sesion.configure(text=f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}")
        if self._label_contador:
            self._label_contador.configure(text=str(self._total_alertas))
        
        color, icono, desc = self._datos_estado()
        if self._label_estado:
            self._label_estado.configure(text=f"{icono}  {self._estado_actual.value}", text_color=color)
        if self._label_desc:
            self._label_desc.configure(text=desc)

    def _datos_estado(self) -> tuple:
        return {
            EstadoAlerta.OPTIMO:      (PALETA["estado_optimo"],     "◉", "Usuario atento y con buena postura."),
            EstadoAlerta.ADVERTENCIA_SUEÑO: (PALETA["estado_advertencia"], "⚠", "Bostezos detectados. Falta de oxigenación."),
            EstadoAlerta.FATIGA_EXTREMA: (PALETA["estado_critico"], "◆", "Peligro: Ojos cerrados. Microsueño inminente."),
            EstadoAlerta.CABECEO:     (PALETA["estado_critico"],     "◆", "Peligro: Cabeceo por sueño detectado."),
            EstadoAlerta.MALA_POSTURA: (PALETA["estado_critico"], "◆", "Peligro: Riesgo ergonómico y mala postura."),
            EstadoAlerta.CALIBRANDO:  (PALETA["acento_primario"],    "◌", "Calibrando sensores de sueño y postura..."),
            EstadoAlerta.AUSENTE:     (PALETA["texto_tenue"],        "✕", "Usuario no detectado en cámara."),
        }.get(self._estado_actual, (PALETA["acento_primario"], "◌", ""))

    def actualizar_estado_visual(self, estado: EstadoFisico) -> None:
        if estado.estado == EstadoAlerta.MALA_POSTURA and self._estado_actual != EstadoAlerta.MALA_POSTURA:
            _hablar("Atención. Llevas tiempo en mala postura. Por favor, corrige tu espalda.")
        self._estado_actual = estado.estado

    def emitir_alerta_bloqueante(self, estado: EstadoFisico) -> None:
        with self._lock:
            if self._mostrando_alerta: return
            self._mostrando_alerta = True
        
        self._historial.registrar(
            estado.estado.value, 
            f"EAR:{estado.ear:.2f} MAR:{estado.mar:.2f} Cuello:{estado.angulo_cuello:.1f}° Lat:{estado.angulo_lateral:.1f}°"
        )
        self._total_alertas = self._historial.total()
        
        mensaje_voz = "Atención. Por favor, toma un descanso."
        if estado.estado == EstadoAlerta.FATIGA_EXTREMA:
            mensaje_voz = "Atención, se detectaron ojos cerrados prolongadamente. Por favor descansa."
        elif estado.estado == EstadoAlerta.CABECEO:
            mensaje_voz = "Atención, se detectó un cabeceo. Toma una pausa."
        elif estado.estado == EstadoAlerta.MALA_POSTURA:
            mensaje_voz = "Atención, mejora tu postura."
            
        _hablar(mensaje_voz)
        
        if self._ventana:
            self._ventana.after(10000, self._desbloquear_alerta)

    def _desbloquear_alerta(self) -> None:
        with self._lock:
            self._mostrando_alerta = False

    def esta_mostrando_alerta(self) -> bool:
        return self._mostrando_alerta
