"""
Adaptador de Salida (Driven Adapter): TkinterAlertAdapter.
Única clase que conoce CustomTkinter.

FEATURE: Panel de cámara con preview en tiempo real del skeleton detectado.
"""
from __future__ import annotations
from typing import Optional, Callable
import threading
import time
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import numpy as np

from ...domain.puertos.puerto_emision_alertas import PuertoEmisionAlertas
from ...domain.entities.postura import Postura, EstadoPostural


DURACION_PAUSA_ACTIVA_SEGUNDOS = 60

# Tamaño del preview de cámara dentro de la UI
PREVIEW_ANCHO = 380
PREVIEW_ALTO  = 214

PALETA = {
    "fondo_oscuro":       "#0A0E1A",
    "fondo_panel":        "#111827",
    "fondo_card":         "#1C2333",
    "borde_card":         "#2D3748",
    "acento_primario":    "#00D4FF",
    "acento_secundario":  "#7C3AED",
    "estado_optimo":      "#10B981",
    "estado_advertencia": "#F59E0B",
    "estado_critico":     "#EF4444",
    "texto_primario":     "#F1F5F9",
    "texto_secundario":   "#94A3B8",
    "texto_tenue":        "#475569",
}


class TkinterAlertAdapter(PuertoEmisionAlertas):

    def __init__(self) -> None:
        self._ventana_principal: Optional[ctk.CTk] = None
        self._ventana_alerta: Optional[ctk.CTkToplevel] = None
        self._mostrando_alerta = False
        self._lock = threading.Lock()

        # Widgets de métricas
        self._label_angulo: Optional[ctk.CTkLabel] = None
        self._label_estado: Optional[ctk.CTkLabel] = None
        self._label_descripcion_estado: Optional[ctk.CTkLabel] = None
        self._label_sesion: Optional[ctk.CTkLabel] = None
        self._label_alerta_contador: Optional[ctk.CTkLabel] = None
        self._barra_progreso: Optional[ctk.CTkProgressBar] = None

        # Widget de preview de cámara
        self._label_camara: Optional[ctk.CTkLabel] = None
        self._imagen_placeholder: Optional[ctk.CTkImage] = None
        self._fuente_frame_anotado: Optional[Callable] = None

        # Estado interno
        self._sesion_inicio = time.time()
        self._angulo_actual = 0.0
        self._estado_actual = EstadoPostural.CALIBRANDO

    def registrar_fuente_frame(self, callback: Callable) -> None:
        """Inyecta el callback que provee el frame anotado de la cámara."""
        self._fuente_frame_anotado = callback

    # -------------------------------------------------------------------------
    # Construcción de la ventana principal
    # -------------------------------------------------------------------------

    def construir_ventana_principal(self) -> ctk.CTk:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._ventana_principal = ctk.CTk()
        self._ventana_principal.title("SafeWork AI — Softech Perú")
        self._ventana_principal.geometry("420x780")
        self._ventana_principal.resizable(False, False)
        self._ventana_principal.configure(fg_color=PALETA["fondo_oscuro"])
        self._ventana_principal.protocol("WM_DELETE_WINDOW", self._minimizar_al_tray)

        self._construir_header()
        self._construir_panel_camara()
        self._construir_indicador_angular()
        self._construir_panel_metricas()
        self._construir_panel_estado()
        self._construir_footer()

        self._ventana_principal.after(100, self._actualizar_ui_loop)

        return self._ventana_principal

    def _construir_header(self) -> None:
        frame_header = ctk.CTkFrame(
            self._ventana_principal,
            fg_color=PALETA["fondo_panel"],
            corner_radius=0,
            height=72,
        )
        frame_header.pack(fill="x", padx=0, pady=0)
        frame_header.pack_propagate(False)

        frame_interno = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_interno.pack(expand=True, fill="both", padx=20, pady=10)

        ctk.CTkLabel(
            frame_interno,
            text="⬡  SAFEWORK AI",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=PALETA["acento_primario"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame_interno,
            text="Monitor de Ergonomía Postural · Softech Perú",
            font=ctk.CTkFont(size=11),
            text_color=PALETA["texto_secundario"],
        ).pack(anchor="w")

    def _construir_panel_camara(self) -> None:
        frame_camara = ctk.CTkFrame(
            self._ventana_principal,
            fg_color=PALETA["fondo_card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETA["borde_card"],
        )
        frame_camara.pack(fill="x", padx=20, pady=(12, 4))

        ctk.CTkLabel(
            frame_camara,
            text="VISIÓN COMPUTACIONAL EN TIEMPO REAL",
            font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(10, 4))

        # Frame de imagen con borde cyan
        frame_borde = ctk.CTkFrame(
            frame_camara,
            fg_color=PALETA["acento_primario"],
            corner_radius=8,
            width=PREVIEW_ANCHO + 2,
            height=PREVIEW_ALTO + 2,
        )
        frame_borde.pack(pady=(0, 10))
        frame_borde.pack_propagate(False)

        # Imagen placeholder inicial (fondo oscuro con mensaje)
        placeholder_np = self._crear_frame_placeholder()
        placeholder_pil = Image.fromarray(cv2.cvtColor(placeholder_np, cv2.COLOR_BGR2RGB))
        self._imagen_placeholder = ctk.CTkImage(
            light_image=placeholder_pil,
            dark_image=placeholder_pil,
            size=(PREVIEW_ANCHO, PREVIEW_ALTO),
        )

        self._label_camara = ctk.CTkLabel(
            frame_borde,
            image=self._imagen_placeholder,
            text="",
            fg_color=PALETA["fondo_oscuro"],
            corner_radius=7,
        )
        self._label_camara.pack(fill="both", expand=True, padx=1, pady=1)

    def _crear_frame_placeholder(self) -> np.ndarray:
        canvas = np.full((PREVIEW_ALTO, PREVIEW_ANCHO, 3), (26, 14, 10), dtype=np.uint8)
        cv2.putText(
            canvas,
            "Iniciando camara...",
            (PREVIEW_ANCHO // 2 - 90, PREVIEW_ALTO // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (80, 80, 80),
            1,
            cv2.LINE_AA,
        )
        return canvas

    def _construir_indicador_angular(self) -> None:
        frame_angulo = ctk.CTkFrame(
            self._ventana_principal,
            fg_color=PALETA["fondo_card"],
            corner_radius=16,
        )
        frame_angulo.pack(fill="x", padx=20, pady=(8, 4))

        ctk.CTkLabel(
            frame_angulo,
            text="ÁNGULO DE INCLINACIÓN CERVICAL",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(12, 2))

        self._label_angulo = ctk.CTkLabel(
            frame_angulo,
            text="0.0°",
            font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color=PALETA["acento_primario"],
        )
        self._label_angulo.pack(pady=2)

        self._barra_progreso = ctk.CTkProgressBar(
            frame_angulo,
            width=340,
            height=6,
            corner_radius=3,
            fg_color=PALETA["borde_card"],
            progress_color=PALETA["estado_optimo"],
        )
        self._barra_progreso.set(0)
        self._barra_progreso.pack(pady=(2, 12))

    def _construir_panel_metricas(self) -> None:
        frame_grid = ctk.CTkFrame(
            self._ventana_principal,
            fg_color="transparent",
        )
        frame_grid.pack(fill="x", padx=20, pady=4)
        frame_grid.columnconfigure(0, weight=1)
        frame_grid.columnconfigure(1, weight=1)

        self._label_sesion = self._crear_card_metrica(
            frame_grid, "DURACIÓN SESIÓN", "00:00:00", 0, 0
        )
        self._label_alerta_contador = self._crear_card_metrica(
            frame_grid, "ALERTAS EMITIDAS", "0", 0, 1
        )

    def _crear_card_metrica(
        self,
        parent: ctk.CTkFrame,
        titulo: str,
        valor_inicial: str,
        fila: int,
        columna: int,
    ) -> ctk.CTkLabel:
        card = ctk.CTkFrame(
            parent,
            fg_color=PALETA["fondo_card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETA["borde_card"],
        )
        pad_x = (0, 6) if columna == 0 else (6, 0)
        card.grid(row=fila, column=columna, padx=pad_x, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(10, 2))

        label_valor = ctk.CTkLabel(
            card,
            text=valor_inicial,
            font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
            text_color=PALETA["texto_primario"],
        )
        label_valor.pack(pady=(0, 10))

        return label_valor

    def _construir_panel_estado(self) -> None:
        frame_estado = ctk.CTkFrame(
            self._ventana_principal,
            fg_color=PALETA["fondo_card"],
            corner_radius=16,
            border_width=1,
            border_color=PALETA["borde_card"],
        )
        frame_estado.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(
            frame_estado,
            text="ESTADO POSTURAL ACTUAL",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(12, 6))

        self._label_estado = ctk.CTkLabel(
            frame_estado,
            text="◌  CALIBRANDO...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=PALETA["acento_primario"],
        )
        self._label_estado.pack(pady=(0, 4))

        self._label_descripcion_estado = ctk.CTkLabel(
            frame_estado,
            text="Analizando postura base. Por favor, siéntese normalmente.",
            font=ctk.CTkFont(size=11),
            text_color=PALETA["texto_secundario"],
            wraplength=340,
        )
        self._label_descripcion_estado.pack(pady=(0, 12))

    def _construir_footer(self) -> None:
        frame_footer = ctk.CTkFrame(
            self._ventana_principal,
            fg_color="transparent",
        )
        frame_footer.pack(fill="x", padx=20, pady=(4, 16))

        ctk.CTkLabel(
            frame_footer,
            text="Disparadores: Inclinación >15° por 3min  ·  Inactividad >45min",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=PALETA["texto_tenue"],
        ).pack()

        ctk.CTkLabel(
            frame_footer,
            text="ODS 8 · ODS 9 · Procesamiento 100% Local · v1.0",
            font=ctk.CTkFont(size=9),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(2, 0))

    # -------------------------------------------------------------------------
    # Loop de actualización de UI
    # -------------------------------------------------------------------------

    def _actualizar_ui_loop(self) -> None:
        if self._ventana_principal:
            try:
                self._refrescar_metricas_visuales()
                self._actualizar_preview_camara()
            except Exception:
                pass
            # Métricas cada 500ms, cámara se actualiza en su propio paso
            self._ventana_principal.after(100, self._actualizar_ui_loop)

    def _actualizar_preview_camara(self) -> None:
        if not self._fuente_frame_anotado or not self._label_camara:
            return

        frame_bgr = self._fuente_frame_anotado()
        if frame_bgr is None:
            return

        try:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            # Redimensionar al tamaño del panel
            frame_resized = cv2.resize(frame_rgb, (PREVIEW_ANCHO, PREVIEW_ALTO))
            pil_img = Image.fromarray(frame_resized)
            ctk_img = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(PREVIEW_ANCHO, PREVIEW_ALTO),
            )
            self._label_camara.configure(image=ctk_img)
            # Mantener referencia para evitar garbage collection
            self._label_camara._current_image = ctk_img
        except Exception:
            pass

    def _refrescar_metricas_visuales(self) -> None:
        segundos_sesion = int(time.time() - self._sesion_inicio)
        horas    = segundos_sesion // 3600
        minutos  = (segundos_sesion % 3600) // 60
        segundos = segundos_sesion % 60

        if self._label_sesion:
            self._label_sesion.configure(
                text=f"{horas:02d}:{minutos:02d}:{segundos:02d}"
            )

        if self._label_angulo:
            self._label_angulo.configure(text=f"{self._angulo_actual:.1f}°")

        progreso = min(self._angulo_actual / 30.0, 1.0)
        if self._barra_progreso:
            self._barra_progreso.set(progreso)

        color_estado, icono, descripcion = self._obtener_datos_visuales_estado()

        if self._label_estado:
            self._label_estado.configure(
                text=f"{icono}  {self._estado_actual.value}",
                text_color=color_estado,
            )

        if self._label_descripcion_estado:
            self._label_descripcion_estado.configure(text=descripcion)

        if self._barra_progreso:
            self._barra_progreso.configure(progress_color=color_estado)

    def _obtener_datos_visuales_estado(self) -> tuple:
        mapa = {
            EstadoPostural.OPTIMO: (
                PALETA["estado_optimo"],
                "◉",
                "Postura correcta. ¡Excelente ergonomía!",
            ),
            EstadoPostural.ADVERTENCIA: (
                PALETA["estado_advertencia"],
                "◈",
                f"Inclinación detectada ({self._angulo_actual:.1f}°). Corrija su postura.",
            ),
            EstadoPostural.CRITICO: (
                PALETA["estado_critico"],
                "◆",
                "Desviación postural crítica. Se requiere pausa activa.",
            ),
            EstadoPostural.CALIBRANDO: (
                PALETA["acento_primario"],
                "◌",
                "Calibrando postura base. Siéntese normalmente.",
            ),
        }
        return mapa.get(self._estado_actual, mapa[EstadoPostural.OPTIMO])

    def _minimizar_al_tray(self) -> None:
        if self._ventana_principal:
            self._ventana_principal.withdraw()

    # -------------------------------------------------------------------------
    # Implementación de PuertoEmisionAlertas
    # -------------------------------------------------------------------------

    def actualizar_estado_visual(self, postura: Postura) -> None:
        self._angulo_actual = postura.angulo_inclinacion_cuello
        self._estado_actual = postura.estado

    def emitir_alerta_postura_critica(self, postura: Postura) -> None:
        with self._lock:
            if self._mostrando_alerta:
                return
            self._mostrando_alerta = True

        angulo = postura.angulo_inclinacion_cuello
        if self._ventana_principal:
            self._ventana_principal.after(
                0,
                lambda: self._renderizar_alerta_postura("POSTURA CRÍTICA DETECTADA", angulo),
            )

    def emitir_alerta_inactividad(self, minutos_inactivo: float) -> None:
        with self._lock:
            if self._mostrando_alerta:
                return
            self._mostrando_alerta = True

        if self._ventana_principal:
            self._ventana_principal.after(
                0,
                lambda: self._renderizar_alerta_inactividad(minutos_inactivo),
            )

    def esta_mostrando_alerta(self) -> bool:
        return self._mostrando_alerta

    # -------------------------------------------------------------------------
    # Ventanas de alerta
    # -------------------------------------------------------------------------

    def _renderizar_alerta_postura(self, titulo: str, angulo: float) -> None:
        alerta = self._crear_ventana_alerta_base()

        ctk.CTkLabel(
            alerta,
            text="⚠",
            font=ctk.CTkFont(size=56),
            text_color=PALETA["estado_critico"],
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            alerta,
            text=titulo,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=PALETA["texto_primario"],
        ).pack(pady=4)

        ctk.CTkLabel(
            alerta,
            text=f"Inclinación cervical de {angulo:.1f}° detectada\npor más de 3 minutos continuos.",
            font=ctk.CTkFont(size=12),
            text_color=PALETA["texto_secundario"],
            justify="center",
        ).pack(pady=6)

        self._construir_temporizador_pausa(alerta)

    def _renderizar_alerta_inactividad(self, minutos: float) -> None:
        alerta = self._crear_ventana_alerta_base()

        ctk.CTkLabel(
            alerta,
            text="⏸",
            font=ctk.CTkFont(size=56),
            text_color=PALETA["estado_advertencia"],
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            alerta,
            text="PAUSA ACTIVA REQUERIDA",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=PALETA["texto_primario"],
        ).pack(pady=4)

        ctk.CTkLabel(
            alerta,
            text=f"Llevas {minutos:.0f} minutos sin movimiento.\nEs momento de descansar.",
            font=ctk.CTkFont(size=12),
            text_color=PALETA["texto_secundario"],
            justify="center",
        ).pack(pady=6)

        self._construir_temporizador_pausa(alerta)

    def _crear_ventana_alerta_base(self) -> ctk.CTkToplevel:
        if self._ventana_alerta is not None:
            try:
                if self._ventana_alerta.winfo_exists():
                    self._ventana_alerta.destroy()
            except Exception:
                pass

        alerta = ctk.CTkToplevel(self._ventana_principal)
        alerta.title("SafeWork AI — Pausa Activa")
        alerta.configure(fg_color=PALETA["fondo_oscuro"])
        alerta.attributes("-topmost", True)
        alerta.resizable(False, False)

        ancho, alto = 500, 440
        sw = alerta.winfo_screenwidth()
        sh = alerta.winfo_screenheight()
        x = (sw - ancho) // 2
        y = (sh - alto) // 2
        alerta.geometry(f"{ancho}x{alto}+{x}+{y}")

        self._ventana_alerta = alerta
        return alerta

    def _construir_temporizador_pausa(self, alerta: ctk.CTkToplevel) -> None:
        ctk.CTkLabel(
            alerta,
            text="PAUSA ACTIVA — TIEMPO RESTANTE",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=PALETA["texto_tenue"],
        ).pack(pady=(10, 2))

        label_tiempo = ctk.CTkLabel(
            alerta,
            text=f"{DURACION_PAUSA_ACTIVA_SEGUNDOS}s",
            font=ctk.CTkFont(family="Consolas", size=40, weight="bold"),
            text_color=PALETA["acento_primario"],
        )
        label_tiempo.pack()

        barra_pausa = ctk.CTkProgressBar(
            alerta,
            width=380,
            height=8,
            corner_radius=4,
            fg_color=PALETA["borde_card"],
            progress_color=PALETA["acento_primario"],
        )
        barra_pausa.set(1.0)
        barra_pausa.pack(pady=8)

        ctk.CTkLabel(
            alerta,
            text="Realice estiramientos cervicales y de hombros.\nGire el cuello suavemente de lado a lado.",
            font=ctk.CTkFont(size=11),
            text_color=PALETA["texto_secundario"],
            justify="center",
        ).pack(pady=6)

        segundos_restantes = [DURACION_PAUSA_ACTIVA_SEGUNDOS]

        def decrementar():
            try:
                if not alerta.winfo_exists():
                    self._liberar_bloqueo_alerta()
                    return
                if segundos_restantes[0] > 0:
                    segundos_restantes[0] -= 1
                    label_tiempo.configure(text=f"{segundos_restantes[0]}s")
                    barra_pausa.set(segundos_restantes[0] / DURACION_PAUSA_ACTIVA_SEGUNDOS)
                    alerta.after(1000, decrementar)
                else:
                    self._cerrar_alerta(alerta)
            except Exception:
                self._liberar_bloqueo_alerta()

        alerta.after(1000, decrementar)

    def _cerrar_alerta(self, alerta: ctk.CTkToplevel) -> None:
        try:
            if alerta.winfo_exists():
                alerta.destroy()
        except Exception:
            pass
        self._liberar_bloqueo_alerta()

    def _liberar_bloqueo_alerta(self) -> None:
        with self._lock:
            self._mostrando_alerta = False
