"""
Crossfading Engine and Auto-DJ Automated Mixing Algorithm.
Supports Equal-Power (Log/Cos), Linear, and Cut crossfade curves,
plus automated track transition triggering when remaining playback time reaches threshold.
"""
import time
from typing import Optional
import numpy as np
from app.config import (
    CrossfadeCurve,
    DEFAULT_CROSSFADE_SECONDS,
    MIN_CROSSFADE_SECONDS,
    MAX_CROSSFADE_SECONDS,
)


class Crossfader:
    """
    DJ Mixer Crossfader and Auto-DJ Crossfade Controller.
    Position ranges from -1.0 (100% Deck A) to +1.0 (100% Deck B).
    """

    def __init__(self, curve: CrossfadeCurve = CrossfadeCurve.EQUAL_POWER):
        self.curve = curve
        self._position: float = -1.0  # -1.0 = Deck A, 0.0 = Center, +1.0 = Deck B

        # Auto-DJ transition state
        self.auto_dj_enabled: bool = True
        self.crossfade_duration: float = DEFAULT_CROSSFADE_SECONDS
        self._is_transitioning: bool = False
        self._transition_start_time: float = 0.0
        self._transition_start_pos: float = -1.0
        self._transition_target_pos: float = 1.0

    @property
    def position(self) -> float:
        return self._position

    @position.setter
    def position(self, val: float):
        self._position = float(np.clip(val, -1.0, 1.0))

    def set_duration(self, seconds: float):
        """Set auto crossfade duration (clamped between MIN and MAX)."""
        self.crossfade_duration = float(np.clip(seconds, MIN_CROSSFADE_SECONDS, MAX_CROSSFADE_SECONDS))

    def get_gains(self) -> tuple[float, float]:
        """
        Calculate (gain_A, gain_B) based on selected crossfader curve.
        """
        # Normalize position to [0.0, 1.0] where 0.0 is Deck A and 1.0 is Deck B
        t = (self._position + 1.0) / 2.0

        if self.curve == CrossfadeCurve.EQUAL_POWER:
            # Constant power: gain_A^2 + gain_B^2 = 1.0
            angle = t * (np.pi / 2.0)
            gain_A = float(np.cos(angle))
            gain_B = float(np.sin(angle))

        elif self.curve == CrossfadeCurve.LINEAR:
            # Linear curve (drops -3dB in center)
            gain_A = float(1.0 - t)
            gain_B = float(t)

        elif self.curve == CrossfadeCurve.LOGARITHMIC:
            # Perceptual logarithmic curve
            gain_A = float(np.sqrt(max(0.0, 1.0 - t)))
            gain_B = float(np.sqrt(max(0.0, t)))

        elif self.curve == CrossfadeCurve.SMOOTH_STEP:
            # Hermite smoothstep curve: 3t^2 - 2t^3
            s = t * t * (3.0 - 2.0 * t)
            gain_A = float(1.0 - s)
            gain_B = float(s)

        else:
            gain_A = float(np.cos(t * np.pi / 2.0))
            gain_B = float(np.sin(t * np.pi / 2.0))

        return gain_A, gain_B

    def start_auto_transition(self, target_deck: str, duration: Optional[float] = None):
        """
        Initiate smooth automated crossfade toward target_deck ('A' or 'B').
        Optionally override duration with musical/beat-synced duration.
        """
        self._transition_start_time = time.time()
        self._transition_start_pos = self._position
        self._transition_target_pos = -1.0 if target_deck == "A" else 1.0
        self._transition_elapsed_sec = 0.0
        self._transition_active_duration = float(duration) if (duration is not None and duration > 0.05) else self.crossfade_duration
        self._is_transitioning = True

    def update_auto_transition(self, frames: int = 0, sample_rate: int = 44100) -> bool:
        """
        Update position if an automated transition is running.
        Can advance either by rendered audio frames or wall-clock time.
        Returns True while transitioning, False when transition finishes.
        """
        if not self._is_transitioning:
            return False

        if frames > 0 and sample_rate > 0:
            delta_sec = frames / float(sample_rate)
            self._transition_elapsed_sec += delta_sec
            elapsed = self._transition_elapsed_sec
        else:
            elapsed = time.time() - self._transition_start_time

        active_dur = getattr(self, "_transition_active_duration", self.crossfade_duration)
        progress = elapsed / max(0.1, active_dur)

        if progress >= 1.0:
            self._position = self._transition_target_pos
            self._is_transitioning = False
            return False

        # Smooth ease-in-out cosine interpolation for automated slider animation
        smooth_progress = 0.5 * (1.0 - np.cos(progress * np.pi))
        self._position = float(
            self._transition_start_pos
            + (self._transition_target_pos - self._transition_start_pos) * smooth_progress
        )
        return True

    @property
    def is_transitioning(self) -> bool:
        return self._is_transitioning
