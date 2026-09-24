"""
Deck User Interface Widget (Deck A and Deck B).
Encapsulates Waveform display, Pioneer-style Transport controls (PLAY, CUE, SYNC, Pitch Bend),
Tempo Slider with Key-Lock, 3-Band Parametric EQ with Kills, DJ Filter sweep,
Algorithmic Reverb Unit, and Stereo VU Level Meter.
"""
from typing import Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QGroupBox,
    QFrame,
)

from app.audio.deck import Deck
from app.config import DeckId, PlaybackState
from app.gui.waveform_widget import WaveformWidget
from app.gui.vu_meter import VuMeterWidget
from app.gui.theme import (
    DECK_A_COLOR,
    DECK_B_COLOR,
    ACCENT_GREEN,
    ACCENT_RED,
    ACCENT_AMBER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    PANEL_DARK,
    PANEL_BORDER,
)


class DeckWidget(QWidget):
    """
    Complete DJ Deck Control Panel.
    """

    sync_requested = pyqtSignal(str)  # Emits target deck ID

    def __init__(self, deck: Deck, parent=None):
        super().__init__(parent)
        self.deck = deck
        self.accent_color = DECK_A_COLOR if deck.deck_id == DeckId.DECK_A else DECK_B_COLOR

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. TOP HEADER: Deck Badge, Track Info, Big LCD Time & BPM
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"background-color: {PANEL_DARK}; border: 1px solid {PANEL_BORDER}; border-radius: 6px; padding: 4px;"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 4, 6, 4)

        # Deck Badge
        self.badge_label = QLabel(f"DECK {self.deck.deck_id}")
        self.badge_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.badge_label.setStyleSheet(
            f"color: #000000; background-color: {self.accent_color}; border-radius: 4px; padding: 4px 8px;"
        )
        header_layout.addWidget(self.badge_label)

        # Track metadata column
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(2)
        self.title_label = QLabel("No Track Loaded")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_PRIMARY};")

        self.artist_label = QLabel("Drag & drop, queue, or load via URL / file below")
        self.artist_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")

        meta_layout.addWidget(self.title_label)
        meta_layout.addWidget(self.artist_label)
        header_layout.addLayout(meta_layout, stretch=1)

        # Loudness & Gain Info
        loudness_layout = QVBoxLayout()
        loudness_layout.setSpacing(1)
        self.lufs_label = QLabel("LUFS: --")
        self.lufs_label.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: bold;")
        self.autogain_label = QLabel("Auto-Gain: --")
        self.autogain_label.setStyleSheet("color: #00e676; font-size: 10px; font-weight: bold;")
        loudness_layout.addWidget(self.lufs_label)
        loudness_layout.addWidget(self.autogain_label)
        header_layout.addLayout(loudness_layout)

        # Big Digital Clock Display
        time_layout = QVBoxLayout()
        time_layout.setSpacing(1)
        self.time_elapsed_label = QLabel("00:00.0")
        self.time_elapsed_label.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self.time_elapsed_label.setStyleSheet(f"color: {self.accent_color};")

        self.time_rem_label = QLabel("-00:00.0")
        self.time_rem_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.time_rem_label.setStyleSheet("color: #8b949e;")

        time_layout.addWidget(self.time_elapsed_label)
        time_layout.addWidget(self.time_rem_label)
        header_layout.addLayout(time_layout)

        # BPM Display Box
        bpm_layout = QVBoxLayout()
        bpm_layout.setSpacing(1)
        self.bpm_label = QLabel("120.0")
        self.bpm_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.bpm_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self.pitch_pct_label = QLabel("+0.00 %")
        self.pitch_pct_label.setStyleSheet(f"color: {self.accent_color}; font-size: 11px; font-weight: bold;")

        bpm_layout.addWidget(self.bpm_label)
        bpm_layout.addWidget(self.pitch_pct_label)
        header_layout.addLayout(bpm_layout)

        main_layout.addWidget(header_frame)

        # 2. WAVEFORM VISUALIZER WITH STEREO VU METER
        wave_box = QHBoxLayout()
        self.waveform_widget = WaveformWidget(self.deck)
        self.waveform_widget.seek_requested.connect(self.deck.seek_fraction)
        wave_box.addWidget(self.waveform_widget, stretch=1)

        self.vu_meter = VuMeterWidget(is_horizontal=False)
        wave_box.addWidget(self.vu_meter)
        main_layout.addLayout(wave_box)

        # 3. LOWER SECTION: Controls, EQ, Loop, Reverb, Pitch
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        # --- Column 1: Transport Controls (Play, Cue, Sync, Nudge) ---
        transport_group = QGroupBox("Transport")
        tg_layout = QVBoxLayout(transport_group)
        tg_layout.setSpacing(6)

        # Big Play / Pause Button
        self.btn_play = QPushButton("PLAY")
        self.btn_play.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_play.setMinimumHeight(38)
        self.btn_play.setStyleSheet(
            f"QPushButton {{ background-color: #0b3d1f; color: {ACCENT_GREEN}; border: 2px solid {ACCENT_GREEN}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background-color: #12592f; }}"
        )
        self.btn_play.clicked.connect(self._on_play_pause_clicked)
        tg_layout.addWidget(self.btn_play)

        # Big CUE Button (Pioneer DJ behavior)
        self.btn_cue = QPushButton("CUE")
        self.btn_cue.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_cue.setMinimumHeight(36)
        self.btn_cue.setStyleSheet(
            f"QPushButton {{ background-color: #401018; color: {ACCENT_RED}; border: 2px solid {ACCENT_RED}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background-color: #5c1824; }}"
        )
        self.btn_cue.pressed.connect(self.deck.cue_press)
        self.btn_cue.released.connect(self.deck.cue_release)
        tg_layout.addWidget(self.btn_cue)

        # Sync and Stop row
        sub_row = QHBoxLayout()
        self.btn_sync = QPushButton("SYNC")
        self.btn_sync.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_sync.setStyleSheet(
            f"QPushButton {{ background-color: #382805; color: {ACCENT_AMBER}; border: 1px solid {ACCENT_AMBER}; }}"
        )
        self.btn_sync.clicked.connect(self._on_sync_clicked)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.clicked.connect(self.deck.stop)
        sub_row.addWidget(self.btn_sync)
        sub_row.addWidget(self.btn_stop)
        tg_layout.addLayout(sub_row)

        # Pitch Bend Nudge Buttons (- and +)
        nudge_row = QHBoxLayout()
        self.btn_nudge_minus = QPushButton("NUDGE -")
        self.btn_nudge_minus.pressed.connect(self.deck.pitch_bend.nudge_down)
        self.btn_nudge_minus.released.connect(self.deck.pitch_bend.release)

        self.btn_nudge_plus = QPushButton("NUDGE +")
        self.btn_nudge_plus.pressed.connect(self.deck.pitch_bend.nudge_up)
        self.btn_nudge_plus.released.connect(self.deck.pitch_bend.release)
        nudge_row.addWidget(self.btn_nudge_minus)
        nudge_row.addWidget(self.btn_nudge_plus)
        tg_layout.addLayout(nudge_row)

        controls_layout.addWidget(transport_group)

        # --- Column 2: Beat Looping Section ---
        loop_group = QGroupBox("Beat Loop")
        lg_layout = QVBoxLayout(loop_group)
        lg_layout.setSpacing(4)

        loop_grid = QGridLayout()
        beats = [1, 2, 4, 8, 16]
        for idx, b in enumerate(beats):
            btn = QPushButton(f"{b}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, beats=b: self._on_loop_beat_clicked(beats))
            loop_grid.addWidget(btn, idx // 3, idx % 3)

        lg_layout.addLayout(loop_grid)

        self.btn_loop_exit = QPushButton("EXIT LOOP")
        self.btn_loop_exit.setStyleSheet("color: #ffab00;")
        self.btn_loop_exit.clicked.connect(self.deck.exit_loop if hasattr(self.deck, 'exit_loop') else self.deck.toggle_loop)
        lg_layout.addWidget(self.btn_loop_exit)

        controls_layout.addWidget(loop_group)

        # --- Column 3: 3-Band Parametric EQ & DJ Color Sweep Filter ---
        eq_group = QGroupBox("EQ / Filter")
        # EQ Group layout with bottom Reset EQ & Filter button
        eq_box_outer = QVBoxLayout(eq_group)
        eq_box_outer.setSpacing(4)
        eq_layout = QHBoxLayout()
        eq_layout.setSpacing(8)

        # HIGH Band
        hi_box = QVBoxLayout()
        hi_label = QLabel("HIGH")
        hi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_hi = QSlider(Qt.Orientation.Vertical)
        self.slider_hi.setRange(-24, 12)
        self.slider_hi.setValue(0)
        self.slider_hi.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.eq, "high_gain", float(v)))
        self.btn_hi_kill = QPushButton("KILL")
        self.btn_hi_kill.setCheckable(True)
        self.btn_hi_kill.toggled.connect(lambda k: setattr(self.deck.dsp_chain.eq, "high_kill", k))
        hi_box.addWidget(hi_label)
        hi_box.addWidget(self.slider_hi, alignment=Qt.AlignmentFlag.AlignHCenter)
        hi_box.addWidget(self.btn_hi_kill)
        eq_layout.addLayout(hi_box)

        # MID Band
        mid_box = QVBoxLayout()
        mid_label = QLabel("MID")
        mid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_mid = QSlider(Qt.Orientation.Vertical)
        self.slider_mid.setRange(-24, 12)
        self.slider_mid.setValue(0)
        self.slider_mid.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.eq, "mid_gain", float(v)))
        self.btn_mid_kill = QPushButton("KILL")
        self.btn_mid_kill.setCheckable(True)
        self.btn_mid_kill.toggled.connect(lambda k: setattr(self.deck.dsp_chain.eq, "mid_kill", k))
        mid_box.addWidget(mid_label)
        mid_box.addWidget(self.slider_mid, alignment=Qt.AlignmentFlag.AlignHCenter)
        mid_box.addWidget(self.btn_mid_kill)
        eq_layout.addLayout(mid_box)

        # LOW Band
        low_box = QVBoxLayout()
        low_label = QLabel("LOW")
        low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_low = QSlider(Qt.Orientation.Vertical)
        self.slider_low.setRange(-24, 12)
        self.slider_low.setValue(0)
        self.slider_low.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.eq, "low_gain", float(v)))
        self.btn_low_kill = QPushButton("KILL")
        self.btn_low_kill.setCheckable(True)
        self.btn_low_kill.toggled.connect(lambda k: setattr(self.deck.dsp_chain.eq, "low_kill", k))
        low_box.addWidget(low_label)
        low_box.addWidget(self.slider_low, alignment=Qt.AlignmentFlag.AlignHCenter)
        low_box.addWidget(self.btn_low_kill)
        eq_layout.addLayout(low_box)

        # DJ Color Sweep Filter
        flt_box = QVBoxLayout()
        flt_label = QLabel("FILTER")
        flt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_filter = QSlider(Qt.Orientation.Vertical)
        self.slider_filter.setRange(-100, 100)
        self.slider_filter.setValue(0)
        self.slider_filter.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.eq, "filter_knob", v / 100.0))
        btn_flt_reset = QPushButton("OFF")
        btn_flt_reset.clicked.connect(lambda: self.slider_filter.setValue(0))
        flt_box.addWidget(flt_label)
        flt_box.addWidget(self.slider_filter, alignment=Qt.AlignmentFlag.AlignHCenter)
        flt_box.addWidget(btn_flt_reset)
        eq_layout.addLayout(flt_box)

        eq_box_outer.addLayout(eq_layout)

        # Dedicated Reset EQ & Filter Button
        self.btn_reset_eq = QPushButton("RESET EQ / FILTER")
        self.btn_reset_eq.setStyleSheet("background-color: #20242e; color: #f0f4f8; font-size: 10px; font-weight: bold;")
        self.btn_reset_eq.clicked.connect(self.reset_eq_and_filter)
        eq_box_outer.addWidget(self.btn_reset_eq)

        controls_layout.addWidget(eq_group)

        # --- Column 4: Algorithmic Reverb Unit ---
        rev_group = QGroupBox("Reverb Unit")
        rev_layout = QVBoxLayout(rev_group)
        rev_layout.setSpacing(4)

        self.btn_reverb_on = QPushButton("REV ON")
        self.btn_reverb_on.setCheckable(True)
        self.btn_reverb_on.toggled.connect(self._on_reverb_toggled)
        rev_layout.addWidget(self.btn_reverb_on)

        # Wet/Dry
        rev_layout.addWidget(QLabel("Wet/Dry:"))
        self.slider_rev_wet = QSlider(Qt.Orientation.Horizontal)
        self.slider_rev_wet.setRange(0, 100)
        self.slider_rev_wet.setValue(35)
        self.slider_rev_wet.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.reverb, "wet", v / 100.0))
        rev_layout.addWidget(self.slider_rev_wet)

        # Room Size
        rev_layout.addWidget(QLabel("Room Size:"))
        self.slider_rev_room = QSlider(Qt.Orientation.Horizontal)
        self.slider_rev_room.setRange(0, 98)
        self.slider_rev_room.setValue(75)
        self.slider_rev_room.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain.reverb, "room_size", v / 100.0))
        rev_layout.addWidget(self.slider_rev_room)

        # Deck Gain Trim
        rev_layout.addWidget(QLabel("Trim Gain:"))
        self.slider_trim = QSlider(Qt.Orientation.Horizontal)
        self.slider_trim.setRange(-12, 12)
        self.slider_trim.setValue(0)
        self.slider_trim.valueChanged.connect(lambda v: setattr(self.deck.dsp_chain, "input_gain_db", float(v)))
        rev_layout.addWidget(self.slider_trim)

        # Dedicated Reset Reverb Button
        self.btn_reset_reverb = QPushButton("RESET REVERB")
        self.btn_reset_reverb.setStyleSheet("background-color: #20242e; color: #f0f4f8; font-size: 10px; font-weight: bold;")
        self.btn_reset_reverb.clicked.connect(self.reset_reverb_defaults)
        rev_layout.addWidget(self.btn_reset_reverb)

        controls_layout.addWidget(rev_group)

        # --- Column 5: Pitch / Tempo Slider (Key Lock) ---
        pitch_group = QGroupBox("Tempo")
        pg_layout = QVBoxLayout(pitch_group)
        pg_layout.setSpacing(4)

        self.btn_key_lock = QPushButton("KEY LOCK")
        self.btn_key_lock.setCheckable(True)
        self.btn_key_lock.toggled.connect(self._on_key_lock_toggled)
        pg_layout.addWidget(self.btn_key_lock)

        self.slider_pitch = QSlider(Qt.Orientation.Vertical)
        self.slider_pitch.setRange(-1600, 1600)  # -16.00% to +16.00%
        self.slider_pitch.setValue(0)
        self.slider_pitch.valueChanged.connect(self._on_pitch_changed)
        pg_layout.addWidget(self.slider_pitch, alignment=Qt.AlignmentFlag.AlignHCenter)

        btn_pitch_reset = QPushButton("0.0%")
        btn_pitch_reset.clicked.connect(lambda: self.slider_pitch.setValue(0))
        pg_layout.addWidget(btn_pitch_reset)

        controls_layout.addWidget(pitch_group)

        main_layout.addLayout(controls_layout)

    def _on_play_pause_clicked(self):
        self.deck.play_pause_toggle()

    def _on_sync_clicked(self):
        # Request sync to other deck
        other = "B" if self.deck.deck_id == DeckId.DECK_A else "A"
        self.sync_requested.emit(other)

    def _on_loop_beat_clicked(self, beats: float):
        self.deck.set_loop_beats(beats)

    def reset_eq_and_filter(self):
        """Reset all EQ gains, kill toggles and sweep filter to flat/neutral, updating UI sliders."""
        self.deck.dsp_chain.eq.reset_defaults()
        # Snap sliders back to center (0) without re-triggering DSP again
        for sl in (self.slider_hi, self.slider_mid, self.slider_low):
            sl.blockSignals(True)
            sl.setValue(0)
            sl.blockSignals(False)
        self.slider_filter.blockSignals(True)
        self.slider_filter.setValue(0)
        self.slider_filter.blockSignals(False)
        # Release kill buttons
        for btn in (self.btn_hi_kill, self.btn_mid_kill, self.btn_low_kill):
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.blockSignals(False)

    def reset_reverb_defaults(self):
        """Restore reverb to factory defaults and update UI sliders/buttons."""
        self.deck.dsp_chain.reverb.reset_defaults()
        # Snap slider positions back
        self.slider_rev_wet.blockSignals(True)
        self.slider_rev_wet.setValue(35)    # 0.35 wet
        self.slider_rev_wet.blockSignals(False)
        self.slider_rev_room.blockSignals(True)
        self.slider_rev_room.setValue(75)   # 0.75 room size
        self.slider_rev_room.blockSignals(False)
        self.slider_trim.blockSignals(True)
        self.slider_trim.setValue(0)
        self.slider_trim.blockSignals(False)
        # Turn off reverb toggle button
        self.btn_reverb_on.blockSignals(True)
        self.btn_reverb_on.setChecked(False)
        self.btn_reverb_on.blockSignals(False)
        self.btn_reverb_on.setStyleSheet("")


    def _on_reverb_toggled(self, checked: bool):
        self.deck.dsp_chain.reverb.enabled = checked
        if checked:
            self.btn_reverb_on.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #000000; font-weight: bold;")
        else:
            self.btn_reverb_on.setStyleSheet("")

    def _on_key_lock_toggled(self, checked: bool):
        self.deck.key_lock = checked
        if checked:
            self.btn_key_lock.setStyleSheet(f"background-color: {self.accent_color}; color: #000000; font-weight: bold;")
        else:
            self.btn_key_lock.setStyleSheet("")

    def _on_pitch_changed(self, value: int):
        pct = value / 100.0  # -16.0% to +16.0%
        self.deck.pitch_slider = pct

    def update_ui(self):
        """Called by GUI timer (30-60 Hz) to refresh position, time, meters, and buttons."""
        track = self.deck.track
        if track is not None:
            self.title_label.setText(track.metadata.title)
            self.artist_label.setText(track.metadata.artist)
            self.lufs_label.setText(f"LUFS: {track.metadata.loudness_lufs:.1f}")
            self.autogain_label.setText(f"Auto-Gain: {track.metadata.auto_gain_db:+.1f} dB")

            # Time formatting
            el = self.deck.elapsed_seconds
            rem = self.deck.remaining_seconds
            el_m = int(el // 60)
            el_s = el % 60
            self.time_elapsed_label.setText(f"{el_m:02d}:{el_s:04.1f}")

            rem_m = int(rem // 60)
            rem_s = rem % 60
            self.time_rem_label.setText(f"-{rem_m:02d}:{rem_s:04.1f}")

            # Highlight remaining time in red if under 10 seconds (Auto-DJ crossfade window)
            if rem <= 10.0:
                self.time_rem_label.setStyleSheet("color: #ff1744; font-weight: bold;")
            else:
                self.time_rem_label.setStyleSheet("color: #8b949e;")

            # BPM and Pitch readout
            eff_bpm = self.deck.current_bpm
            self.bpm_label.setText(f"{eff_bpm:.1f}")
            self.pitch_pct_label.setText(f"{self.deck.pitch_slider:+.2f} %")

        # Play button glow state
        if self.deck.state == PlaybackState.PLAYING:
            self.btn_play.setText("PAUSE")
            self.btn_play.setStyleSheet(
                f"QPushButton {{ background-color: {ACCENT_GREEN}; color: #000000; border: 2px solid #ffffff; font-weight: bold; border-radius: 6px; }}"
            )
        else:
            self.btn_play.setText("PLAY")
            self.btn_play.setStyleSheet(
                f"QPushButton {{ background-color: #0b3d1f; color: {ACCENT_GREEN}; border: 2px solid {ACCENT_GREEN}; border-radius: 6px; }}"
            )

        # Update Waveform
        self.waveform_widget.update()

        # Update Stereo VU levels
        peak_l = float(self.deck.dsp_chain.peak_levels[0])
        peak_r = float(self.deck.dsp_chain.peak_levels[1])
        self.vu_meter.set_levels(peak_l, peak_r)
