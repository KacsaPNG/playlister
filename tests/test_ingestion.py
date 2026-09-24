"""
Unit tests for Ingestion and Local File Loader.
"""
import tempfile
import numpy as np
import soundfile as sf
import pytest

from app.ingestion.local_loader import LocalAudioLoader
from app.audio.buffer import AudioTrack


def test_local_loader_wav():
    sr = 44100
    t = np.linspace(0, 3, sr * 3)
    sig = (0.4 * np.sin(2 * np.pi * 500 * t)).astype(np.float32)
    stereo = np.column_stack([sig, sig])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, stereo, sr)
        tmp_path = f.name

    loader = LocalAudioLoader(sample_rate=sr)
    track = loader.load_file(tmp_path)

    assert isinstance(track, AudioTrack)
    assert track.sample_rate == sr
    assert track.total_samples == sr * 3
    assert abs(track.duration_sec - 3.0) < 0.05
    assert track.metadata.loudness_lufs < 0.0
    assert track.metadata.bpm > 0


def test_waveform_peaks_generation():
    sr = 44100
    t = np.linspace(0, 2, sr * 2)
    sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    track = AudioTrack(sig, sr)

    max_p, min_p = track.get_waveform_peaks(num_bins=400)
    assert len(max_p) == 400
    assert len(min_p) == 400
    assert np.max(max_p) > 0.5
    assert np.min(min_p) < -0.5
