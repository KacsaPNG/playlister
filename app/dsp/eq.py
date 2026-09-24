"""
3-Band Parametric EQ and DJ Sweep Filter.
Features Low-Shelf (250 Hz), Mid Peaking (1 kHz), High-Shelf (4 kHz),
dedicated band kill toggles, and dual Low-Pass / High-Pass sweep filter.
"""
import numpy as np
from app.dsp.biquad import BiquadFilter


class ThreeBandEQ:
    """
    Studio-grade 3-Band Parametric EQ + DJ Filter Unit for DJ Decks.
    Frequencies tuned for standard DJ mixers:
      - Low Band: 250 Hz (Low Shelf, Bass & Kick)
      - Mid Band: 1000 Hz (Peaking Bell, Vocals & Synths)
      - High Band: 4000 Hz (High Shelf, Cymbals, Hi-hats & Air)
    Gain range: -24 dB to +12 dB, with instantaneous -60 dB Kill Switches.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        self.low_filter = BiquadFilter(sample_rate)
        self.mid_filter = BiquadFilter(sample_rate)
        self.high_filter = BiquadFilter(sample_rate)
        self.sweep_filter = BiquadFilter(sample_rate)

        # Gains in dB (-24.0 to +12.0)
        self._low_gain = 0.0
        self._mid_gain = 0.0
        self._high_gain = 0.0

        # Kill toggles
        self._low_kill = False
        self._mid_kill = False
        self._high_kill = False

        # Filter knob: -1.0 (LPF) to 0.0 (Bypass) to +1.0 (HPF)
        self._filter_val = 0.0

        self._update_low()
        self._update_mid()
        self._update_high()
        self._update_sweep()

    def reset_state(self):
        """Reset delay lines to eliminate residual ring."""
        self.low_filter.reset_state()
        self.mid_filter.reset_state()
        self.high_filter.reset_state()
        self.sweep_filter.reset_state()

    def reset_defaults(self):
        """Reset gains, kill switches, and sweep filter back to neutral defaults."""
        self._low_gain = 0.0
        self._mid_gain = 0.0
        self._high_gain = 0.0
        self._low_kill = False
        self._mid_kill = False
        self._high_kill = False
        self._filter_val = 0.0
        self._update_low()
        self._update_mid()
        self._update_high()
        self._update_sweep()
        self.reset_state()

    # Low Band
    @property
    def low_gain(self) -> float:
        return self._low_gain

    @low_gain.setter
    def low_gain(self, db: float):
        self._low_gain = float(np.clip(db, -24.0, 12.0))
        self._update_low()

    @property
    def low_kill(self) -> bool:
        return self._low_kill

    @low_kill.setter
    def low_kill(self, kill: bool):
        self._low_kill = bool(kill)
        self._update_low()

    def _update_low(self):
        gain = -60.0 if self._low_kill else self._low_gain
        self.low_filter.set_low_shelf(f0=250.0, gain_db=gain, s=1.0)

    # Mid Band
    @property
    def mid_gain(self) -> float:
        return self._mid_gain

    @mid_gain.setter
    def mid_gain(self, db: float):
        self._mid_gain = float(np.clip(db, -24.0, 12.0))
        self._update_mid()

    @property
    def mid_kill(self) -> bool:
        return self._mid_kill

    @mid_kill.setter
    def mid_kill(self, kill: bool):
        self._mid_kill = bool(kill)
        self._update_mid()

    def _update_mid(self):
        gain = -60.0 if self._mid_kill else self._mid_gain
        self.mid_filter.set_peaking(f0=1000.0, gain_db=gain, q=1.0)

    # High Band
    @property
    def high_gain(self) -> float:
        return self._high_gain

    @high_gain.setter
    def high_gain(self, db: float):
        self._high_gain = float(np.clip(db, -24.0, 12.0))
        self._update_high()

    @property
    def high_kill(self) -> bool:
        return self._high_kill

    @high_kill.setter
    def high_kill(self, kill: bool):
        self._high_kill = bool(kill)
        self._update_high()

    def _update_high(self):
        gain = -60.0 if self._high_kill else self._high_gain
        self.high_filter.set_high_shelf(f0=4000.0, gain_db=gain, s=1.0)

    # DJ Sweep Filter
    @property
    def filter_knob(self) -> float:
        return self._filter_val

    @filter_knob.setter
    def filter_knob(self, val: float):
        """Value from -1.0 (Low-Pass sweep) to 0.0 (Off) to +1.0 (High-Pass sweep)."""
        self._filter_val = float(np.clip(val, -1.0, 1.0))
        self._update_sweep()

    def _update_sweep(self):
        val = self._filter_val
        if abs(val) < 0.02:
            self.sweep_filter.is_bypass = True
        elif val < 0:
            # Low-Pass filter from 20000 Hz down to 60 Hz exponentially
            # val is [-1.0, 0.0]
            t = (val + 1.0)  # [0.0 to 1.0]
            cutoff = 60.0 * ((20000.0 / 60.0) ** t)
            self.sweep_filter.set_low_pass(f0=cutoff, q=1.0)
        else:
            # High-Pass filter from 20 Hz up to 8000 Hz exponentially
            # val is [0.0, 1.0]
            cutoff = 20.0 * ((8000.0 / 20.0) ** val)
            self.sweep_filter.set_high_pass(f0=cutoff, q=1.0)

    def process(self, x: np.ndarray) -> np.ndarray:
        """Process a stereo audio block through the EQ and Sweep Filter cascade."""
        if x.shape[0] == 0:
            return x

        out = self.low_filter.process(x)
        out = self.mid_filter.process(out)
        out = self.high_filter.process(out)
        out = self.sweep_filter.process(out)
        return out
