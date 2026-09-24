"""
Interactive Real-Time Waveform Visualizer for DJ Decks.
Renders an Overview Waveform with click-to-seek, cue markers, and loop regions,
plus a Dynamic Scrolling Zoom Waveform centered on the playhead needle for beat-matching.
"""
from typing import Optional
import numpy as np
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPolygonF
from PyQt6.QtWidgets import QWidget

from app.audio.deck import Deck
from app.config import DeckId


class WaveformWidget(QWidget):
    """
    High-performance QPainter DJ Waveform visualizer.
    Supports scrubbing/seeking via mouse interaction.
    """

    seek_requested = pyqtSignal(float)  # Emits normalized position [0.0, 1.0]

    def __init__(self, deck: Deck, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.setMinimumHeight(130)
        self.setMouseTracking(True)

        self._is_dragging = False

        # Theme colors based on Deck ID
        if deck.deck_id == DeckId.DECK_A:
            self.color_primary = QColor("#00e5ff")
            self.color_secondary = QColor("#0077b6")
            self.color_bg = QColor("#08121a")
            self.color_grid = QColor("#142a38")
        else:
            self.color_primary = QColor("#ff6d00")
            self.color_secondary = QColor("#d00000")
            self.color_bg = QColor("#1a0e08")
            self.color_grid = QColor("#381f14")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.deck.track is not None:
            self._is_dragging = True
            self._handle_mouse_seek(event.pos().x())

    def mouseMoveEvent(self, event):
        if self._is_dragging and self.deck.track is not None:
            self._handle_mouse_seek(event.pos().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def _handle_mouse_seek(self, mouse_x: float):
        w = max(1.0, float(self.width()))
        norm_pos = float(np.clip(mouse_x / w, 0.0, 1.0))
        self.seek_requested.emit(norm_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Fast crisp audio lines

        w = float(self.width())
        h = float(self.height())

        # Background
        painter.fillRect(self.rect(), self.color_bg)

        # Overview height (top 35%) and Zoomed Waveform height (bottom 65%)
        overview_h = h * 0.35
        zoom_h = h * 0.65
        zoom_top = overview_h

        # Separator line
        painter.setPen(QPen(QColor("#252a36"), 1))
        painter.drawLine(0, int(overview_h), int(w), int(overview_h))

        track = self.deck.track
        if track is None:
            # Draw placeholder centerlines
            painter.setPen(QPen(QColor("#262934"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(0, int(overview_h * 0.5), int(w), int(overview_h * 0.5))
            painter.drawLine(0, int(zoom_top + zoom_h * 0.5), int(w), int(zoom_top + zoom_h * 0.5))

            painter.setPen(QColor("#586069"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "NO TRACK LOADED")
            return

        # 1. RENDER OVERVIEW WAVEFORM (Top section)
        max_peaks, min_peaks = track.get_waveform_peaks(num_bins=int(w))
        num_bins = len(max_peaks)
        half_ov_h = overview_h * 0.5

        # Overview centerline
        painter.setPen(QPen(self.color_grid, 1))
        painter.drawLine(0, int(half_ov_h), int(w), int(half_ov_h))

        # Waveform amplitude bars
        painter.setPen(QPen(self.color_secondary, 1))
        for x_idx in range(num_bins):
            top_y = half_ov_h - (max_peaks[x_idx] * half_ov_h * 0.9)
            bot_y = half_ov_h - (min_peaks[x_idx] * half_ov_h * 0.9)
            painter.drawLine(x_idx, int(top_y), x_idx, int(bot_y))

        # Current Playhead position in overview
        progress_frac = self.deck.playhead_pos / float(max(1, track.total_samples))
        playhead_x = int(progress_frac * w)

        # Cue point marker in overview
        cue_frac = self.deck.cue_point / float(max(1, track.total_samples))
        cue_x = int(cue_frac * w)
        painter.setPen(QPen(QColor("#ff1744"), 2))
        painter.drawLine(cue_x, 0, cue_x, int(overview_h))

        # Loop active region in overview
        if self.deck.loop_active and self.deck.loop_end_pos > self.deck.loop_start_pos:
            l_start_x = int((self.deck.loop_start_pos / track.total_samples) * w)
            l_end_x = int((self.deck.loop_end_pos / track.total_samples) * w)
            loop_rect = QRectF(l_start_x, 0, max(2, l_end_x - l_start_x), overview_h)
            painter.fillRect(loop_rect, QColor(0, 230, 118, 40))

        # Playhead line in overview
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(playhead_x, 0, playhead_x, int(overview_h))

        # 2. RENDER SCROLLING ZOOM WAVEFORM (Bottom section)
        # Center needle is fixed at 50% width
        needle_x = w * 0.5
        center_y = zoom_top + (zoom_h * 0.5)
        half_z_h = zoom_h * 0.5

        # Show 3 seconds of audio centered at playhead
        zoom_window_sec = 3.0
        zoom_samples = int(track.sample_rate * zoom_window_sec)
        half_zoom_samples = zoom_samples // 2

        start_sample = int(self.deck.playhead_pos - half_zoom_samples)
        slice_samples = zoom_samples

        zoom_slice = track.get_slice(start_sample, slice_samples)
        mono_zoom = 0.5 * (zoom_slice[:, 0] + zoom_slice[:, 1])

        # Subsample to match screen pixel width
        step = max(1, len(mono_zoom) // int(w))
        decimated = mono_zoom[::step]
        num_points = min(int(w), len(decimated))

        # Grid lines / Beat ticks
        painter.setPen(QPen(self.color_grid, 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(center_y), int(w), int(center_y))

        # Beat lines based on BPM
        if track.metadata.bpm and track.metadata.bpm > 0:
            beat_sec = 60.0 / track.metadata.bpm
            beat_samples = beat_sec * track.sample_rate
            pixels_per_sample = w / float(zoom_samples)

            first_beat_idx = int(np.floor(start_sample / beat_samples))
            last_beat_idx = int(np.ceil((start_sample + zoom_samples) / beat_samples))

            painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
            for b_idx in range(first_beat_idx, last_beat_idx + 1):
                b_sample = b_idx * beat_samples
                bx = (b_sample - start_sample) * pixels_per_sample
                if 0 <= bx <= w:
                    painter.drawLine(int(bx), int(zoom_top), int(bx), int(h))

        # Draw Zoom Waveform polygon with gradient
        grad = QLinearGradient(0, zoom_top, 0, h)
        grad.setColorAt(0.0, self.color_primary)
        grad.setColorAt(0.5, self.color_secondary)
        grad.setColorAt(1.0, self.color_primary)
        painter.setPen(QPen(QBrush(grad), 1))

        # Draw vertical lines for each pixel in zoom
        for i in range(num_points):
            val = decimated[i]
            amplitude = val * half_z_h * 0.95
            y1 = center_y - amplitude
            y2 = center_y + amplitude
            painter.drawLine(i, int(y1), i, int(y2))

        # Center Playhead Needle
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(int(needle_x), int(zoom_top), int(needle_x), int(h))
        # Needle cap triangle
        triangle = QPolygonF([
            QPointF(needle_x - 5, zoom_top),
            QPointF(needle_x + 5, zoom_top),
            QPointF(needle_x, zoom_top + 8),
        ])
        painter.setBrush(QColor("#ffffff"))
        painter.drawPolygon(triangle)
