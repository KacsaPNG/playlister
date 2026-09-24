"""
Main Application Window for Standalone DJ System.
Hosts Dual Decks, Center Mixer, Ingestion / Smart Queue,
Audio Device Selector, and High-Precision Real-Time UI Refresh Loop.
"""
import logging
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QSplitter,
    QStatusBar,
    QMessageBox,
)
import sounddevice as sd

from app.audio.engine import DualDeckAudioEngine
from app.config import DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE
from app.gui.deck_widget import DeckWidget
from app.gui.mixer_widget import MixerWidget
from app.gui.queue_widget import QueueWidget
from app.gui.theme import (
    QSS_STYLESHEET,
    BG_DARK,
    PANEL_DARK,
    PANEL_BORDER,
    DECK_A_COLOR,
    DECK_B_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_GREEN,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main DJ Desktop Application Window.
    """

    def __init__(self, engine: DualDeckAudioEngine):
        super().__init__()
        self.engine = engine

        self.setWindowTitle("PLAYLISTERAG // Standalone Dual-Deck DJ System")
        self.resize(1340, 880)
        self.setMinimumSize(1100, 720)

        # Apply dark DJ stylesheet
        self.setStyleSheet(QSS_STYLESHEET)

        self._init_ui()
        self._init_audio_devices()

        # Connect Deck SYNC signals
        self.deck_a_widget.sync_requested.connect(self._sync_deck_a_to_b)
        self.deck_b_widget.sync_requested.connect(self._sync_deck_b_to_a)

        # Start Engine Audio Stream
        try:
            self.engine.start()
        except Exception as e:
            logger.error(f"Failed to initialize audio stream: {e}")
            QMessageBox.critical(self, "Audio Device Error", f"Could not open audio stream:\n{e}")

        # High-Rate UI Refresh & Auto-DJ Timer (~40 Hz = 25 ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)
        self.timer.start(25)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # 1. TOP HEADER BAR
        top_bar = QFrame()
        top_bar.setStyleSheet(
            f"background-color: {PANEL_DARK}; border: 1px solid {PANEL_BORDER}; border-radius: 6px; padding: 4px;"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)

        # App Brand Title
        brand_label = QLabel("PLAYLISTERAG // DUAL-DECK PRO DJ")
        brand_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        brand_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; letter-spacing: 1px;"
        )
        top_layout.addWidget(brand_label)

        top_layout.addStretch(1)

        # Audio Output Device Selector
        top_layout.addWidget(QLabel("Audio Output:"))
        self.combo_device = QComboBox()
        self.combo_device.setMinimumWidth(240)
        self.combo_device.currentIndexChanged.connect(self._on_device_changed)
        top_layout.addWidget(self.combo_device)

        # Beatmatching Toggle Button
        self.btn_beatmatch_top = QPushButton("BEATMATCH: ON")
        self.btn_beatmatch_top.setCheckable(True)
        self.btn_beatmatch_top.setChecked(self.engine.beatmatching_enabled)
        self.btn_beatmatch_top.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_beatmatch_top.setStyleSheet(
            f"QPushButton {{ background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; border-radius: 4px; padding: 4px 10px; }}"
        )
        self.btn_beatmatch_top.toggled.connect(self._on_top_beatmatch_toggled)
        top_layout.addWidget(self.btn_beatmatch_top)

        # Engine Stats readout
        self.label_sr = QLabel(f"{self.engine.sample_rate} Hz | {self.engine.block_size} spl")
        self.label_sr.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        top_layout.addWidget(self.label_sr)

        self.label_cpu = QLabel("DSP: 0.0% (0.0 ms)")
        self.label_cpu.setStyleSheet(
            f"background-color: #101217; color: {ACCENT_GREEN}; border: 1px solid #20242e; border-radius: 4px; padding: 3px 6px; font-weight: bold;"
        )
        top_layout.addWidget(self.label_cpu)

        main_layout.addWidget(top_bar)

        # 2. DECKS & MIXER SPLITTER
        decks_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Deck A
        self.deck_a_widget = DeckWidget(self.engine.deck_a)
        decks_splitter.addWidget(self.deck_a_widget)

        # Center Mixer
        self.mixer_widget = MixerWidget(self.engine)
        decks_splitter.addWidget(self.mixer_widget)

        # Deck B
        self.deck_b_widget = DeckWidget(self.engine.deck_b)
        decks_splitter.addWidget(self.deck_b_widget)

        decks_splitter.setStretchFactor(0, 4)
        decks_splitter.setStretchFactor(1, 2)
        decks_splitter.setStretchFactor(2, 4)

        # 3. BOTTOM: QUEUE & INGESTION
        self.queue_widget = QueueWidget(self.engine)

        # Master Vertical Splitter between Decks and Queue
        # Ratio 3:5 = decks get 37%, playlist gets 63% of vertical space
        vert_splitter = QSplitter(Qt.Orientation.Vertical)
        vert_splitter.addWidget(decks_splitter)
        vert_splitter.addWidget(self.queue_widget)
        vert_splitter.setStretchFactor(0, 3)
        vert_splitter.setStretchFactor(1, 5)
        # Set an initial size hint so the queue opens big on first launch
        vert_splitter.setSizes([380, 520])


        main_layout.addWidget(vert_splitter)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"background-color: {PANEL_DARK}; color: {TEXT_SECONDARY};")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Engine ready. Add YouTube tracks or local audio files to start.")

    def _init_audio_devices(self):
        """Populate audio output devices dropdown from sounddevice."""
        self.combo_device.blockSignals(True)
        self.combo_device.clear()

        try:
            devices = sd.query_devices()
            default_out = sd.default.device[1]

            out_idx = 0
            for idx, dev in enumerate(devices):
                if dev.get("max_output_channels", 0) >= 2:
                    name = f"[{idx}] {dev.get('name', 'Unknown')}"
                    self.combo_device.addItem(name, idx)
                    if idx == default_out:
                        self.combo_device.setCurrentIndex(out_idx)
                    out_idx += 1
        except Exception as e:
            logger.warning(f"Could not list audio devices: {e}")
            self.combo_device.addItem("Default Audio Device", None)

        self.combo_device.blockSignals(False)

    def _on_device_changed(self, idx: int):
        device_id = self.combo_device.currentData()
        try:
            self.engine.stop()
            self.engine.start(device_index=device_id)
            self.status_bar.showMessage(f"Switched audio device to ID {device_id}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Audio Device Error", f"Failed to switch to selected device:\n{e}")

    def _on_top_beatmatch_toggled(self, checked: bool):
        self.engine.beatmatching_enabled = checked
        if checked:
            self.btn_beatmatch_top.setText("BEATMATCH: ON")
            self.btn_beatmatch_top.setStyleSheet(
                f"QPushButton {{ background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; border-radius: 4px; padding: 4px 10px; }}"
            )
            self.status_bar.showMessage("Beatmatching enabled.", 2500)
        else:
            self.btn_beatmatch_top.setText("BEATMATCH: DISABLED")
            self.btn_beatmatch_top.setStyleSheet(
                "QPushButton { background-color: #20242e; color: #ff4d6d; border: 1px solid #ff3366; border-radius: 4px; padding: 4px 10px; }"
            )
            self.status_bar.showMessage("Beatmatching disabled.", 2500)

        # Sync mixer widget button if present
        if hasattr(self, "mixer_widget") and hasattr(self.mixer_widget, "btn_beatmatch"):
            if self.mixer_widget.btn_beatmatch.isChecked() != checked:
                self.mixer_widget.btn_beatmatch.blockSignals(True)
                self.mixer_widget.btn_beatmatch.setChecked(checked)
                self.mixer_widget._on_beatmatch_toggled(checked)
                self.mixer_widget.btn_beatmatch.blockSignals(False)

    def _sync_deck_a_to_b(self, _):
        """Sync Deck A tempo to Deck B current BPM."""
        if not self.engine.beatmatching_enabled:
            self.status_bar.showMessage("Beatmatching is disabled. Enable it to sync.", 3000)
            return
        target_bpm = self.engine.deck_b.current_bpm
        self.engine.deck_a.sync_to_bpm(target_bpm)
        self.deck_a_widget.slider_pitch.setValue(int(self.engine.deck_a.pitch_slider * 100.0))

    def _sync_deck_b_to_a(self, _):
        """Sync Deck B tempo to Deck A current BPM."""
        if not self.engine.beatmatching_enabled:
            self.status_bar.showMessage("Beatmatching is disabled. Enable it to sync.", 3000)
            return
        target_bpm = self.engine.deck_a.current_bpm
        self.engine.deck_b.sync_to_bpm(target_bpm)
        self.deck_b_widget.slider_pitch.setValue(int(self.engine.deck_b.pitch_slider * 100.0))

    def _on_timer_tick(self):
        """High-frequency periodic update."""
        # 1. Run Auto-DJ state machine
        self.engine.check_auto_dj()

        # 2. Update Decks UI
        self.deck_a_widget.update_ui()
        self.deck_b_widget.update_ui()

        # 3. Update Mixer UI
        self.mixer_widget.update_ui()

        # 4. Sync beatmatch top button
        if hasattr(self, "btn_beatmatch_top") and self.btn_beatmatch_top.isChecked() != self.engine.beatmatching_enabled:
            self.btn_beatmatch_top.blockSignals(True)
            self.btn_beatmatch_top.setChecked(self.engine.beatmatching_enabled)
            if self.engine.beatmatching_enabled:
                self.btn_beatmatch_top.setText("BEATMATCH: ON")
                self.btn_beatmatch_top.setStyleSheet(
                    f"QPushButton {{ background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; border-radius: 4px; padding: 4px 10px; }}"
                )
            else:
                self.btn_beatmatch_top.setText("BEATMATCH: DISABLED")
                self.btn_beatmatch_top.setStyleSheet(
                    "QPushButton { background-color: #20242e; color: #ff4d6d; border: 1px solid #ff3366; border-radius: 4px; padding: 4px 10px; }"
                )
            self.btn_beatmatch_top.blockSignals(False)

        # 5. Update CPU & latency readout
        cpu = self.engine.dsp_cpu_percent
        cb_dur = self.engine.callback_duration_ms
        self.label_cpu.setText(f"DSP: {cpu:.1f}% ({cb_dur:.2f} ms)")

    def closeEvent(self, event):
        """Clean shutdown of PortAudio stream upon window exit."""
        self.timer.stop()
        self.engine.stop()
        super().closeEvent(event)
