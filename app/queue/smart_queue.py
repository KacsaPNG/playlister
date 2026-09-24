"""
Dynamic Playlist Queue with Alternating Deck Routing.
Automatically distributes incoming tracks alternately between Deck A and Deck B
and supplies preloaded tracks to the idle deck during auto-crossfade transitions.
"""
from dataclasses import dataclass
from enum import Enum
import threading
from typing import Optional, List, Callable
from app.audio.buffer import AudioTrack
from app.config import DeckId


class QueueStatus(str, Enum):
    QUEUED = "Queued"
    LOADED_A = "Loaded (Deck A)"
    LOADED_B = "Loaded (Deck B)"
    PLAYING = "Playing"
    PLAYED = "Played"


@dataclass
class QueueItem:
    track: AudioTrack
    target_deck: str  # "A" or "B"
    status: QueueStatus = QueueStatus.QUEUED


class SmartQueue:
    """
    Dynamic playlist queue that routes alternating track selections between Deck A and Deck B.
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.items: List[QueueItem] = []
        self._last_assigned_deck: str = "B"  # So first track routes to "A"
        self._on_queue_changed_callbacks: List[Callable[[], None]] = []

    def add_change_listener(self, callback: Callable[[], None]):
        self._on_queue_changed_callbacks.append(callback)

    def _notify(self):
        for cb in self._on_queue_changed_callbacks:
            try:
                cb()
            except Exception:
                pass

    def add_track(self, track: AudioTrack, target_deck: Optional[str] = None) -> QueueItem:
        """
        Add a track to the smart queue.
        If target_deck is not explicitly provided, alternates automatically between Deck A and B.
        """
        with self.lock:
            if not target_deck:
                # Alternate deck routing
                target_deck = "A" if self._last_assigned_deck == "B" else "B"
                self._last_assigned_deck = target_deck

            item = QueueItem(track=track, target_deck=target_deck, status=QueueStatus.QUEUED)
            self.items.append(item)
            self._notify()
            return item

    def get_next_for_deck(self, deck_id: str) -> Optional[AudioTrack]:
        """
        Retrieve and reserve the next queued track designated for the specified deck.
        """
        with self.lock:
            for item in self.items:
                if item.status == QueueStatus.QUEUED and item.target_deck == deck_id:
                    item.status = QueueStatus.LOADED_A if deck_id == "A" else QueueStatus.LOADED_B
                    self._notify()
                    return item.track

            # Fallback: if no track is explicitly assigned to deck_id, pick first QUEUED track
            for item in self.items:
                if item.status == QueueStatus.QUEUED:
                    item.target_deck = deck_id
                    item.status = QueueStatus.LOADED_A if deck_id == "A" else QueueStatus.LOADED_B
                    self._notify()
                    return item.track

            return None

    def mark_playing(self, track_id: str):
        with self.lock:
            for item in self.items:
                if item.track.metadata.id == track_id:
                    item.status = QueueStatus.PLAYING
            self._notify()

    def mark_played(self, track_id: str):
        with self.lock:
            for item in self.items:
                if item.track.metadata.id == track_id:
                    item.status = QueueStatus.PLAYED
            self._notify()

    def remove_index(self, index: int):
        with self.lock:
            if 0 <= index < len(self.items):
                del self.items[index]
                self._notify()

    def clear(self):
        with self.lock:
            self.items.clear()
            self._notify()

    def __len__(self):
        with self.lock:
            return len(self.items)
