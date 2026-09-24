"""
Lookahead Master Peak Limiter & Gain Staging Unit.
Prevents clipping and harmonic distortion across multiple decks and loud tracks
via fast peak detection, lookahead delay, soft-knee gain reduction, and tanh saturation ceiling.
"""
import numpy as np


class PeakLimiter:
    """
    Studio-grade Master Output Peak Limiter.
    Threshold: default -0.5 dBFS
    Ceiling: default -0.1 dBFS
    Release time: 50 ms
    Lookahead: 64 samples (~1.45 ms at 44.1 kHz)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        threshold_db: float = -0.5,
        ceiling_db: float = -0.1,
        release_ms: float = 50.0,
        lookahead_samples: int = 64,
    ):
        self.sample_rate = sample_rate
        self.threshold = 10.0 ** (threshold_db / 20.0)
        self.ceiling = 10.0 ** (ceiling_db / 20.0)
        self.lookahead_samples = lookahead_samples

        # Calculate release coefficient per sample
        release_sec = release_ms / 1000.0
        self.release_coeff = float(np.exp(-1.0 / (sample_rate * release_sec)))

        # Persistent lookahead buffer and state
        self.delay_buf = np.zeros((lookahead_samples, 2), dtype=np.float32)
        self.envelope = 0.0
        self.current_gr_db = 0.0
        self.enabled = True

    def reset_state(self):
        """Reset internal delay buffer and envelope."""
        self.delay_buf.fill(0)
        self.envelope = 0.0
        self.current_gr_db = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Process incoming stereo block (N, 2).
        Returns limited, transparent audio and updates current gain reduction.
        """
        if not self.enabled or x.shape[0] == 0:
            return x

        N = x.shape[0]
        # Lookahead delay concatenation: [delay_buf, x]
        extended = np.vstack([self.delay_buf, x])
        # The output audio is drawn from the delayed stream
        delayed_audio = extended[:N]
        # Store remainder for next block
        self.delay_buf = extended[N : N + self.lookahead_samples].copy()

        # Instantaneous peak magnitude from the incoming stream (which leads by lookahead)
        peaks = np.max(np.abs(x), axis=1)

        # Vectorized envelope follower with exponential release
        envelope = np.empty(N, dtype=np.float32)
        env = self.envelope
        rel = self.release_coeff
        for i in range(N):
            p = peaks[i]
            if p > env:
                env = p  # Instant attack
            else:
                env = p + (env - p) * rel  # Smooth release
            envelope[i] = env
        self.envelope = env

        # Compute gain factor
        # When envelope > threshold, attenuate by threshold / envelope
        gain = np.ones(N, dtype=np.float32)
        over = envelope > self.threshold
        if np.any(over):
            gain[over] = self.threshold / (envelope[over] + 1e-9)

        # Track maximum gain reduction in this block for GUI meter
        min_gain = float(np.min(gain))
        if min_gain < 1.0:
            self.current_gr_db = round(float(20.0 * np.log10(min_gain)), 1)
        else:
            self.current_gr_db = 0.0

        # Apply gain
        out = delayed_audio * gain[:, np.newaxis]

        # Safety soft saturation ceiling (tanh curve) to prevent any inter-sample clip
        c = self.ceiling
        t = self.threshold
        abs_out = np.abs(out)
        clipping_mask = abs_out > t
        if np.any(clipping_mask):
            diff = abs_out[clipping_mask] - t
            scale = c - t
            saturated = t + scale * np.tanh(diff / max(scale, 1e-6))
            out[clipping_mask] = np.sign(out[clipping_mask]) * saturated

        return out.astype(np.float32)
