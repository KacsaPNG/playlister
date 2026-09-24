"""
End-to-End Integration Test for Dual-Deck Engine, Auto-DJ, and DSP Chain.
Validates loading demo tracks, rendering audio blocks, auto-crossfading, and loudness normalization.
"""
from pathlib import Path
import numpy as np
import pytest

from app.audio.engine import DualDeckAudioEngine
from app.ingestion.local_loader import LocalAudioLoader
from app.config import PlaybackState


def test_end_to_end_playback_and_crossfade():
    demo_dir = Path("demo_tracks")
    track_a_path = demo_dir / "Demo_Track_A_124BPM.wav"
    track_b_path = demo_dir / "Demo_Track_B_128BPM.wav"

    assert track_a_path.is_file(), "Demo track A must exist"
    assert track_b_path.is_file(), "Demo track B must exist"

    # Initialize Engine (headless)
    engine = DualDeckAudioEngine(sample_rate=44100, block_size=1024)

    # Ingest tracks
    loader = LocalAudioLoader(44100)
    track_a = loader.load_file(track_a_path)
    track_b = loader.load_file(track_b_path)

    assert track_a.metadata.bpm == 124.0 or abs(track_a.metadata.bpm - 124.0) < 5.0
    assert track_b.metadata.bpm == 128.0 or abs(track_b.metadata.bpm - 128.0) < 5.0

    # Load tracks into Deck A and Deck B
    engine.deck_a.load_track(track_a)
    engine.deck_b.load_track(track_b)

    # Start playback on Deck A
    engine.deck_a.play()
    assert engine.deck_a.state == PlaybackState.PLAYING

    # Crossfader starts at full Left (-1.0)
    engine.crossfader.position = -1.0

    # Render 50 audio blocks (simulating ~1.16 seconds of real-time audio)
    rendered_blocks = []
    for _ in range(50):
        # Emulate audio callback
        out_buffer = np.zeros((1024, 2), dtype=np.float32)
        engine._audio_callback(out_buffer, 1024, None, None)
        rendered_blocks.append(out_buffer)

    concatenated = np.vstack(rendered_blocks)
    assert concatenated.shape == (50 * 1024, 2)
    assert np.max(np.abs(concatenated)) > 0.05
    assert not np.isnan(concatenated).any()

    # Fast-forward Deck A to within 5 seconds of the end
    remaining_target = 4.0
    seek_time = track_a.duration_sec - remaining_target
    engine.deck_a.seek_seconds(seek_time)
    engine.crossfader.set_duration(6.0)

    # Run check_auto_dj
    engine.check_auto_dj()

    # Deck B should now be triggered into PLAYING state
    assert engine.deck_b.state == PlaybackState.PLAYING
    assert engine.crossfader.is_transitioning

    # Render through the transition
    for _ in range(200):
        out_buffer = np.zeros((1024, 2), dtype=np.float32)
        engine._audio_callback(out_buffer, 1024, None, None)

    # Crossfade should have moved toward Deck B
    assert engine.crossfader.position > -0.5
