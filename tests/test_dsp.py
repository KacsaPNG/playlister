"""
Unit Tests for DSP Components.
Validates biquad filters, 3-band EQ, Freeverb reverb, resampler, WSOLA, loudness, and peak limiter.
"""
import numpy as np
import pytest

from app.dsp.biquad import BiquadFilter
from app.dsp.eq import ThreeBandEQ
from app.dsp.reverb import ReverbUnit
from app.dsp.time_stretch import Resampler, WSOLATimeStretch, PitchBend, BpmDetector
from app.dsp.loudness import LoudnessAnalyzer
from app.dsp.limiter import PeakLimiter
from app.dsp.filter_chain import DeckFilterChain


def test_biquad_filters():
    sr = 44100
    biquad = BiquadFilter(sr)
    x = np.random.randn(1024, 2).astype(np.float32)

    # Test Low-Shelf
    biquad.set_low_shelf(250.0, -12.0)
    out1 = biquad.process(x)
    assert out1.shape == x.shape
    assert not np.isnan(out1).any()
    assert not np.isinf(out1).any()

    # Test High-Shelf
    biquad.set_high_shelf(4000.0, 6.0)
    out2 = biquad.process(x)
    assert out2.shape == x.shape

    # Test Peaking
    biquad.set_peaking(1000.0, -6.0, q=1.0)
    out3 = biquad.process(x)
    assert out3.shape == x.shape

    # Test Sweep LPF/HPF
    biquad.set_low_pass(500.0)
    out4 = biquad.process(x)
    assert out4.shape == x.shape
    biquad.set_high_pass(2000.0)
    out5 = biquad.process(x)
    assert out5.shape == x.shape


def test_three_band_eq():
    eq = ThreeBandEQ(44100)
    x = np.random.randn(1024, 2).astype(np.float32)

    eq.low_gain = -6.0
    eq.mid_gain = 3.0
    eq.high_gain = -3.0
    eq.filter_knob = -0.5  # Low-pass sweep

    out = eq.process(x)
    assert out.shape == x.shape
    assert not np.isnan(out).any()

    # Test kill switches
    eq.low_kill = True
    eq.mid_kill = True
    eq.high_kill = True
    out_killed = eq.process(x)
    assert np.max(np.abs(out_killed)) < np.max(np.abs(x))


def test_reverb():
    reverb = ReverbUnit(44100)
    x = np.random.randn(1024, 2).astype(np.float32)

    reverb.enabled = True
    reverb.wet = 0.5
    reverb.room_size = 0.85
    reverb.damping = 0.3

    out = reverb.process(x)
    assert out.shape == x.shape
    assert not np.isnan(out).any()
    assert not np.isinf(out).any()


def test_resampler():
    x = np.random.randn(1024, 2).astype(np.float32)
    # Test speed up (+8%)
    out_fast = Resampler.resample_block(x, 1.08)
    assert out_fast.shape == (round(1024 / 1.08), 2)
    # Test slow down (-8%)
    out_slow = Resampler.resample_block(x, 0.92)
    assert out_slow.shape == (round(1024 / 0.92), 2)


def test_wsola_time_stretch():
    wsola = WSOLATimeStretch()
    x = np.random.randn(44100, 2).astype(np.float32)

    stretched = wsola.stretch(x, 1.15)
    assert stretched.shape[1] == 2
    assert abs(stretched.shape[0] - int(44100 / 1.15)) < 1000
    assert not np.isnan(stretched).any()


def test_pitch_bend():
    pb = PitchBend(step_size=0.04)
    assert pb.current_offset == 0.0
    pb.nudge_up()
    for _ in range(20):
        val = pb.update()
    assert val > 0.035
    pb.release()
    for _ in range(30):
        val = pb.update()
    assert abs(val) < 0.005


def test_loudness_analyzer():
    analyzer = LoudnessAnalyzer(44100, target_lufs=-14.0)
    t = np.linspace(0, 3, 44100 * 3)
    sig = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    stereo = np.column_stack([sig, sig])

    report = analyzer.analyze(stereo)
    assert isinstance(report.integrated_lufs, float)
    assert isinstance(report.true_peak_db, float)
    assert isinstance(report.recommended_gain_db, float)


def test_peak_limiter():
    limiter = PeakLimiter(44100, threshold_db=-0.5, ceiling_db=-0.1)
    # Signal with peaks at +6 dBFS (amplitude 2.0)
    x = (np.random.randn(2048, 2) * 2.0).astype(np.float32)

    out = limiter.process(x)
    assert out.shape == x.shape
    # Check that peaks do not exceed ceiling
    ceiling_linear = 10.0 ** (-0.1 / 20.0)
    assert np.max(np.abs(out)) <= ceiling_linear + 0.01
    assert limiter.current_gr_db < 0.0  # Limiting was applied


def test_deck_filter_chain():
    chain = DeckFilterChain(44100)
    x = np.random.randn(1024, 2).astype(np.float32)
    out = chain.process(x)
    assert out.shape == x.shape
    assert chain.peak_levels[0] > 0.0
