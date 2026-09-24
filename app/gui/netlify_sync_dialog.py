"""
Netlify Web Playlist Sync Dialog for PlaylisterAG.
Allows the DJ to fetch tracks submitted on the Netlify website,
preview them, remove unwanted songs directly from the playlist,
and load songs directly into Deck A or Deck B.
"""
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QCheckBox,
    QFrame,
)

from app.gui.theme import (
    DECK_A_COLOR,
    DECK_B_COLOR,
    PANEL_DARK,
    PANEL_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

DEFAULT_ENDPOINT = "http://localhost:5173/api/playlist"


def normalize_api_url(url: str) -> str:
    """Normalize user input URL to ensure valid http(s) and /api/playlist path."""
    url = url.strip()
    if not url:
        return DEFAULT_ENDPOINT
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    url = url.rstrip("/")
    if not url.endswith("/api/playlist"):
        url += "/api/playlist"
    return url


class FetchWebQueueWorker(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, endpoint_url: str):
        super().__init__()
        self.endpoint_url = normalize_api_url(endpoint_url)

    def run(self):
        try:
            req = urllib.request.Request(
                self.endpoint_url,
                headers={
                    "User-Agent": "PlaylisterAG-Desktop/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                content_type = response.headers.get("Content-Type", "")
                raw = response.read().decode("utf-8").strip()

                if not raw:
                    self.error_signal.emit(
                        "Server returned an empty response. Ensure the web application is running."
                    )
                    return

                # Check if server returned HTML instead of JSON
                if "text/html" in content_type or raw.startswith("<!") or raw.startswith("<html"):
                    self.error_signal.emit(
                        f"The server returned an HTML page instead of JSON API.\n\n"
                        f"Current URL: {self.endpoint_url}\n\n"
                        f"For local testing, make sure 'npm run dev' is running in the 'web' folder.\n"
                        f"For production, enter your Netlify site URL."
                    )
                    return

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    snippet = raw[:120].replace("\n", " ")
                    self.error_signal.emit(
                        f"Unable to parse response as JSON (got: {snippet!r}).\n"
                        f"Please verify the URL: {self.endpoint_url}"
                    )
                    return

                if not data.get("success", False):
                    self.error_signal.emit(data.get("error", "API request was not successful."))
                    return

                tracks = data.get("tracks", [])
                self.finished_signal.emit(tracks)

        except urllib.error.HTTPError as e:
            self.error_signal.emit(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            self.error_signal.emit(
                f"Cannot connect to {self.endpoint_url}\n\n"
                f"Reason: {e.reason}\n\n"
                f"For local dev, make sure 'npm run dev' is running in the 'web' folder."
            )
        except Exception as e:
            self.error_signal.emit(f"Connection error: {str(e)}")


class RemoveWebTrackWorker(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, endpoint_url: str, track_id: str):
        super().__init__()
        self.endpoint_url = normalize_api_url(endpoint_url)
        self.track_id = track_id

    def run(self):
        try:
            payload = json.dumps({"action": "remove", "id": self.track_id}).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "PlaylisterAG-Desktop/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read().decode("utf-8").strip()
                if raw:
                    try:
                        data = json.loads(raw)
                        if data.get("success"):
                            self.finished_signal.emit(True, "Track removed from web playlist.")
                            return
                        self.finished_signal.emit(False, data.get("error", "Removal failed."))
                    except json.JSONDecodeError:
                        self.finished_signal.emit(False, "Server returned invalid response.")
                else:
                    self.finished_signal.emit(False, "Empty response from server.")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class NetlifySyncDialog(QDialog):
    def __init__(self, queue_widget, parent=None):
        super().__init__(parent)
        self.queue_widget = queue_widget
        self.tracks: List[Dict] = []
        self._fetch_worker: Optional[FetchWebQueueWorker] = None
        self._remove_worker: Optional[RemoveWebTrackWorker] = None

        self.setWindowTitle("🌐 Netlify Web Playlist Sync & Dev View")
        self.setMinimumSize(860, 520)
        self.setStyleSheet(f"background-color: {PANEL_DARK}; color: {TEXT_PRIMARY};")

        self._init_ui()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._fetch_playlist)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Header / Connection ────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(
            f"background-color: #111827; border: 1px solid {PANEL_BORDER}; border-radius: 8px; padding: 10px;"
        )
        hdr_layout = QVBoxLayout(hdr)

        info = QLabel(
            "<b>Sync with Netlify Web Playlist:</b><br/>"
            "View songs submitted on the website, remove songs from the playlist, or load them directly into Deck A or Deck B."
        )
        info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        info.setTextFormat(Qt.TextFormat.RichText)
        hdr_layout.addWidget(info)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Website / API URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:5173 or https://your-site.netlify.app")
        self.url_input.setText(DEFAULT_ENDPOINT)
        self.url_input.setStyleSheet(
            f"background-color: #1f2937; border: 1px solid {PANEL_BORDER}; padding: 6px; border-radius: 4px;"
        )
        url_row.addWidget(self.url_input, stretch=1)

        self.btn_fetch = QPushButton("🔄 Fetch Playlist")
        self.btn_fetch.setStyleSheet(
            f"background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; font-weight: bold; padding: 6px 14px;"
        )
        self.btn_fetch.clicked.connect(self._fetch_playlist)
        url_row.addWidget(self.btn_fetch)
        hdr_layout.addLayout(url_row)

        opt_row = QHBoxLayout()
        self.chk_auto = QCheckBox("Auto-refresh every 8 seconds")
        self.chk_auto.stateChanged.connect(self._on_auto_check_changed)
        opt_row.addWidget(self.chk_auto)
        self.status_lbl = QLabel("Click 'Fetch Playlist' to connect.")
        self.status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        opt_row.addWidget(self.status_lbl, stretch=1)
        hdr_layout.addLayout(opt_row)

        layout.addWidget(hdr)

        # ── Track table ────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Song Title", "Artist", "Votes"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # ── Action Buttons ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self.btn_deck_a = QPushButton("Load → Deck A")
        self.btn_deck_a.setStyleSheet(
            f"background-color: #0d2833; color: {DECK_A_COLOR}; border: 1px solid {DECK_A_COLOR}; font-weight: bold; padding: 8px 14px;"
        )
        self.btn_deck_a.clicked.connect(lambda: self._load_selected("DECK_A"))
        btn_row.addWidget(self.btn_deck_a)

        self.btn_deck_b = QPushButton("Load → Deck B")
        self.btn_deck_b.setStyleSheet(
            f"background-color: #331e0d; color: {DECK_B_COLOR}; border: 1px solid {DECK_B_COLOR}; font-weight: bold; padding: 8px 14px;"
        )
        self.btn_deck_b.clicked.connect(lambda: self._load_selected("DECK_B"))
        btn_row.addWidget(self.btn_deck_b)

        self.btn_queue = QPushButton("Add to DJ Deck Queue")
        self.btn_queue.setStyleSheet(
            f"background-color: #1f2937; color: #ffffff; border: 1px solid {PANEL_BORDER}; padding: 8px 14px;"
        )
        self.btn_queue.clicked.connect(lambda: self._load_selected("QUEUE"))
        btn_row.addWidget(self.btn_queue)

        # Dev View remove action
        self.btn_remove = QPushButton("🗑 Remove from Playlist")
        self.btn_remove.setStyleSheet(
            "background-color: rgba(255,51,102,0.18); color: #ff4d6d; "
            "border: 1px solid #ff3366; font-weight: bold; padding: 8px 14px;"
        )
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self.btn_remove)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        layout.addLayout(btn_row)

    def _on_auto_check_changed(self, state: int):
        if state == 2:
            self.poll_timer.start(8000)
            self._fetch_playlist()
        else:
            self.poll_timer.stop()

    def _fetch_playlist(self):
        url = self.url_input.text().strip() or DEFAULT_ENDPOINT
        self.status_lbl.setText("Connecting to web playlist...")
        self.btn_fetch.setEnabled(False)

        self._fetch_worker = FetchWebQueueWorker(url)
        self._fetch_worker.finished_signal.connect(self._on_fetch_success)
        self._fetch_worker.error_signal.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_success(self, tracks: list):
        self.btn_fetch.setEnabled(True)
        self.tracks = tracks
        self.table.setRowCount(len(tracks))

        for row, trk in enumerate(tracks):
            def cell(text: str, center: bool = False) -> QTableWidgetItem:
                item = QTableWidgetItem(str(text))
                if center:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            self.table.setItem(row, 0, cell(row + 1, center=True))
            self.table.setItem(row, 1, cell(trk.get("title", "Unknown")))
            self.table.setItem(row, 2, cell(trk.get("artist", "Unknown")))
            self.table.setItem(row, 3, cell(str(trk.get("upvotes", 0)), center=True))

        msg = f"✓ {len(tracks)} track(s) in web playlist."
        self.status_lbl.setText(msg)

    def _on_fetch_error(self, err: str):
        self.btn_fetch.setEnabled(True)
        first_line = err.splitlines()[0]
        self.status_lbl.setText(f"Sync error: {first_line}")
        QMessageBox.warning(self, "Sync Error", err)

    def _load_selected(self, target: str):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.tracks):
            QMessageBox.information(self, "Select a Track", "Please select a track from the playlist first.")
            return
        trk = self.tracks[row]
        url = trk.get("url", "")
        if not url:
            QMessageBox.warning(self, "No URL", f"Track '{trk.get('title')}' has no streamable URL.")
            return
        self.queue_widget._start_ingestion(url, is_youtube=True, target_action=target)
        self.status_lbl.setText(f"Loading '{trk.get('title')}' into {target}...")

    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.tracks):
            QMessageBox.information(self, "Select a Track", "Please select a track to remove.")
            return
        trk = self.tracks[row]
        title = trk.get("title", "Track")
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove '{title}' from the web playlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        url = self.url_input.text().strip() or DEFAULT_ENDPOINT
        self.btn_remove.setEnabled(False)
        self.status_lbl.setText(f"Removing '{title}' from web playlist...")

        self._remove_worker = RemoveWebTrackWorker(url, trk.get("id", ""))
        self._remove_worker.finished_signal.connect(self._on_remove_done)
        self._remove_worker.start()

    def _on_remove_done(self, success: bool, msg: str):
        self.btn_remove.setEnabled(True)
        self.status_lbl.setText(msg)
        if success:
            self._fetch_playlist()
        else:
            QMessageBox.warning(self, "Remove Failed", msg)
