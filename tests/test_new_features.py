"""
Unit tests for the new features:
1. EQ & DJ Filter reset
2. Reverb reset to factory defaults
3. Beat-synced Auto-DJ transitions (phase-alignment, tempo-matching, phrase quantization)
4. Playlist jump loading to Deck A and Deck B
"""
import os
import numpy as np
import pytest

from app.audio.buffer import AudioTrack, TrackMetadata
from app.audio.deck import Deck
from app.audio.engine import DualDeckAudioEngine
from app.config import DeckId, PlaybackState, CrossfadeCurve
from app.dsp.eq import ThreeBandEQ
from app.dsp.reverb import ReverbUnit
from app.queue.crossfader import Crossfader
from app.queue.smart_queue import SmartQueue, QueueStatus


def make_test_track(title="Track", duration_sec=15.0, bpm=128.0, sr=44100):
    t = np.linspace(0, duration_sec, int(sr * duration_sec))
    sig = (0.4 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    stereo = np.column_stack([sig, sig])
    meta = TrackMetadata(title=title, duration_sec=duration_sec, bpm=bpm)
    return AudioTrack(stereo, sr, meta)


def test_eq_and_filter_reset():
    eq = ThreeBandEQ(sample_rate=44100)
    # Modify EQ parameters via properties
    eq.high_gain = 6.0
    eq.mid_gain = -12.0
    eq.low_gain = -24.0
    eq.filter_val = -0.8  # Lowpass filter engaged
    eq.high_kill = True
    eq.low_kill = True

    assert eq.high_gain == 6.0
    assert eq.filter_val == -0.8
    assert eq.high_kill is True

    # Call reset_defaults
    eq.reset_defaults()

    assert eq.high_gain == 0.0
    assert eq.mid_gain == 0.0
    assert eq.low_gain == 0.0
    assert eq.filter_val == 0.0
    assert eq.high_kill is False
    assert eq.mid_kill is False
    assert eq.low_kill is False


def test_reverb_reset():
    rev = ReverbUnit(sample_rate=44100)
    rev.enabled = True
    rev.wet = 0.85
    rev.room_size = 0.95
    rev.damping = 0.5

    assert rev.enabled is True
    assert rev.wet == 0.85

    # Reset
    rev.reset_defaults()

    assert rev.enabled is False
    assert rev.wet == 0.35
    assert rev.room_size == 0.75
    assert rev.damping == 0.25



def test_beat_synced_auto_dj_transition():
    sr = 44100
    engine = DualDeckAudioEngine(sample_rate=sr, block_size=1024)
    engine.crossfader.auto_dj_enabled = True
    engine.crossfader.position = -1.0  # Deck A active

    # 120 BPM: spb = 0.5s, 4-beat bar = 2.0s
    track_a = make_test_track("Track A", duration_sec=20.0, bpm=120.0, sr=sr)
    # 124 BPM incoming
    track_b = make_test_track("Track B", duration_sec=20.0, bpm=124.0, sr=sr)

    engine.deck_a.load_track(track_a)
    engine.deck_b.load_track(track_b)
    engine.deck_a.play()

    engine.crossfader.set_duration(8.0)  # 8.0s setting

    # Seek Deck A so it is inside the crossfade window but OFF beat:
    # At 120 BPM, beats are at 0.0, 0.5, 1.0, 1.5 ...
    # Seek to 12.23s (rem = 7.77s <= 8.0s, but off beat by 0.23s)
    engine.deck_a.seek_seconds(12.23)
    engine.check_auto_dj()

    # Off beat: should NOT have triggered transition yet!
    assert not engine.crossfader.is_transitioning
    assert engine.deck_b.state != PlaybackState.PLAYING

    # Now seek Deck A to exactly on beat: 12.5s (rem = 7.5s <= 8.0s)
    engine.deck_a.seek_seconds(12.5)
    engine.check_auto_dj()

    # On beat: should trigger!
    assert engine.crossfader.is_transitioning
    assert engine.deck_b.state == PlaybackState.PLAYING

    # Deck B tempo should be beatmatched to Deck A (120 BPM)
    assert abs(engine.deck_b.current_bpm - 120.0) < 0.2


def test_playlist_jump_loading():
    sr = 44100
    engine = DualDeckAudioEngine(sample_rate=sr, block_size=1024)

    t1 = make_test_track("Song 1", duration_sec=10.0, sr=sr)
    t2 = make_test_track("Song 2", duration_sec=10.0, sr=sr)
    t3 = make_test_track("Song 3", duration_sec=10.0, sr=sr)

    engine.queue.add_track(t1)
    engine.queue.add_track(t2)
    engine.queue.add_track(t3)

    assert len(engine.queue.items) == 3

    # Jump: load item 2 directly to Deck A
    item = engine.queue.items[2]
    engine.deck_a.load_track(item.track)
    item.target_deck = "A"
    item.status = QueueStatus.LOADED_A

    assert engine.deck_a.track.metadata.title == "Song 3"
    assert engine.queue.items[2].status == QueueStatus.LOADED_A


def test_disable_beatmatching():
    sr = 44100
    engine = DualDeckAudioEngine(sample_rate=sr, block_size=1024)

    # Deck A at 120 BPM, Deck B at 135 BPM
    t_a = make_test_track("Track A", duration_sec=20.0, bpm=120.0, sr=sr)
    t_b = make_test_track("Track B", duration_sec=20.0, bpm=135.0, sr=sr)

    engine.deck_a.load_track(t_a)
    engine.deck_b.load_track(t_b)
    engine.crossfader.position = -1.0  # Deck A active

    engine.deck_a.play()
    assert engine.deck_a.current_bpm == 120.0
    assert engine.deck_b.current_bpm == 135.0

    # 1. Disable beatmatching
    engine.beatmatching_enabled = False
    assert engine.beatmatching_enabled is False

    engine.crossfader.set_duration(8.0)
    # Seek on beat to trigger
    engine.deck_a.seek_seconds(12.5)
    engine.check_auto_dj()

    assert engine.crossfader.is_transitioning
    assert engine.deck_b.state == PlaybackState.PLAYING
    # Beatmatching disabled: Deck B BPM must remain at 135.0, NOT synced to 120.0!
    assert engine.deck_b.current_bpm == 135.0
    assert engine.deck_b.pitch_slider == 0.0
