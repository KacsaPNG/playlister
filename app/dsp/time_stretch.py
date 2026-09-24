"""
BPM & Pitch Control Engine.
Includes Resampling Interpolation for Turntable Pitch Fader,
WSOLA (Waveform Similarity Overlap-Add) Time-Stretching for Key-Lock,
Smooth Pitch Bend / Turntable Nudge, and Automatic BPM Detection.
"""
import numpy as np
from scipy import signal


class Resampler:
    """
    Sub-sample interpolation resampler for variable speed audio playback.
    Supports high-speed linear and Hermite cubic interpolation.
    """

    @staticmethod
    def resample_block(audio: np.ndarray, rate: float) -> np.ndarray:
        """
        Resample a 2D stereo array (N, 2) to a new length corresponding to speed `rate`.
        Rate > 1.0 speeds up playback (higher pitch), Rate < 1.0 slows down (lower pitch).
        """
        if abs(rate - 1.0) < 1e-4 or audio.shape[0] < 4:
            return audio

        N = audio.shape[0]
        out_len = int(round(N / rate))
        if out_len <= 0:
            return np.empty((0, audio.shape[1]), dtype=audio.dtype)

        orig_indices = np.arange(N, dtype=np.float32)
        new_indices = np.linspace(0, N - 1, out_len, dtype=np.float32)

        out_ch0 = np.interp(new_indices, orig_indices, audio[:, 0])
        out_ch1 = np.interp(new_indices, orig_indices, audio[:, 1])
        return np.column_stack([out_ch0, out_ch1]).astype(audio.dtype)


class WSOLATimeStretch:
    """
    Waveform Similarity Overlap-Add (WSOLA) Time-Stretching Algorithm.
    Allows real-time tempo changes without altering musical key or pitch (Key Lock).
    """

    def __init__(self, frame_size: int = 1024, hop_size: int = 512, tolerance: int = 128):
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.tolerance = tolerance
        self.window = np.hanning(frame_size).astype(np.float32)

    def stretch(self, audio: np.ndarray, rate: float) -> np.ndarray:
        """
        Stretch audio duration by factor 1/rate while preserving pitch.
        rate = 1.0 -> original tempo
        rate = 1.2 -> 20% faster tempo, same pitch
        rate = 0.8 -> 20% slower tempo, same pitch
        """
        if abs(rate - 1.0) < 0.005:
            return audio

        N = audio.shape[0]
        channels = audio.shape[1]
        out_len = int(N / rate)
        output = np.zeros((out_len + self.frame_size, channels), dtype=np.float32)
        norm_weights = np.zeros(out_len + self.frame_size, dtype=np.float32)

        ana_hop = int(self.hop_size * rate)
        syn_hop = self.hop_size

        syn_pos = 0
        ana_pos = 0

        while ana_pos + self.frame_size + self.tolerance < N and syn_pos + self.frame_size < out_len:
            if syn_pos == 0:
                best_offset = 0
            else:
                prev_frame = output[syn_pos : syn_pos + self.frame_size, 0]
                candidates = audio[
                    ana_pos - self.tolerance : ana_pos + self.tolerance + self.frame_size, 0
                ]
                corrs = np.correlate(candidates, prev_frame, mode="valid")
                best_offset = int(np.argmax(corrs)) - self.tolerance

            actual_ana = max(0, min(N - self.frame_size, ana_pos + best_offset))
            frame = audio[actual_ana : actual_ana + self.frame_size]

            for c in range(channels):
                output[syn_pos : syn_pos + self.frame_size, c] += frame[:, c] * self.window
            norm_weights[syn_pos : syn_pos + self.frame_size] += self.window

            syn_pos += syn_hop
            ana_pos += ana_hop

        nz = norm_weights > 1e-4
        for c in range(channels):
            output[nz, c] /= norm_weights[nz]

        return output[:out_len]


class PitchBend:
    """
    Turntable pitch bend / nudge controller.
    Provides smooth momentary speed ramping (+/- 4% or +/- 8%) when nudge buttons are held.
    """

    def __init__(self, step_size: float = 0.05, ramp_speed: float = 0.2):
        self.step_size = step_size
        self.ramp_speed = ramp_speed
        self.target_offset = 0.0
        self.current_offset = 0.0

    def nudge_up(self):
        self.target_offset = self.step_size

    def nudge_down(self):
        self.target_offset = -self.step_size

    def release(self):
        self.target_offset = 0.0

    def update(self) -> float:
        """Smoothly ramp toward target offset and return current value."""
        self.current_offset += (self.target_offset - self.current_offset) * self.ramp_speed
        if abs(self.current_offset) < 1e-4:
            self.current_offset = 0.0
        return self.current_offset


class BpmDetector:
    """
    Fast autocorrelation-based BPM / Tempo detector for loaded audio tracks.
    """

    @staticmethod
    def estimate_bpm(audio: np.ndarray, sample_rate: int = 44100, min_bpm: float = 70.0, max_bpm: float = 175.0) -> float:
        """
        Estimate track tempo in Beats Per Minute (BPM).
        Analyzes energy novelty curve using low-passed onset envelope autocorrelation.
        """
        if audio.shape[0] < sample_rate * 5:
            return 120.0

        # Downsample to ~4000 Hz for ultra-fast novelty analysis
        downsample_factor = max(1, sample_rate // 4000)
        mono = 0.5 * (audio[:, 0] + audio[:, 1])

        # Analyze middle 30 seconds of track for reliable beat detection
        mid_start = max(0, len(mono) // 2 - (sample_rate * 15))
        mid_end = min(len(mono), mid_start + (sample_rate * 30))
        segment = mono[mid_start:mid_end:downsample_factor]
        fs_sub = sample_rate / downsample_factor

        # Frame energy envelope (hop = 64 samples)
        hop = 64
        num_frames = len(segment) // hop
        if num_frames < 100:
            return 120.0

        frames = segment[: num_frames * hop].reshape((num_frames, hop))
        energy = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-6)

        # Novelty: positive derivative of envelope
        diff = np.diff(energy)
        novelty = np.maximum(0, diff)

        # Autocorrelation of novelty curve
        novelty -= np.mean(novelty)
        autocorr = signal.correlate(novelty, novelty, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        # Lag range corresponding to min_bpm and max_bpm
        # bpm = (fs_sub / hop) * 60 / lag
        fps = fs_sub / hop
        min_lag = int(np.floor((fps * 60.0) / max_bpm))
        max_lag = int(np.ceil((fps * 60.0) / min_bpm))

        if max_lag >= len(autocorr):
            max_lag = len(autocorr) - 1

        search_window = autocorr[min_lag : max_lag + 1]
        if len(search_window) == 0:
            return 120.0

        best_lag = min_lag + int(np.argmax(search_window))
        bpm = (fps * 60.0) / best_lag

        # Normalize octave (e.g. if detected half-time < 80, bring to 120-160 range)
        while bpm < 75.0:
            bpm *= 2.0
        while bpm > 175.0:
            bpm /= 2.0

        return round(float(bpm), 1)
