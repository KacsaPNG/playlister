"""
Audio Track Buffer and Metadata Models.
Thread-safe uncompressed 32-bit floating point PCM audio buffer,
cue point markers, and waveform peak summary generator for DJ visualizers.
"""
from dataclasses import dataclass, field
import uuid
import numpy as np


@dataclass
class TrackMetadata:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "Unknown Track"
    artist: str = "Unknown Artist"
    duration_sec: float = 0.0
    source_url: str = ""
    thumbnail_url: str = ""
    bpm: float = 120.0
    loudness_lufs: float = -14.0
    true_peak_db: float = 0.0
    auto_gain_db: float = 0.0


class AudioTrack:
    """
    In-memory uncompressed 32-bit float stereo PCM audio track.
    Provides fast sub-sample seeking, slicing, and waveform overview caching.
    """

    def __init__(self, pcm_data: np.ndarray, sample_rate: int = 44100, metadata: TrackMetadata = None):
        # Ensure 2D float32 stereo array (N, 2)
        if pcm_data.ndim == 1:
            self.pcm_data = np.column_stack([pcm_data, pcm_data]).astype(np.float32)
        elif pcm_data.shape[1] == 1:
            self.pcm_data = np.repeat(pcm_data, 2, axis=1).astype(np.float32)
        else:
            self.pcm_data = pcm_data[:, :2].astype(np.float32)

        self.sample_rate = sample_rate
        self.metadata = metadata or TrackMetadata()

        # Update duration in metadata
        self.total_samples = self.pcm_data.shape[0]
        self.duration_sec = self.total_samples / float(sample_rate)
        self.metadata.duration_sec = self.duration_sec

        # Cue point in samples (default 0)
        self.cue_point = 0

        # Cached waveform min/max peaks for high-speed UI rendering
        self._waveform_cache = None

    def get_slice(self, start_sample: int, num_samples: int) -> np.ndarray:
        """
        Extract a block of samples starting at start_sample.
        If out of bounds, pads with zeros.
        """
        if start_sample >= self.total_samples or start_sample + num_samples <= 0:
            return np.zeros((num_samples, 2), dtype=np.float32)

        end_sample = start_sample + num_samples

        pad_left = max(0, -start_sample)
        pad_right = max(0, end_sample - self.total_samples)

        valid_start = max(0, start_sample)
        valid_end = min(self.total_samples, end_sample)

        slice_data = self.pcm_data[valid_start:valid_end]

        if pad_left > 0 or pad_right > 0:
            parts = []
            if pad_left > 0:
                parts.append(np.zeros((pad_left, 2), dtype=np.float32))
            parts.append(slice_data)
            if pad_right > 0:
                parts.append(np.zeros((pad_right, 2), dtype=np.float32))
            return np.vstack(parts)

        return slice_data

    def get_waveform_peaks(self, num_bins: int = 800) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate or return cached min/max peak summary for waveform rendering.
        Returns (min_peaks, max_peaks) arrays of length num_bins.
        """
        if self._waveform_cache is not None and len(self._waveform_cache[0]) == num_bins:
            return self._waveform_cache

        if self.total_samples == 0:
            zeros = np.zeros(num_bins, dtype=np.float32)
            return zeros, zeros

        mono = 0.5 * (self.pcm_data[:, 0] + self.pcm_data[:, 1])
        bin_size = max(1, self.total_samples // num_bins)

        # Truncate to exact multiple of bin_size
        num_usable = (len(mono) // bin_size) * bin_size
        if num_usable == 0:
            zeros = np.zeros(num_bins, dtype=np.float32)
            return zeros, zeros

        reshaped = mono[:num_usable].reshape((-1, bin_size))
        max_peaks = np.max(reshaped, axis=1)
        min_peaks = np.min(reshaped, axis=1)

        # Interpolate or slice to exact num_bins
        if len(max_peaks) != num_bins:
            orig_x = np.linspace(0, 1, len(max_peaks))
            target_x = np.linspace(0, 1, num_bins)
            max_peaks = np.interp(target_x, orig_x, max_peaks)
            min_peaks = np.interp(target_x, orig_x, min_peaks)

        self._waveform_cache = (max_peaks.astype(np.float32), min_peaks.astype(np.float32))
        return self._waveform_cache
