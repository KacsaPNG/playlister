"""
Per-Deck DSP Filter Chain.
Integrates input gain staging, 3-Band Parametric EQ with kills and sweep filter,
algorithmic reverb, deck volume fader, and real-time stereo VU level metering.
"""
import numpy as np
from app.dsp.eq import ThreeBandEQ
from app.dsp.reverb import ReverbUnit


class DeckFilterChain:
    """
    Modular real-time DSP filter chain applied to each deck's audio output.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        self.eq = ThreeBandEQ(sample_rate)
        self.reverb = ReverbUnit(sample_rate)

        # Gain staging
        self._input_gain_db = 0.0
        self._auto_gain_db = 0.0
        self._volume = 1.0  # 0.0 to 1.0 (Deck fader)
        self._is_muted = False

        # Real-time VU metering outputs [peak_L, peak_R, rms_L, rms_R] in [0.0, 1.0]
        self.peak_levels = np.zeros(2, dtype=np.float32)
        self.rms_levels = np.zeros(2, dtype=np.float32)

    def reset_state(self):
        """Reset internal filter memory and delay lines."""
        self.eq.reset_state()
        self.reverb.reset_state()
        self.peak_levels.fill(0)
        self.rms_levels.fill(0)

    @property
    def input_gain_db(self) -> float:
        return self._input_gain_db

    @input_gain_db.setter
    def input_gain_db(self, db: float):
        self._input_gain_db = float(np.clip(db, -24.0, 12.0))

    @property
    def auto_gain_db(self) -> float:
        return self._auto_gain_db

    @auto_gain_db.setter
    def auto_gain_db(self, db: float):
        self._auto_gain_db = float(np.clip(db, -24.0, 18.0))

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, vol: float):
        self._volume = float(np.clip(vol, 0.0, 1.0))

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    @is_muted.setter
    def is_muted(self, muted: bool):
        self._is_muted = bool(muted)

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Execute full DSP processing pipeline on input block (N, 2).
        1. Input Gain + Auto-Gain
        2. 3-Band Parametric EQ & Sweep Filter
        3. Algorithmic Reverb
        4. Deck Volume Fader
        5. VU Metering
        """
        if x.shape[0] == 0:
            return x

        # 1. Gain staging: combine trim gain and auto-gain offset
        total_gain_db = self._input_gain_db + self._auto_gain_db
        if abs(total_gain_db) > 0.05:
            gain_linear = 10.0 ** (total_gain_db / 20.0)
            out = x * gain_linear
        else:
            out = x.copy()

        # 2. 3-Band Parametric EQ and DJ Sweep Filter
        out = self.eq.process(out)

        # 3. Algorithmic Reverb
        out = self.reverb.process(out)

        # 4. Deck Volume Fader
        if self._is_muted:
            out = np.zeros_like(out)
        elif abs(self._volume - 1.0) > 0.01:
            out *= self._volume

        # 5. Measure Peak & RMS for stereo visual VU meters
        if out.shape[0] > 0:
            self.peak_levels[0] = float(np.max(np.abs(out[:, 0])))
            self.peak_levels[1] = float(np.max(np.abs(out[:, 1])))
            self.rms_levels[0] = float(np.sqrt(np.mean(out[:, 0] ** 2) + 1e-12))
            self.rms_levels[1] = float(np.sqrt(np.mean(out[:, 1] ** 2) + 1e-12))

        return out
