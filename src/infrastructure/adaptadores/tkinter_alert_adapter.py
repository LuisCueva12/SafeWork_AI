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
        self._voz_habilitada = True

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
        ctk.CTkLabel(f, text="Softech Perú  ·  v1.0.0  ·  Híbrido", font=ctk.CTkFont(size=11), text_color=PALETA["texto_secundario"]).pack(anchor="w", padx=20, pady=(0, 6))
        
        def toggle_voz():
            self._voz_habilitada = bool(self._switch_voz.get())
            if self._voz_habilitada:
                _hablar("Asistente de voz activado")
            else:
                _hablar("Asistente de voz desactivado")

        self._switch_voz = ctk.CTkSwitch(
            f, text="Asistente de Voz", 
            command=toggle_voz,
            font=ctk.CTkFont(size=10),
            progress_color=PALETA["acento_primario"],
            text_color=PALETA["texto_secundario"]
        )
        self._switch_voz.select()
        self._switch_voz.pack(anchor="w", padx=20, pady=(0, 14))

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
        ctk.CTkLabel(f, text="Softech Perú · SafeWork AI v1.0.0 · Híbrido", font=ctk.CTkFont(size=9), text_color=PALETA["texto_tenue"]).pack()

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
        if estado.estado == EstadoAlerta.CALIBRANDO and self._estado_actual != EstadoAlerta.CALIBRANDO:
            if self._voz_habilitada:
                _hablar("Iniciando calibración de sensores. Por favor, siéntate erguido y mira hacia la pantalla.")
        elif self._estado_actual == EstadoAlerta.CALIBRANDO and estado.estado != EstadoAlerta.CALIBRANDO:
            if self._voz_habilitada:
                _hablar("Calibración completada con éxito. SafeWork está monitoreando en segundo plano.")
        
        if estado.estado == EstadoAlerta.MALA_POSTURA and self._estado_actual != EstadoAlerta.MALA_POSTURA:
            if self._voz_habilitada:
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
        
        if self._ventana:
            self._ventana.after(0, lambda: self._mostrar_ventana_pausa_activa(estado))

    def _mostrar_ventana_pausa_activa(self, estado: EstadoFisico) -> None:
        self._alerta_win = ctk.CTkToplevel(self._ventana)
        self._alerta_win.title("Pausa Activa - SafeWork AI")
        self._alerta_win.geometry("450x420")
        self._alerta_win.configure(fg_color=PALETA["fondo_oscuro"])
        self._alerta_win.resizable(False, False)
        self._alerta_win.attributes("-topmost", True)
        self._alerta_win.protocol("WM_DELETE_WINDOW", self._cerrar_pausa_activa)
        
        try:
            screen_w = self._alerta_win.winfo_screenwidth()
            screen_h = self._alerta_win.winfo_screenheight()
            x = (screen_w - 450) // 2
            y = (screen_h - 420) // 2
            self._alerta_win.geometry(f"450x420+{x}+{y}")
        except:
            pass

        es_postura = estado.estado == EstadoAlerta.MALA_POSTURA
        
        if es_postura:
            tipo_alerta = "ALERTA ERGONÓMICA"
            color_alerta = PALETA["estado_critico"]
            titulo_ejercicio = "Rutina: Estiramiento de Cuello y Hombros"
            pasos = [
                ("1. Rotación de Hombros", "Gira los hombros hacia atrás lentamente para liberar tensión.", "Iniciemos la pausa. Paso uno: Gira los hombros hacia atrás lentamente."),
                ("2. Alineación Cervical", "Lleva tu cabeza con la barbilla hacia atrás manteniéndola erguida.", "Paso dos: Alineación cervical. Lleva la barbilla hacia atrás, manteniendo la mirada al frente."),
                ("3. Inclinación Lateral", "Lleva la oreja derecha al hombro derecho, luego la izquierda.", "Paso tres: Inclinación lateral. Lleva la oreja hacia el hombro derecho y luego hacia el izquierdo."),
                ("4. Estiramiento Lumbar", "Apoya bien la espalda y estira ambos brazos hacia el frente.", "Paso cuatro: Estiramiento lumbar. Estira los brazos al frente y entrelaza tus dedos.")
            ]
        else:
            tipo_alerta = "ALERTA DE FATIGA Y SUEÑO"
            color_alerta = PALETA["estado_critico"]
            titulo_ejercicio = "Rutina: Relajación Ocular y Enfoque"
            pasos = [
                ("1. Regla 20-20-20", "Mira un objeto lejano a 6 metros de distancia durante 5 segundos.", "Iniciemos la pausa visual. Paso uno: Enfoca un punto lejano a seis metros."),
                ("2. Parpadeo Consciente", "Parpadea suave y profundamente 10 veces para lubricar los ojos.", "Paso dos: Parpadeo consciente. Parpadea suavemente para rehumectar tus ojos."),
                ("3. Respiración Profunda", "Inhala profundo por la nariz y exhala el aire despacio.", "Paso tres: Oxigenación. Inhala profundo por la nariz y exhala despacio."),
                ("4. Estiramiento Cervical", "Gira la cabeza realizando círculos suaves hacia cada lado.", "Paso cuatro: Estiramiento cervical. Gira suavemente la cabeza en círculos.")
            ]

        header = ctk.CTkFrame(self._alerta_win, fg_color=PALETA["fondo_panel"], corner_radius=12)
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header, 
            text=f"🚨  {tipo_alerta}", 
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), 
            text_color=color_alerta
        ).pack(anchor="w", padx=15, pady=(10, 2))
        
        ctk.CTkLabel(
            header, 
            text="Tómate un breve descanso para prevenir dolores físicos y fatiga.", 
            font=ctk.CTkFont(size=11), 
            text_color=PALETA["texto_secundario"]
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ex_panel = ctk.CTkFrame(self._alerta_win, fg_color=PALETA["fondo_card"], corner_radius=12, border_width=1, border_color=PALETA["borde_card"])
        ex_panel.pack(fill="both", expand=True, padx=20, pady=10)
        
        lbl_titulo_rutina = ctk.CTkLabel(
            ex_panel, 
            text=titulo_ejercicio, 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color=PALETA["acento_primario"]
        )
        lbl_titulo_rutina.pack(anchor="w", padx=20, pady=(12, 2))

        lbl_paso_num = ctk.CTkLabel(
            ex_panel, 
            text="", 
            font=ctk.CTkFont(family="Consolas", size=10), 
            text_color=PALETA["texto_secundario"]
        )
        lbl_paso_num.pack(anchor="w", padx=20, pady=2)

        lbl_paso_titulo = ctk.CTkLabel(
            ex_panel, 
            text="", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=PALETA["texto_primario"]
        )
        lbl_paso_titulo.pack(anchor="w", padx=20, pady=(4, 2))

        lbl_paso_desc = ctk.CTkLabel(
            ex_panel, 
            text="", 
            font=ctk.CTkFont(size=11), 
            text_color=PALETA["texto_tenue"],
            justify="left",
            wraplength=380,
            anchor="w"
        )
        lbl_paso_desc.pack(anchor="w", padx=20, pady=(2, 12))

        self._segundos_restantes = 20
        self._ultimo_indice_hablado = -1

        progress = ctk.CTkProgressBar(self._alerta_win, width=410, progress_color=PALETA["acento_primario"], fg_color=PALETA["fondo_panel"])
        progress.pack(pady=(15, 2))
        progress.set(1.0)

        label_timer = ctk.CTkLabel(
            self._alerta_win, 
            text="Tiempo recomendado: 20s", 
            font=ctk.CTkFont(family="Consolas", size=11), 
            text_color=PALETA["texto_secundario"]
        )
        label_timer.pack(pady=2)

        btn_panel = ctk.CTkFrame(self._alerta_win, fg_color="transparent")
        btn_panel.pack(fill="x", padx=20, pady=(10, 20))
        
        btn_saltar = ctk.CTkButton(
            btn_panel, 
            text="Saltar Pausa", 
            width=140,
            fg_color=PALETA["fondo_panel"], 
            hover_color=PALETA["borde_card"], 
            text_color=PALETA["texto_secundario"], 
            command=self._cerrar_pausa_activa
        )
        btn_saltar.pack(side="left")
        
        btn_completar = ctk.CTkButton(
            btn_panel, 
            text="Completar (20s)", 
            width=250,
            state="disabled", 
            fg_color=PALETA["fondo_panel"], 
            text_color=PALETA["texto_tenue"], 
            command=self._completar_pausa_activa
        )
        btn_completar.pack(side="right")

        def actualizar_timer():
            if not self._alerta_win or not self._alerta_win.winfo_exists():
                return
            
            indice_paso = (20 - self._segundos_restantes) // 5
            indice_paso = min(max(0, indice_paso), 3)

            nombre, desc, voz_instruccion = pasos[indice_paso]

            try:
                lbl_paso_num.configure(text=f"Paso {indice_paso + 1} de 4")
                lbl_paso_titulo.configure(text=nombre)
                lbl_paso_desc.configure(text=desc)
            except:
                pass

            if self._voz_habilitada and (indice_paso != self._ultimo_indice_hablado):
                self._ultimo_indice_hablado = indice_paso
                _hablar(voz_instruccion)

            self._segundos_restantes -= 1

            if self._segundos_restantes >= 0:
                try:
                    label_timer.configure(text=f"Tiempo recomendado: {self._segundos_restantes}s")
                    progress.set(self._segundos_restantes / 20.0)
                    btn_completar.configure(text=f"Completar ({self._segundos_restantes}s)")
                except:
                    pass
                self._alerta_win.after(1000, actualizar_timer)
            else:
                try:
                    label_timer.configure(text="¡Pausa de estiramiento recomendada completada!", text_color=PALETA["estado_optimo"])
                    progress.set(0.0)
                    btn_completar.configure(
                        text="¡Completar!", 
                        state="normal", 
                        fg_color=PALETA["estado_optimo"], 
                        hover_color="#0D9488", 
                        text_color="#FFFFFF"
                    )
                except:
                    pass
                if self._voz_habilitada:
                    _hablar("Pausa completada. Excelente trabajo. Puedes continuar con tus actividades.")
                
        self._alerta_win.after(10, actualizar_timer)

    def _cerrar_pausa_activa(self) -> None:
        if self._alerta_win:
            try:
                self._alerta_win.destroy()
            except:
                pass
            self._alerta_win = None
        with self._lock:
            self._mostrando_alerta = False

    def _completar_pausa_activa(self) -> None:
        self._cerrar_pausa_activa()

    def esta_mostrando_alerta(self) -> bool:
        return self._mostrando_alerta
