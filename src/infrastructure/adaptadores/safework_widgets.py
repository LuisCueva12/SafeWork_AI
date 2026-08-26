from __future__ import annotations

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def aplicar_sombra_suave(
    widget: QWidget,
    *,
    blur: int = 24,
    offset_y: int = 6,
    color: QColor | None = None,
) -> None:
    """Sombra difusa que reemplaza los bordes duros de tarjetas/paneles."""
    sombra = QGraphicsDropShadowEffect(widget)
    sombra.setBlurRadius(blur)
    sombra.setOffset(0, offset_y)
    sombra.setColor(color or QColor(15, 23, 42, 45))
    widget.setGraphicsEffect(sombra)


class CircularMetricWidget(QWidget):
    def __init__(self, titulo: str, icono: str = "", parent=None) -> None:
        super().__init__(parent)
        self._titulo = titulo
        self._icono = icono
        self._valor_texto = "--"
        self._valor_texto_animado = "--"
        self._subtexto = ""
        self._descripcion = ""
        self._porcentaje = 0.0
        self._porcentaje_objetivo = 0.0
        self._color = QColor("#94a3b8")
        self._color_ring_bg = QColor("#e2e8f0")
        # Caché de fuentes: se crean una sola vez en __init__ en lugar de en cada paintEvent.
        # paintEvent se llama ~41 veces/segundo (antes) → ahora 25 veces/segundo con timer a 40ms.
        # Sin caché cada repaint creaba y destruía 5 objetos QFont.
        self._font_icon = QFont("Segoe MDL2 Assets", 12)
        self._font_title = QFont("Segoe UI", 10)
        self._font_title.setWeight(QFont.Weight.DemiBold)
        self._font_val = QFont("Segoe UI", 16)
        self._font_val.setWeight(QFont.Weight.Bold)
        self._font_sub = QFont("Segoe UI", 10)
        self._font_sub.setWeight(QFont.Weight.DemiBold)
        self._font_desc = QFont("Segoe UI", 8)
        # Timer a 40ms (25fps) en lugar de 24ms (41fps) — visualmente idéntico, ~40% menos CPU
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._animar_hacia_objetivo)
        self.setFixedSize(140, 195)
        aplicar_sombra_suave(self, blur=18, offset_y=4)

    def actualizar(
        self,
        valor_texto: str,
        porcentaje: float,
        subtexto: str,
        descripcion: str,
        color_hex: str,
    ) -> None:
        self._valor_texto = valor_texto
        self._porcentaje_objetivo = max(0.0, min(100.0, porcentaje))
        self._subtexto = subtexto
        self._descripcion = descripcion
        self._color = QColor(color_hex)
        # Solo iniciar el timer si el widget es visible (evita repaints en segundo plano)
        if self.isVisible() and not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def _animar_hacia_objetivo(self) -> None:
        delta = self._porcentaje_objetivo - self._porcentaje
        if abs(delta) < 0.8:
            self._porcentaje = self._porcentaje_objetivo
            self._valor_texto_animado = self._valor_texto
            self._anim_timer.stop()
            self.update()
            return

        self._porcentaje += delta * 0.22
        self._actualizar_texto_animado()
        self.update()

    def _actualizar_texto_animado(self) -> None:
        texto = self._valor_texto.strip()
        if texto.endswith("%"):
            self._valor_texto_animado = f"{int(round(self._porcentaje))}%"
            return
        self._valor_texto_animado = self._valor_texto

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        rect = QRect(0, 0, w, h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect.adjusted(1, 1, -2, -2), 12, 12)

        icon_rect = QRect(14, 14, 20, 20)
        painter.setFont(self._font_icon)
        painter.setPen(QColor("#64748b"))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._icono)

        title_rect = QRect(36, 14, w - 40, 20)
        painter.setFont(self._font_title)
        painter.setPen(QColor("#0f172a"))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._titulo)

        ring_size = 72
        ring_x = (w - ring_size) // 2
        ring_y = 44
        ring_rect = QRect(ring_x, ring_y, ring_size, ring_size)
        ring_width = 6

        bg_pen = QPen(self._color_ring_bg)
        bg_pen.setWidth(ring_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(ring_rect.adjusted(ring_width // 2, ring_width // 2, -ring_width // 2, -ring_width // 2), 225 * 16, -270 * 16)

        if self._porcentaje > 0:
            fg_pen = QPen(self._color)
            fg_pen.setWidth(ring_width)
            fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen)
            span = int(-270 * 16 * self._porcentaje / 100.0)
            painter.drawArc(ring_rect.adjusted(ring_width // 2, ring_width // 2, -ring_width // 2, -ring_width // 2), 225 * 16, span)

        painter.setFont(self._font_val)
        painter.setPen(QColor("#1e293b"))
        painter.drawText(ring_rect, Qt.AlignmentFlag.AlignCenter, self._valor_texto_animado)

        sub_y = ring_y + ring_size + 14
        sub_rect = QRect(0, sub_y, w, 18)
        painter.setFont(self._font_sub)
        painter.setPen(self._color)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self._subtexto)

        if self._descripcion:
            desc_rect = QRect(10, sub_y + 20, w - 20, 28)
            painter.setFont(self._font_desc)
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self._descripcion)


class MiniTrendWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._valores: list[float] = [0.0, 0.0, 0.0, 0.0]
        self._objetivo: list[float] = [0.0, 0.0, 0.0, 0.0]
        # Timer a 40ms (25fps) en lugar de 30ms (33fps)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._animar_hacia_objetivo)
        self.setMinimumHeight(78)

    def actualizar(self, valores: list[float]) -> None:
        if not valores:
            self._objetivo = [0.0, 0.0, 0.0, 0.0]
        else:
            self._objetivo = [max(0.0, float(v)) for v in valores]
        while len(self._objetivo) < 4:
            self._objetivo.append(0.0)
        # Solo animar si el widget está visible
        if self.isVisible() and not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def _animar_hacia_objetivo(self) -> None:
        actualizado = False
        for indice, objetivo in enumerate(self._objetivo):
            actual = self._valores[indice]
            delta = objetivo - actual
            if abs(delta) < 0.25:
                self._valores[indice] = objetivo
                continue
            self._valores[indice] = actual + delta * 0.2
            actualizado = True
        if not actualizado:
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.fillRect(rect, QColor("#f8fbff"))
        pen_grid = QPen(QColor("#dbeafe"))
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)
        for ratio in (0.25, 0.5, 0.75):
            y = int(rect.top() + rect.height() * ratio)
            painter.drawLine(rect.left(), y, rect.right(), y)

        if len(self._valores) < 2:
            return

        v_min = min(self._valores)
        v_max = max(self._valores)
        span = max(1.0, v_max - v_min)
        n = len(self._valores) - 1

        puntos: list[tuple[int, int]] = []
        for i, v in enumerate(self._valores):
            x = int(rect.left() + (i / n) * rect.width())
            norm = (v - v_min) / span
            y = int(rect.bottom() - norm * rect.height())
            puntos.append((x, y))

        pen_linea = QPen(QColor("#0891b2"))
        pen_linea.setWidth(2)
        painter.setPen(pen_linea)
        for i in range(len(puntos) - 1):
            painter.drawLine(puntos[i][0], puntos[i][1], puntos[i + 1][0], puntos[i + 1][1])

        painter.setBrush(QColor("#06b6d4"))
        painter.setPen(QPen(QColor("#06b6d4")))
        for x, y in puntos:
            painter.drawEllipse(x - 2, y - 2, 4, 4)
