"""
Unit tests for DualDeckAudioEngine, Deck, Crossfader, and SmartQueue.
"""
import numpy as np
import pytest

from app.audio.buffer import AudioTrack, TrackMetadata
from app.audio.deck import Deck
from app.audio.engine import DualDeckAudioEngine
from app.config import DeckId, PlaybackState, CrossfadeCurve
from app.queue.crossfader import Crossfader
from app.queue.smart_queue import SmartQueue, QueueStatus


def make_test_track(title="Test", duration_sec=10.0, sr=44100):
    t = np.linspace(0, duration_sec, int(sr * duration_sec))
    sig = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stereo = np.column_stack([sig, sig])
    meta = TrackMetadata(title=title, duration_sec=duration_sec, bpm=128.0)
    return AudioTrack(stereo, sr, meta)


def test_deck_playback_and_cue():
    sr = 44100
    deck = Deck(DeckId.DECK_A, sr)
    track = make_test_track(duration_sec=5.0, sr=sr)

    deck.load_track(track)
    assert deck.state == PlaybackState.STOPPED
    assert deck.playhead_pos == 0.0

    # Start playback
    deck.play()
    assert deck.state == PlaybackState.PLAYING

    # Render 1024 frames
    block = deck.render_block(1024)
    assert block.shape == (1024, 2)
    assert deck.playhead_pos > 1000

    # Test seek
    deck.seek_seconds(2.5)
    assert abs(deck.elapsed_seconds - 2.5) < 0.01

    # Test Pioneer CUE behavior
    deck.cue_press()
    assert deck.state == PlaybackState.PAUSED
    assert deck.playhead_pos == 0.0  # Returned to cue point 0


def test_crossfader_equal_power():
    xfader = Crossfader(CrossfadeCurve.EQUAL_POWER)

    # At full left (-1.0)
    xfader.position = -1.0
    gA, gB = xfader.get_gains()
    assert abs(gA - 1.0) < 1e-4
    assert abs(gB - 0.0) < 1e-4

    # At center (0.0)
    xfader.position = 0.0
    gA, gB = xfader.get_gains()
    # In equal-power, gA^2 + gB^2 = 1.0
    power = gA**2 + gB**2
    assert abs(power - 1.0) < 1e-4
    assert abs(gA - np.sqrt(0.5)) < 1e-3
    assert abs(gB - np.sqrt(0.5)) < 1e-3

    # At full right (+1.0)
    xfader.position = 1.0
    gA, gB = xfader.get_gains()
    assert abs(gA - 0.0) < 1e-4
    assert abs(gB - 1.0) < 1e-4


def test_smart_queue_alternation():
    queue = SmartQueue()
    t1 = make_test_track("Song 1")
    t2 = make_test_track("Song 2")
    t3 = make_test_track("Song 3")

    item1 = queue.add_track(t1)
    item2 = queue.add_track(t2)
    item3 = queue.add_track(t3)

    # Verify alternation A -> B -> A
    assert item1.target_deck == "A"
    assert item2.target_deck == "B"
    assert item3.target_deck == "A"

    next_a = queue.get_next_for_deck("A")
    assert next_a.metadata.title == "Song 1"

    next_b = queue.get_next_for_deck("B")
    assert next_b.metadata.title == "Song 2"


def test_engine_mixing_and_autodj():
    engine = DualDeckAudioEngine(44100, 1024)
    tA = make_test_track("Deck A Track", duration_sec=8.0)
    tB = make_test_track("Deck B Track", duration_sec=8.0)

    engine.deck_a.load_track(tA)
    engine.deck_b.load_track(tB)

    engine.deck_a.play()
    engine.crossfader.position = -1.0  # Deck A active

    # Seek Deck A so only 6 seconds remain (within crossfade window of 7s)
    engine.deck_a.seek_seconds(3.0)
    engine.crossfader.set_duration(7.0)

    # Check Auto-DJ trigger
    engine.check_auto_dj()
    # Should have triggered playback on Deck B and started crossfade transition
    assert engine.deck_b.state == PlaybackState.PLAYING
    assert engine.crossfader.is_transitioning
