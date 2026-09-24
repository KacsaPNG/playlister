"""
Utility to generate synthetic demo DJ tracks (Electronic / House style)
for offline testing and beatmatching validation.
"""
from pathlib import Path
import numpy as np
import soundfile as sf


def generate_kick(sr=44100, dur=0.2):
    t = np.linspace(0, dur, int(sr * dur))
    freq = 150.0 * np.exp(-t * 25.0) + 40.0
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    env = np.exp(-t * 15.0)
    return (np.sin(phase) * env).astype(np.float32)


def generate_hihat(sr=44100, dur=0.08):
    n = int(sr * dur)
    noise = np.random.randn(n).astype(np.float32)
    t = np.linspace(0, dur, n)
    env = np.exp(-t * 60.0)
    return (noise * env * 0.4).astype(np.float32)


def generate_house_track(filename: str, bpm: float = 126.0, duration_bars: int = 16, sr: int = 44100):
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4.0
    total_sec = bar_sec * duration_bars
    total_samples = int(total_sec * sr)

    audio_L = np.zeros(total_samples, dtype=np.float32)
    audio_R = np.zeros(total_samples, dtype=np.float32)

    kick = generate_kick(sr)
    hihat = generate_hihat(sr)

    # 4/4 Beat grid
    total_beats = duration_bars * 4
    for b in range(total_beats):
        beat_sample = int(b * beat_sec * sr)

        # Kick on every beat
        if beat_sample + len(kick) < total_samples:
            audio_L[beat_sample : beat_sample + len(kick)] += kick * 0.8
            audio_R[beat_sample : beat_sample + len(kick)] += kick * 0.8

        # Offbeat hi-hat (on the & of every beat)
        offbeat_sample = int((b + 0.5) * beat_sec * sr)
        if offbeat_sample + len(hihat) < total_samples:
            audio_L[offbeat_sample : offbeat_sample + len(hihat)] += hihat * 0.6
            audio_R[offbeat_sample : offbeat_sample + len(hihat)] += hihat * 0.4

    # Add a grooving bassline
    bass_notes = [55.0, 55.0, 65.41, 73.42, 55.0, 49.0, 55.0, 61.74]  # A1, C2, D2, A1, G1, A1, B1
    for b in range(total_beats):
        note_freq = bass_notes[b % len(bass_notes)]
        sample_start = int(b * beat_sec * sr)
        note_len = int(beat_sec * 0.7 * sr)
        if sample_start + note_len < total_samples:
            t = np.linspace(0, beat_sec * 0.7, note_len)
            bass = 0.4 * (
                np.sin(2 * np.pi * note_freq * t) + 0.3 * np.sin(2 * np.pi * note_freq * 2 * t)
            )
            env = np.exp(-t * 3.0)
            audio_L[sample_start : sample_start + note_len] += (bass * env).astype(np.float32)
            audio_R[sample_start : sample_start + note_len] += (bass * env).astype(np.float32)

    # Soft master limiting
    stereo = np.column_stack([audio_L, audio_R])
    max_val = np.max(np.abs(stereo))
    if max_val > 0.95:
        stereo = stereo * (0.95 / max_val)

    out_path = Path(filename).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), stereo, sr)
    print(f"Generated demo track: {out_path} ({duration_bars} bars, {bpm} BPM)")
    return out_path


if __name__ == "__main__":
    demo_dir = Path("demo_tracks")
    demo_dir.mkdir(exist_ok=True)
    generate_house_track(demo_dir / "Demo_Track_A_124BPM.wav", bpm=124.0, duration_bars=12)
    generate_house_track(demo_dir / "Demo_Track_B_128BPM.wav", bpm=128.0, duration_bars=12)
