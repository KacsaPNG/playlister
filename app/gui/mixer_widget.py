"""
Center DJ Mixer and Auto-DJ Automation Widget.
Controls Deck A/B Channel Faders, Equal-Power Crossfader with selectable curves,
Master Volume, Master Peak Limiter GR Meter, and Auto-DJ Crossfade Controller.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QComboBox,
    QGroupBox,
    QFrame,
)

from app.audio.engine import DualDeckAudioEngine
from app.config import CrossfadeCurve
from app.gui.vu_meter import VuMeterWidget
from app.gui.theme import (
    DECK_A_COLOR,
    DECK_B_COLOR,
    ACCENT_GREEN,
    ACCENT_PURPLE,
    ACCENT_AMBER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    PANEL_DARK,
    PANEL_BORDER,
)


class MixerWidget(QWidget):
    """
    Central Mixer and Auto-DJ panel connecting Deck A and Deck B.
    """

    def __init__(self, engine: DualDeckAudioEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. TOP: Master Section & Limiter
        master_group = QGroupBox("Master Output & Limiter")
        mg_layout = QVBoxLayout(master_group)
        mg_layout.setSpacing(4)

        # Meter + Master Fader row
        meter_row = QHBoxLayout()

        # Master VU Meter
        self.master_vu = VuMeterWidget(is_horizontal=False)
        meter_row.addWidget(self.master_vu)

        # Master Volume Fader
        master_fader_box = QVBoxLayout()
        self.label_master_vol = QLabel("100%")
        self.label_master_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_master_vol = QSlider(Qt.Orientation.Vertical)
        self.slider_master_vol.setRange(0, 125)
        self.slider_master_vol.setValue(100)
        self.slider_master_vol.valueChanged.connect(self._on_master_vol_changed)

        master_fader_box.addWidget(self.label_master_vol)
        master_fader_box.addWidget(self.slider_master_vol, alignment=Qt.AlignmentFlag.AlignHCenter)
        meter_row.addLayout(master_fader_box)

        mg_layout.addLayout(meter_row)

        # Peak Limiter Gain Reduction (GR) readout
        self.limiter_badge = QLabel("LIMITER: 0.0 dB GR")
        self.limiter_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.limiter_badge.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.limiter_badge.setStyleSheet(
            "background-color: #101217; color: #00e676; border: 1px solid #20242e; border-radius: 4px; padding: 3px;"
        )
        mg_layout.addWidget(self.limiter_badge)

        main_layout.addWidget(master_group)

        # 2. CHANNEL FADERS SECTION (Deck A & Deck B Volume)
        fader_group = QGroupBox("Channel Faders")
        fg_layout = QHBoxLayout(fader_group)
        fg_layout.setSpacing(12)

        # Deck A Fader
        fa_box = QVBoxLayout()
        fa_label = QLabel("DECK A")
        fa_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        fa_label.setStyleSheet(f"color: {DECK_A_COLOR};")
        fa_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_vol_a = QSlider(Qt.Orientation.Vertical)
        self.slider_vol_a.setRange(0, 100)
        self.slider_vol_a.setValue(100)
        self.slider_vol_a.valueChanged.connect(
            lambda v: setattr(self.engine.deck_a.dsp_chain, "volume", v / 100.0)
        )
        fa_box.addWidget(fa_label)
        fa_box.addWidget(self.slider_vol_a, alignment=Qt.AlignmentFlag.AlignHCenter)
        fg_layout.addLayout(fa_box)

        # Deck B Fader
        fb_box = QVBoxLayout()
        fb_label = QLabel("DECK B")
        fb_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        fb_label.setStyleSheet(f"color: {DECK_B_COLOR};")
        fb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_vol_b = QSlider(Qt.Orientation.Vertical)
        self.slider_vol_b.setRange(0, 100)
        self.slider_vol_b.setValue(100)
        self.slider_vol_b.valueChanged.connect(
            lambda v: setattr(self.engine.deck_b.dsp_chain, "volume", v / 100.0)
        )
        fb_box.addWidget(fb_label)
        fb_box.addWidget(self.slider_vol_b, alignment=Qt.AlignmentFlag.AlignHCenter)
        fg_layout.addLayout(fb_box)

        main_layout.addWidget(fader_group)

        # 3. CROSSFADER SECTION
        xfader_group = QGroupBox("Equal-Power Crossfader")
        xg_layout = QVBoxLayout(xfader_group)
        xg_layout.setSpacing(4)

        # Curve selector
        curve_row = QHBoxLayout()
        curve_row.addWidget(QLabel("Curve:"))
        self.combo_curve = QComboBox()
        for curve in CrossfadeCurve:
            self.combo_curve.addItem(curve.value, curve)
        self.combo_curve.currentIndexChanged.connect(self._on_curve_changed)
        curve_row.addWidget(self.combo_curve)
        xg_layout.addLayout(curve_row)

        # Crossfader Labels A <---> B
        labels_row = QHBoxLayout()
        lbl_a = QLabel("A")
        lbl_a.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_a.setStyleSheet(f"color: {DECK_A_COLOR};")
        lbl_mid = QLabel("CENTER")
        lbl_mid.setStyleSheet("color: #8b949e; font-size: 10px;")
        lbl_b = QLabel("B")
        lbl_b.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_b.setStyleSheet(f"color: {DECK_B_COLOR};")
        labels_row.addWidget(lbl_a)
        labels_row.addStretch(1)
        labels_row.addWidget(lbl_mid)
        labels_row.addStretch(1)
        labels_row.addWidget(lbl_b)
        xg_layout.addLayout(labels_row)

        # Horizontal Crossfader Slider
        self.slider_crossfade = QSlider(Qt.Orientation.Horizontal)
        self.slider_crossfade.setRange(-100, 100)
        self.slider_crossfade.setValue(-100)
        self.slider_crossfade.valueChanged.connect(self._on_crossfader_moved)
        xg_layout.addWidget(self.slider_crossfade)

        # Snap Buttons
        snap_row = QHBoxLayout()
        btn_snap_a = QPushButton("< A")
        btn_snap_a.clicked.connect(lambda: self.slider_crossfade.setValue(-100))
        btn_snap_c = QPushButton("CENTER")
        btn_snap_c.clicked.connect(lambda: self.slider_crossfade.setValue(0))
        btn_snap_b = QPushButton("B >")
        btn_snap_b.clicked.connect(lambda: self.slider_crossfade.setValue(100))
        snap_row.addWidget(btn_snap_a)
        snap_row.addWidget(btn_snap_c)
        snap_row.addWidget(btn_snap_b)
        xg_layout.addLayout(snap_row)

        main_layout.addWidget(xfader_group)

        # 4. AUTO-DJ AUTOMATION PANEL
        autodj_group = QGroupBox("Smart Auto-DJ Engine")
        ag_layout = QVBoxLayout(autodj_group)
        ag_layout.setSpacing(6)

        # Master Auto-DJ Toggle
        self.btn_autodj = QPushButton("AUTO-DJ: ACTIVE")
        self.btn_autodj.setCheckable(True)
        self.btn_autodj.setChecked(True)
        self.btn_autodj.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_autodj.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT_PURPLE}; color: #000000; border-radius: 6px; padding: 6px; }}"
        )
        self.btn_autodj.toggled.connect(self._on_autodj_toggled)
        ag_layout.addWidget(self.btn_autodj)

        # Beatmatching Toggle
        self.btn_beatmatch = QPushButton("BEATMATCHING: ON")
        self.btn_beatmatch.setCheckable(True)
        self.btn_beatmatch.setChecked(getattr(self.engine, "beatmatching_enabled", True))
        self.btn_beatmatch.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_beatmatch.setStyleSheet(
            f"QPushButton {{ background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; border-radius: 6px; padding: 6px; }}"
        )
        self.btn_beatmatch.toggled.connect(self._on_beatmatch_toggled)
        ag_layout.addWidget(self.btn_beatmatch)

        # Duration setting (5s to 10s)
        dur_row = QHBoxLayout()
        self.label_duration = QLabel("Mix Duration: 7.0 s")
        self.label_duration.setStyleSheet("font-weight: bold;")
        dur_row.addWidget(self.label_duration)
        ag_layout.addLayout(dur_row)

        self.slider_duration = QSlider(Qt.Orientation.Horizontal)
        self.slider_duration.setRange(30, 150)  # 3.0s to 15.0s
        self.slider_duration.setValue(70)      # 7.0s default
        self.slider_duration.valueChanged.connect(self._on_duration_changed)
        ag_layout.addWidget(self.slider_duration)

        # Live status badge
        self.autodj_status = QLabel("STATUS: STANDBY")
        self.autodj_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.autodj_status.setStyleSheet(
            "background-color: #101217; color: #8b949e; border: 1px solid #20242e; border-radius: 4px; padding: 4px; font-weight: bold;"
        )
        ag_layout.addWidget(self.autodj_status)

        # Instant Manual Mix Trigger Button
        self.btn_trigger_mix = QPushButton("TRIGGER TRANSITION NOW")
        self.btn_trigger_mix.setStyleSheet(
            f"QPushButton {{ background-color: #2b1f06; color: {ACCENT_AMBER}; border: 1px solid {ACCENT_AMBER}; font-weight: bold; }}"
        )
        self.btn_trigger_mix.clicked.connect(self._on_manual_trigger_mix)
        ag_layout.addWidget(self.btn_trigger_mix)

        main_layout.addWidget(autodj_group)

    def _on_master_vol_changed(self, val: int):
        vol = val / 100.0
        self.engine.master_volume = vol
        self.label_master_vol.setText(f"{val}%")

    def _on_curve_changed(self, idx: int):
        curve = self.combo_curve.currentData()
        if curve:
            self.engine.crossfader.curve = curve

    def _on_crossfader_moved(self, val: int):
        pos = val / 100.0
        # If user moves slider manually, update crossfader
        if not self.engine.crossfader.is_transitioning:
            self.engine.crossfader.position = pos

    def _on_autodj_toggled(self, checked: bool):
        self.engine.crossfader.auto_dj_enabled = checked
        if checked:
            self.btn_autodj.setText("AUTO-DJ: ACTIVE")
            self.btn_autodj.setStyleSheet(
                f"QPushButton {{ background-color: {ACCENT_PURPLE}; color: #000000; border-radius: 6px; padding: 6px; }}"
            )
        else:
            self.btn_autodj.setText("AUTO-DJ: OFF")
            self.btn_autodj.setStyleSheet(
                "QPushButton { background-color: #20242e; color: #8b949e; border-radius: 6px; padding: 6px; }"
            )

    def _on_beatmatch_toggled(self, checked: bool):
        self.engine.beatmatching_enabled = checked
        if checked:
            self.btn_beatmatch.setText("BEATMATCHING: ON")
            self.btn_beatmatch.setStyleSheet(
                f"QPushButton {{ background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; border-radius: 6px; padding: 6px; }}"
            )
        else:
            self.btn_beatmatch.setText("BEATMATCHING: OFF (DISABLED)")
            self.btn_beatmatch.setStyleSheet(
                "QPushButton { background-color: #20242e; color: #ff4d6d; border: 1px solid #ff3366; border-radius: 6px; padding: 6px; }"
            )

    def _on_duration_changed(self, val: int):
        sec = val / 10.0
        self.engine.crossfader.set_duration(sec)
        self.label_duration.setText(f"Mix Duration: {sec:.1f} s")

    def _on_manual_trigger_mix(self):
        # Target the other deck
        target = "B" if self.engine.crossfader.position < 0 else "A"
        # Make sure target deck is playing
        target_deck = self.engine.deck_b if target == "B" else self.engine.deck_a
        if target_deck.track is not None:
            target_deck.play()
        self.engine.crossfader.start_auto_transition(target_deck=target)

    def update_ui(self):
        """Called by GUI refresh timer."""
        # Update Master VU
        peak_l = float(self.engine.master_peak_levels[0])
        peak_r = float(self.engine.master_peak_levels[1])
        self.master_vu.set_levels(peak_l, peak_r)

        # Update Limiter GR
        gr_db = self.engine.master_limiter.current_gr_db
        if gr_db < -0.1:
            self.limiter_badge.setText(f"LIMITER: {gr_db:.1f} dB GR")
            self.limiter_badge.setStyleSheet(
                "background-color: #33050e; color: #ff1744; border: 1px solid #ff1744; border-radius: 4px; padding: 3px;"
            )
        else:
            self.limiter_badge.setText("LIMITER: 0.0 dB GR (TRANSPARENT)")
            self.limiter_badge.setStyleSheet(
                "background-color: #101217; color: #00e676; border: 1px solid #20242e; border-radius: 4px; padding: 3px;"
            )

        # If Auto-DJ is transitioning, update slider visually
        if self.engine.crossfader.is_transitioning:
            slider_val = int(self.engine.crossfader.position * 100.0)
            self.slider_crossfade.blockSignals(True)
            self.slider_crossfade.setValue(slider_val)
            self.slider_crossfade.blockSignals(False)

            self.autodj_status.setText("MIXING TRANSITION IN PROGRESS...")
            self.autodj_status.setStyleSheet(
                f"background-color: #2b1f06; color: {ACCENT_AMBER}; border: 1px solid {ACCENT_AMBER}; border-radius: 4px; padding: 4px; font-weight: bold;"
            )
        else:
            # Check remaining seconds on active deck to show countdown
            active_deck = self.engine.deck_a if self.engine.crossfader.position <= 0 else self.engine.deck_b
            if active_deck.state.value == "PLAYING":
                rem = active_deck.remaining_seconds
                xfade_sec = self.engine.crossfader.crossfade_duration
                if rem <= xfade_sec + 5.0:
                    self.autodj_status.setText(f"TRANSITION IN {rem:.1f}s")
                    self.autodj_status.setStyleSheet(
                        "background-color: #33050e; color: #ff1744; border: 1px solid #ff1744; border-radius: 4px; padding: 4px; font-weight: bold;"
                    )
                else:
                    self.autodj_status.setText("STATUS: DECK PLAYING")
                    self.autodj_status.setStyleSheet(
                        "background-color: #101217; color: #00e676; border: 1px solid #20242e; border-radius: 4px; padding: 4px; font-weight: bold;"
                    )
            else:
                self.autodj_status.setText("STATUS: STANDBY")
                self.autodj_status.setStyleSheet(
                    "background-color: #101217; color: #8b949e; border: 1px solid #20242e; border-radius: 4px; padding: 4px; font-weight: bold;"
                )
