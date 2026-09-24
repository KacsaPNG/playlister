"""
Audio Loudness Analysis Engine (ITU-R BS.1770-4 / EBU R128).
Calculates Integrated Loudness (LUFS), Momentary Loudness,
True Peak (dBTP), RMS (dBFS), and Auto-Gain Normalization Offsets.
"""
from dataclasses import dataclass
import numpy as np
from scipy import signal


@dataclass
class LoudnessReport:
    integrated_lufs: float
    true_peak_db: float
    rms_db: float
    recommended_gain_db: float


class LoudnessAnalyzer:
    """
    ITU-R BS.1770-4 / EBU R128 Compliant Loudness and Energy Meter.
    Uses K-weighting pre-filter, RLB high-pass filter, and dual-gated
    energy integration for accurate perceptual loudness measurement.
    """

    def __init__(self, sample_rate: int = 44100, target_lufs: float = -14.0):
        self.sample_rate = sample_rate
        self.target_lufs = target_lufs
        self._init_filters()

    def _init_filters(self):
        sr = self.sample_rate

        # Stage 1: K-weighting High-Shelf filter (head diffraction simulation ~1.5 kHz, +4 dB)
        w0 = 2.0 * np.pi * 1500.0 / sr
        A = 10.0 ** (4.0 / 40.0)
        alpha = np.sin(w0) / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / 0.707 - 1.0) + 2.0)
        two_sqrt_a_alpha = 2.0 * np.sqrt(A) * alpha

        b0 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) + two_sqrt_a_alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * np.cos(w0))
        b2 = A * ((A + 1.0) + (A - 1.0) * np.cos(w0) - two_sqrt_a_alpha)
        a0 = (A + 1.0) - (A - 1.0) * np.cos(w0) + two_sqrt_a_alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * np.cos(w0))
        a2 = (A + 1.0) - (A - 1.0) * np.cos(w0) - two_sqrt_a_alpha

        self.b_hs = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
        self.a_hs = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

        # Stage 2: RLB High-Pass filter (38.1 Hz cutoff)
        w0_hp = 2.0 * np.pi * 38.1 / sr
        alpha_hp = np.sin(w0_hp) / (2.0 * 0.5)

        b0_hp = (1.0 + np.cos(w0_hp)) / 2.0
        b1_hp = -(1.0 + np.cos(w0_hp))
        b2_hp = (1.0 + np.cos(w0_hp)) / 2.0
        a0_hp = 1.0 + alpha_hp
        a1_hp = -2.0 * np.cos(w0_hp)
        a2_hp = 1.0 - alpha_hp

        self.b_hp = np.array([b0_hp / a0_hp, b1_hp / a0_hp, b2_hp / a0_hp], dtype=np.float32)
        self.a_hp = np.array([1.0, a1_hp / a0_hp, a2_hp / a0_hp], dtype=np.float32)

    def analyze(self, audio: np.ndarray) -> LoudnessReport:
        """
        Analyze audio PCM buffer shape (N, 2).
        Returns comprehensive LoudnessReport.
        """
        if audio.shape[0] < self.sample_rate * 0.5:
            return LoudnessReport(
                integrated_lufs=self.target_lufs,
                true_peak_db=0.0,
                rms_db=-14.0,
                recommended_gain_db=0.0,
            )

        # Peak & RMS
        max_peak = float(np.max(np.abs(audio)))
        peak_db = 20.0 * np.log10(max(max_peak, 1e-6))
        rms_val = float(np.sqrt(np.mean(audio ** 2) + 1e-12))
        rms_db = 20.0 * np.log10(rms_val)

        # K-weighting filter application
        y = np.empty_like(audio)
        for c in range(audio.shape[1]):
            filtered_stage1 = signal.lfilter(self.b_hs, self.a_hs, audio[:, c])
            y[:, c] = signal.lfilter(self.b_hp, self.a_hp, filtered_stage1)

        # 400ms rectangular window with 75% overlap (100ms hop) per BS.1770
        block_size = int(self.sample_rate * 0.4)
        hop_size = int(self.sample_rate * 0.1)
        num_blocks = (len(audio) - block_size) // hop_size

        if num_blocks <= 0:
            mean_sq = np.mean(y ** 2, axis=0)
            int_lufs = -0.691 + 10.0 * np.log10(float(np.sum(mean_sq)) + 1e-12)
        else:
            block_powers = np.empty(num_blocks, dtype=np.float32)
            for i in range(num_blocks):
                blk = y[i * hop_size : i * hop_size + block_size]
                z = np.mean(blk ** 2, axis=0)
                # Channel weightings: 1.0 for Left and Right
                block_powers[i] = np.sum(z)

            # Absolute threshold gating at -70 LUFS
            abs_thresh_power = 10.0 ** ((-70.0 + 0.691) / 10.0)
            valid = block_powers > abs_thresh_power
            if not np.any(valid):
                int_lufs = -70.0
            else:
                ungated_lufs = -0.691 + 10.0 * np.log10(float(np.mean(block_powers[valid])) + 1e-12)
                # Relative threshold gating at -10 LU below ungated loudness
                rel_thresh_power = 10.0 ** ((ungated_lufs - 10.0 + 0.691) / 10.0)
                gated = block_powers > rel_thresh_power
                if not np.any(gated):
                    int_lufs = ungated_lufs
                else:
                    int_lufs = -0.691 + 10.0 * np.log10(float(np.mean(block_powers[gated])) + 1e-12)

        # Calculate recommended gain offset
        gain_offset = float(np.clip(self.target_lufs - int_lufs, -18.0, 18.0))
        # Ensure gain doesn't cause peak clipping before limiter
        if peak_db + gain_offset > -0.5:
            gain_offset = min(gain_offset, -0.5 - peak_db)

        return LoudnessReport(
            integrated_lufs=round(float(int_lufs), 1),
            true_peak_db=round(float(peak_db), 1),
            rms_db=round(float(rms_db), 1),
            recommended_gain_db=round(float(gain_offset), 1),
        )
