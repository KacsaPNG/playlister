"""
Application Configuration and Audio Constants for Standalone DJ Application.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_BLOCK_SIZE = 1024
CHANNELS = 2
DTYPE = "float32"

# Audio buffer configuration
MAX_BUFFER_SECONDS = 3600  # Up to 1 hour audio buffer per track
DEFAULT_CROSSFADE_SECONDS = 7.0  # Automatic crossfading duration (5 - 10 seconds)
MIN_CROSSFADE_SECONDS = 3.0
MAX_CROSSFADE_SECONDS = 15.0

# Loudness normalization target (ITU-R BS.1770 / EBU R128 standard)
TARGET_LUFS = -14.0
LIMITER_THRESHOLD_DB = -0.5
LIMITER_CEILING_DB = -0.1

# Cache directory for downloaded tracks
CACHE_DIR = Path(tempfile.gettempdir()) / "playlisterag_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class CrossfadeCurve(str, Enum):
    EQUAL_POWER = "Equal Power (Log/Cos)"
    LINEAR = "Linear"
    LOGARITHMIC = "Logarithmic"
    SMOOTH_STEP = "Smooth Step"

class PlaybackState(str, Enum):
    STOPPED = "STOPPED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    CUEING = "CUEING"

class DeckId(str, Enum):
    DECK_A = "A"
    DECK_B = "B"
