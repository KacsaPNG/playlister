"""
Real-time Stereo VU Level Meter Widget.
Draws Left and Right channel LED ladders with Green / Yellow / Red clip indicators.
"""
import numpy as np
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget


class VuMeterWidget(QWidget):
    """
    Compact stereo Peak & RMS VU level meter.
    Orientation: Vertical.
    """

    def __init__(self, parent=None, is_horizontal=False):
        super().__init__(parent)
        self.is_horizontal = is_horizontal
        if is_horizontal:
            self.setMinimumSize(100, 16)
            self.setMaximumHeight(20)
        else:
            self.setMinimumSize(18, 120)
            self.setMaximumWidth(24)

        self.level_l = 0.0
        self.level_r = 0.0
        self.peak_l = 0.0
        self.peak_r = 0.0
        self.decay = 0.88  # Peak decay rate

    def set_levels(self, l: float, r: float):
        """Update meter levels in range [0.0, 1.0]."""
        self.level_l = float(np.clip(l, 0.0, 1.2))
        self.level_r = float(np.clip(r, 0.0, 1.2))

        # Peak hold decay
        self.peak_l = max(self.level_l, self.peak_l * self.decay)
        self.peak_r = max(self.level_r, self.peak_r * self.decay)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#101216"))

        if not self.is_horizontal:
            # Vertical Meter (Left channel in col 1, Right in col 2)
            col_w = (w - 3) / 2.0
            self._draw_bar(painter, 1, 0, col_w, h, self.level_l, self.peak_l)
            self._draw_bar(painter, 2 + col_w, 0, col_w, h, self.level_r, self.peak_r)
        else:
            # Horizontal Meter (Top is Left, Bottom is Right)
            row_h = (h - 3) / 2.0
            self._draw_horiz_bar(painter, 0, 1, w, row_h, self.level_l, self.peak_l)
            self._draw_horiz_bar(painter, 0, 2 + row_h, w, row_h, self.level_r, self.peak_r)

    def _draw_bar(self, painter: QPainter, x: float, y: float, w: float, h: float, val: float, peak: float):
        num_leds = 20
        led_h = (h - (num_leds + 1)) / float(num_leds)

        for i in range(num_leds):
            # i = 0 is bottom (quiet), i = num_leds - 1 is top (loud/clip)
            led_norm = (i + 1) / float(num_leds)
            led_y = h - ((i + 1) * (led_h + 1))

            # LED Color
            if led_norm > 0.88:
                on_color = QColor("#ff1744")  # Red Clip
                off_color = QColor("#33050e")
            elif led_norm > 0.70:
                on_color = QColor("#ffab00")  # Yellow warning
                off_color = QColor("#332200")
            else:
                on_color = QColor("#00e676")  # Green normal
                off_color = QColor("#00331a")

            color = on_color if val >= led_norm else off_color
            painter.fillRect(QRectF(x, led_y, w, led_h), color)

        # Draw peak hold line
        peak_idx = int(np.clip(peak * num_leds, 0, num_leds - 1))
        peak_y = h - ((peak_idx + 1) * (led_h + 1))
        painter.fillRect(QRectF(x, peak_y, w, 2), QColor("#ffffff"))

    def _draw_horiz_bar(self, painter: QPainter, x: float, y: float, w: float, h: float, val: float, peak: float):
        num_leds = 30
        led_w = (w - (num_leds + 1)) / float(num_leds)

        for i in range(num_leds):
            led_norm = (i + 1) / float(num_leds)
            led_x = i * (led_w + 1)

            if led_norm > 0.88:
                on_color = QColor("#ff1744")
                off_color = QColor("#33050e")
            elif led_norm > 0.70:
                on_color = QColor("#ffab00")
                off_color = QColor("#332200")
            else:
                on_color = QColor("#00e676")
                off_color = QColor("#00331a")

            color = on_color if val >= led_norm else off_color
            painter.fillRect(QRectF(led_x, y, led_w, h), color)
