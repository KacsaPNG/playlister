"""
Smart Playlist Queue and YouTube Audio Stream Ingestion Widget.
Features asynchronous non-blocking yt-dlp stream downloading and PCM decoding,
local audio file loading, alternating A/B deck routing, and live playlist management.
"""
from typing import Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFrame,
    QMenu,
    QAbstractItemView,
)

from app.audio.buffer import AudioTrack
from app.audio.engine import DualDeckAudioEngine
from app.config import DeckId
from app.ingestion.local_loader import LocalAudioLoader
from app.ingestion.ytdlp_stream import YouTubeIngestor
from app.queue.smart_queue import QueueStatus, QueueItem
from app.gui.theme import (
    DECK_A_COLOR,
    DECK_B_COLOR,
    ACCENT_GREEN,
    ACCENT_AMBER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    PANEL_DARK,
    PANEL_BORDER,
)


class IngestionWorker(QThread):
    """
    Background worker thread to ingest YouTube streams or local files
    without hitching or blocking the real-time audio thread or GUI.
    """

    progress_signal = pyqtSignal(str, float)  # (status_message, percent_0_to_1)
    finished_signal = pyqtSignal(object, str)  # (AudioTrack, target_action)
    error_signal = pyqtSignal(str)

    def __init__(self, source_url: str, is_youtube: bool, target_action: str, sample_rate: int):
        super().__init__()
        self.source_url = source_url
        self.is_youtube = is_youtube
        self.target_action = target_action  # "QUEUE", "DECK_A", or "DECK_B"
        self.sample_rate = sample_rate

    def run(self):
        try:
            if self.is_youtube:
                ingestor = YouTubeIngestor(self.sample_rate)
                track = ingestor.ingest_url(
                    self.source_url,
                    progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct),
                )
            else:
                loader = LocalAudioLoader(self.sample_rate)
                track = loader.load_file(
                    self.source_url,
                    progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct),
                )
            self.finished_signal.emit(track, self.target_action)
        except Exception as e:
            self.error_signal.emit(str(e))


