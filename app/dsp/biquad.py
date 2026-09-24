"""
Biquad Filter Implementation using Audio EQ Cookbook Formulas.
Direct Form II Transposed block filtering using scipy.signal.lfilter with persistent state.
"""
import numpy as np
from scipy import signal


class BiquadFilter:
    """
    Second-order IIR (Biquad) filter with persistent internal state across blocks.
    Supports Low-Shelf, High-Shelf, Peaking, Low-Pass, and High-Pass filters.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        # Normalized coefficients [b0, b1, b2, a0, a1, a2]
        self.b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        # Persistent filter state for stereo [2 channels, 2 delays]
        self.zi = np.zeros((2, 2), dtype=np.float32)
        self.is_bypass = True

    def reset_state(self):
        """Reset internal filter delay memory."""
        self.zi = np.zeros((2, 2), dtype=np.float32)

    def set_low_shelf(self, f0: float, gain_db: float, s: float = 1.0):
        """
        Configure as Low-Shelf filter.
        f0: cutoff frequency in Hz
        gain_db: boost/cut in dB
        s: shelf slope parameter (default 1.0)
        """
        if abs(gain_db) < 0.05:
            self.is_bypass = True
            return

        self.is_bypass = False
        f0 = max(10.0, min(f0, self.sample_rate * 0.49))
        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * f0 / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / s - 1.0) + 2.0)
        two_sqrt_a_alpha = 2.0 * np.sqrt(A) * alpha

        b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + two_sqrt_a_alpha)
        b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - two_sqrt_a_alpha)
        a0 = (A + 1.0) + (A - 1.0) * cos_w0 + two_sqrt_a_alpha
        a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
        a2 = (A + 1.0) + (A - 1.0) * cos_w0 - two_sqrt_a_alpha

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    def set_high_shelf(self, f0: float, gain_db: float, s: float = 1.0):
        """
        Configure as High-Shelf filter.
        f0: cutoff frequency in Hz
        gain_db: boost/cut in dB
        s: shelf slope parameter (default 1.0)
        """
        if abs(gain_db) < 0.05:
            self.is_bypass = True
            return

        self.is_bypass = False
        f0 = max(10.0, min(f0, self.sample_rate * 0.49))
        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * f0 / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / s - 1.0) + 2.0)
        two_sqrt_a_alpha = 2.0 * np.sqrt(A) * alpha

        b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + two_sqrt_a_alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - two_sqrt_a_alpha)
        a0 = (A + 1.0) - (A - 1.0) * cos_w0 + two_sqrt_a_alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
        a2 = (A + 1.0) - (A - 1.0) * cos_w0 - two_sqrt_a_alpha

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    def set_peaking(self, f0: float, gain_db: float, q: float = 1.0):
        """
        Configure as Peaking (Parametric Bell) filter.
        f0: center frequency in Hz
        gain_db: boost/cut in dB
        q: resonance / quality factor (default 1.0)
        """
        if abs(gain_db) < 0.05:
            self.is_bypass = True
            return

        self.is_bypass = False
        f0 = max(10.0, min(f0, self.sample_rate * 0.49))
        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * f0 / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2.0 * q)

        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w0
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha / A

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    def set_low_pass(self, f0: float, q: float = 0.707):
        """Configure as 2nd-order resonant Low-Pass filter."""
        f0 = max(10.0, min(f0, self.sample_rate * 0.49))
        w0 = 2.0 * np.pi * f0 / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2.0 * q)

        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = (1.0 - cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)
        self.is_bypass = False

    def set_high_pass(self, f0: float, q: float = 0.707):
        """Configure as 2nd-order resonant High-Pass filter."""
        f0 = max(10.0, min(f0, self.sample_rate * 0.49))
        w0 = 2.0 * np.pi * f0 / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2.0 * q)

        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        self.b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)
        self.is_bypass = False

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Process a stereo block x with shape (N, 2).
        Maintains filter delay line state seamlessly across consecutive blocks.
        """
        if self.is_bypass or x.shape[0] == 0:
            return x

        # Process channel 0 (Left) and channel 1 (Right)
        # Using signal.lfilter with persistent zi
        out = np.empty_like(x)
        out[:, 0], self.zi[0] = signal.lfilter(self.b, self.a, x[:, 0], zi=self.zi[0])
        out[:, 1], self.zi[1] = signal.lfilter(self.b, self.a, x[:, 1], zi=self.zi[1])
        return out