class QueueWidget(QWidget):
    """
    Smart Queue playlist table and ingestion interface.
    """

    def __init__(self, engine: DualDeckAudioEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._worker: Optional[IngestionWorker] = None

        self._init_ui()

        # Listen to queue changes
        self.engine.queue.add_change_listener(self.refresh_table)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. INGESTION TOOLBAR
        ingest_frame = QFrame()
        ingest_frame.setStyleSheet(
            f"background-color: {PANEL_DARK}; border: 1px solid {PANEL_BORDER}; border-radius: 6px; padding: 4px;"
        )
        ingest_layout = QVBoxLayout(ingest_frame)
        ingest_layout.setSpacing(4)

        # Top row: URL Input and Buttons
        input_row = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube or YouTube Music URL here (e.g. https://www.youtube.com/watch?v=...)...")
        self.url_input.returnPressed.connect(self._on_add_to_queue)
        input_row.addWidget(self.url_input, stretch=1)

        # Ingestion Buttons
        self.btn_queue = QPushButton("ADD TO QUEUE (AUTO A/B)")
        self.btn_queue.setStyleSheet(
            f"background-color: #1a2a38; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; font-weight: bold;"
        )
        self.btn_queue.clicked.connect(self._on_add_to_queue)
        input_row.addWidget(self.btn_queue)

        self.btn_load_a = QPushButton("LOAD -> DECK A")
        self.btn_load_a.setStyleSheet(
            f"background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; font-weight: bold;"
        )
        self.btn_load_a.clicked.connect(lambda: self._on_ingest_direct("DECK_A"))
        input_row.addWidget(self.btn_load_a)

        self.btn_load_b = QPushButton("LOAD -> DECK B")
        self.btn_load_b.setStyleSheet(
            f"background-color: #331e0d; color: {DECK_B_COLOR}; border: 1px solid {DECK_B_COLOR}; font-weight: bold;"
        )
        self.btn_load_b.clicked.connect(lambda: self._on_ingest_direct("DECK_B"))
        input_row.addWidget(self.btn_load_b)

        # Browse Local File button
        self.btn_browse = QPushButton("BROWSE LOCAL FILE...")
        self.btn_browse.setStyleSheet("background-color: #242936; color: #ffffff;")
        self.btn_browse.clicked.connect(self._on_browse_local)
        input_row.addWidget(self.btn_browse)

        # Netlify Web Queue Sync button
        self.btn_netlify = QPushButton("🌐 NETLIFY SYNC")
        self.btn_netlify.setStyleSheet(
            f"background-color: #1f1d36; color: #c77dff; border: 1px solid #7b2cbf; font-weight: bold;"
        )
        self.btn_netlify.setToolTip("Open Netlify Web Queue to view guest requests and remove songs")
        self.btn_netlify.clicked.connect(self._on_open_netlify_sync)
        input_row.addWidget(self.btn_netlify)

        ingest_layout.addLayout(input_row)

        # Bottom row: Progress bar and status label
        progress_row = QHBoxLayout()
        self.status_label = QLabel("Ready to ingest YouTube audio streams or local tracks.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        progress_row.addWidget(self.status_label, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        progress_row.addWidget(self.progress_bar)

        ingest_layout.addLayout(progress_row)
        main_layout.addWidget(ingest_frame)

        # 2. SMART QUEUE PLAYLIST TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#", "Track Title", "Artist", "Duration", "BPM", "LUFS / Auto-Gain", "Deck", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        # Enable double-click to jump/load track
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        # Enable right-click context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        main_layout.addWidget(self.table)

    # ── Playlist jump helpers ────────────────────────────────────────────────

    def _on_table_double_clicked(self, index):
        """Double-click: load the selected track to its designated deck immediately."""
        row = index.row()
        if row < 0 or row >= len(self.engine.queue.items):
            return
        item = self.engine.queue.items[row]
        self._jump_load_track(item, item.target_deck)

    def _on_table_context_menu(self, pos):
        """Right-click context menu: load to Deck A, load to Deck B, or remove from queue."""
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self.engine.queue.items):
            return

        item = self.engine.queue.items[row]
        menu = QMenu(self)

        act_a = menu.addAction(f"▶  Load to Deck A (now)")
        act_b = menu.addAction(f"▶  Load to Deck B (now)")
        menu.addSeparator()
        act_remove = menu.addAction("✕  Remove from queue")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_a:
            self._jump_load_track(item, "A")
        elif action == act_b:
            self._jump_load_track(item, "B")
        elif action == act_remove:
            self.engine.queue.remove_index(row)

    def _jump_load_track(self, item, deck_id: str):
        """Load a queued track to the specified deck immediately and update statuses."""
        track = item.track
        if deck_id == "A":
            self.engine.deck_a.load_track(track)
            item.target_deck = "A"
        else:
            self.engine.deck_b.load_track(track)
            item.target_deck = "B"
        from app.queue.smart_queue import QueueStatus
        item.status = QueueStatus.LOADED_A if deck_id == "A" else QueueStatus.LOADED_B
        self.refresh_table()


    def _on_add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self._start_ingestion(url, is_youtube=True, target_action="QUEUE")

    def _on_ingest_direct(self, target_deck: str):
        url = self.url_input.text().strip()
        if not url:
            return
        self._start_ingestion(url, is_youtube=True, target_action=target_deck)

    def _on_browse_local(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio Track",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.aiff);;All Files (*.*)",
        )
        if file_path:
            self._start_ingestion(file_path, is_youtube=False, target_action="QUEUE")

    def _start_ingestion(self, source: str, is_youtube: bool, target_action: str):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "Another audio stream is currently being ingested. Please wait.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.status_label.setText(f"Ingesting: {source[:60]}...")

        self._worker = IngestionWorker(source, is_youtube, target_action, self.engine.sample_rate)
        self._worker.progress_signal.connect(self._on_worker_progress)
        self._worker.finished_signal.connect(self._on_worker_finished)
        self._worker.error_signal.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_progress(self, msg: str, pct: float):
        self.status_label.setText(msg)
        self.progress_bar.setValue(int(pct * 100))

    def _on_worker_finished(self, track: AudioTrack, target_action: str):
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Successfully loaded: {track.metadata.title}")
        self.url_input.clear()

        if target_action == "DECK_A":
            self.engine.deck_a.load_track(track)
        elif target_action == "DECK_B":
            self.engine.deck_b.load_track(track)
        else:
            # Add to smart queue (auto alternates A / B)
            self.engine.queue.add_track(track)

            # If Deck A is empty, preload immediately
            if self.engine.deck_a.track is None:
                next_a = self.engine.queue.get_next_for_deck("A")
                if next_a is not None:
                    self.engine.deck_a.load_track(next_a)

            # If Deck B is empty, preload immediately
            if self.engine.deck_b.track is None:
                next_b = self.engine.queue.get_next_for_deck("B")
                if next_b is not None:
                    self.engine.deck_b.load_track(next_b)

        self.refresh_table()

    def _on_worker_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {err_msg[:80]}")
        QMessageBox.critical(self, "Ingestion Error", f"Failed to ingest audio source:\n{err_msg}")

    def refresh_table(self):
        """Re-render smart queue table with current queue items."""
        items = self.engine.queue.items
        self.table.setRowCount(len(items))

        for idx, item in enumerate(items):
            m = item.track.metadata

            # Col 0: Index
            num_item = QTableWidgetItem(f"{idx + 1}")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 0, num_item)

            # Col 1: Title
            title_item = QTableWidgetItem(m.title)
            title_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(idx, 1, title_item)

            # Col 2: Artist
            self.table.setItem(idx, 2, QTableWidgetItem(m.artist))

            # Col 3: Duration
            d_min = int(m.duration_sec // 60)
            d_sec = int(m.duration_sec % 60)
            dur_item = QTableWidgetItem(f"{d_min:02d}:{d_sec:02d}")
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 3, dur_item)

            # Col 4: BPM
            bpm_item = QTableWidgetItem(f"{m.bpm:.1f}")
            bpm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 4, bpm_item)

            # Col 5: LUFS & Auto-Gain
            lufs_text = f"{m.loudness_lufs:.1f} ({m.auto_gain_db:+.1f} dB)"
            lufs_item = QTableWidgetItem(lufs_text)
            lufs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 5, lufs_item)

            # Col 6: Assigned Deck
            deck_item = QTableWidgetItem(f"Deck {item.target_deck}")
            deck_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            deck_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if item.target_deck == "A":
                deck_item.setForeground(QColor(DECK_A_COLOR))
            else:
                deck_item.setForeground(QColor(DECK_B_COLOR))
            self.table.setItem(idx, 6, deck_item)

            # Col 7: Status
            status_item = QTableWidgetItem(item.status.value)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if item.status == QueueStatus.PLAYING:
                status_item.setForeground(QColor(ACCENT_GREEN))
            elif item.status == QueueStatus.PLAYED:
                status_item.setForeground(QColor("#586069"))
            self.table.setItem(idx, 7, status_item)

    def _on_open_netlify_sync(self):
        """Open Netlify Web Queue sync dialog to preview submissions, remove songs, and load to decks."""
        from app.gui.netlify_sync_dialog import NetlifySyncDialog
        dialog = NetlifySyncDialog(self, parent=self)
        dialog.exec()

