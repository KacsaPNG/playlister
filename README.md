# PlaylisterAG // Professional Dual-Deck Desktop DJ Application

A standalone, production-ready desktop DJ system built with Python, PyQt6, NumPy, SciPy, and PortAudio (`sounddevice`). Features dual multi-threaded audio processing decks, automated YouTube and YouTube Music stream ingestion directly into memory PCM buffers, an intelligent auto-cueing smart playlist queue, an automated mixing crossfade engine with equal-power logarithmic curves, professional DSP effects (3-band parametric EQ, Pioneer-style sweep filter, Schroeder/Freeverb algorithmic reverb, WSOLA time-stretching), and ITU-R BS.1770 / EBU R128 integrated loudness normalization with a lookahead master peak limiter.

---

## 🎧 Architecture & Core Features

```
                                  [ YouTube / YouTube Music URL ]
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │  yt-dlp Stream Reader │
                                     │  & FFmpeg PCM Decoder │
                                     └───────────┬───────────┘
                                                 │ 32-bit float stereo PCM
                                                 ▼
                                     ┌───────────────────────┐
                                     │  BS.1770 Loudness &   │
                                     │  BPM Auto-Analyzer    │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │   Smart Queue Router  │
                                     │   (Alternates A / B)  │
                                     └─────┬───────────┬─────┘
                                           │           │
                       ┌───────────────────┘           └───────────────────┐
                       ▼                                                   ▼
            ┌─────────────────────┐                             ┌─────────────────────┐
            │       DECK A        │                             │       DECK B        │
            │  Buffer & Playhead  │                             │  Buffer & Playhead  │
            ├─────────────────────┤                             ├─────────────────────┤
            │ WSOLA Time-Stretch  │                             │ WSOLA Time-Stretch  │
            │   & Vinyl Resample  │                             │   & Vinyl Resample  │
            ├─────────────────────┤                             ├─────────────────────┤
            │ 3-Band Parametric EQ│                             │ 3-Band Parametric EQ│
            │   & DJ Sweep Filter │                             │   & DJ Sweep Filter │
            ├─────────────────────┤                             ├─────────────────────┤
            │  Freeverb Reverb    │                             │  Freeverb Reverb    │
            ├─────────────────────┤                             ├─────────────────────┤
            │ Auto-Gain / Trim    │                             │ Auto-Gain / Trim    │
            └──────────┬──────────┘                             └──────────┬──────────┘
                       │                                                   │
                       └───────────────────┐           ┌───────────────────┘
                                           ▼           ▼
                                     ┌───────────────────────┐
                                     │ Equal-Power Crossfade │◄── Auto-DJ Countdown
                                     │    Mixer & Faders     │    (Triggers at 5-10s)
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Master Lookahead Peak │
                                     │ Limiter & Tanh Ceiling│
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     [ Stereo PortAudio Out ]
```

### 1. Dual-Deck Audio Engine (`app/audio/`)
- **Simultaneous Multi-Threaded Audio Pipeline**: Two completely decoupled audio pipelines ([Deck A](file:///app/audio/deck.py) and [Deck B](file:///app/audio/deck.py)) operating with sample-accurate fractional playhead tracking.
- **Pioneer DJ CUE Behavior**:
  - Pressing CUE while playing immediately pauses and returns playhead to the stored cue point.
  - Pressing CUE while paused re-anchors the cue point at the current playhead position and plays a momentary preview while held.
- **Sub-Sample Seeking & Looping**: Seamless beat-quantized looping (`1`, `2`, `4`, `8`, `16` beats) and interactive click/drag waveform scrubbing.

### 2. YouTube Audio Stream Ingestion (`app/ingestion/`)
- **In-Memory Streaming Decoding**: Directly extracts audio streams from YouTube and YouTube Music URLs using `yt-dlp` and pipes them through bundled FFmpeg (`imageio-ffmpeg`) directly into uncompressed 32-bit floating point PCM arrays (`f32le`, 44.1 kHz stereo) in memory without intermediate video files.
- **Local Audio Library Support**: Seamlessly loads local audio files (`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.aiff`) via `soundfile` with FFmpeg fallback.
- **Non-Blocking Background Workers**: Ingestion runs on dedicated background `QThread` workers so the UI and real-time audio playback never freeze or glitch.

### 3. Smart Queue & Automated Crossfader (`app/queue/`)
- **Dynamic Alternating Deck Router**: Automatically routes queued tracks alternately between Deck A and Deck B (Track 1 ➔ Deck A, Track 2 ➔ Deck B, Track 3 ➔ Deck A...).
- **Equal-Power Crossfading**:
  - Implements constant acoustic power curves: $G_A = \cos\left(\frac{\pi}{2} t\right)$, $G_B = \sin\left(\frac{\pi}{2} t\right)$ satisfying $G_A^2 + G_B^2 = 1.0$, completely eliminating the center volume dip of linear crossfaders.
  - Selectable curves: Equal Power, Linear, Logarithmic, and Smooth Step.
- **Auto-DJ Continuous Mix Algorithm**:
  - Real-time monitor triggers when 5 to 10 seconds remain on the playing deck.
  - Automatically triggers playback on the secondary deck and performs an automated equal-power crossfade transition.
  - Upon transition completion, the idle deck is paused, marked as played, and the next track in the queue is automatically preloaded and cued up for uninterrupted hands-free mixing.

### 4. DSP Filter Chain & Effects (`app/dsp/`)
- **3-Band Parametric EQ & Kill Switches** ([`app/dsp/eq.py`](file:///app/dsp/eq.py)):
  - Built from Robert Bristow-Johnson's Audio EQ Cookbook:
    - **Low-Shelf**: 250 Hz, -24 dB to +12 dB
    - **Peaking Mid**: 1000 Hz, Q = 1.0, -24 dB to +12 dB
    - **High-Shelf**: 4000 Hz, -24 dB to +12 dB
  - Direct Form II Transposed biquad filtering with persistent filter state vectors across consecutive audio blocks for click-free performance.
  - Dedicated instant -60 dB Kill toggles for each frequency band.
- **DJ Color Sweep Filter**:
  - Bi-directional sweep knob: sweeping counter-clockwise engages a 2nd-order resonant Low-Pass filter down to 60 Hz; sweeping clockwise engages a resonant High-Pass filter up to 8 kHz. Center position is completely neutral (bypassed).
- **Algorithmic Reverb Unit** ([`app/dsp/reverb.py`](file:///app/dsp/reverb.py)):
  - Stereo Schroeder/Freeverb architecture: 8 parallel Lowpass Feedback Comb Filters (LBCF) + 4 series All-Pass diffusion filters per channel with prime delay spacings.
  - Vectorized block-based circular buffers in NumPy with adjustable room size, high-frequency damping, stereo width, and wet/dry mix.
- **BPM & Pitch Control** ([`app/dsp/time_stretch.py`](file:///app/dsp/time_stretch.py)):
  - **Turntable Pitch Fader**: Sub-sample interpolation resampling (-16% to +16%).
  - **Key-Lock (Master Tempo)**: Waveform Similarity Overlap-Add (WSOLA) time-stretching preserves original musical key while adjusting playback tempo.
  - **Pitch Bend / Nudge**: Momentary +/- buttons with smooth exponential return for beat grid nudging.
  - **Automatic BPM Detection**: Novelty energy envelope autocorrelation detects tempo on track ingestion.

### 5. Loudness Normalization & Peak Limiter (`app/dsp/loudness.py`, `app/dsp/limiter.py`)
- **ITU-R BS.1770 / EBU R128 Integrated Loudness**:
  - K-weighting high-shelf head filter + RLB high-pass filter with dual-gated energy integration.
  - Analyzes audio on load and computes recommended gain offsets to normalize all tracks to -14 LUFS standard.
- **Master Lookahead Peak Limiter**:
  - Lookahead delay buffer + fast peak envelope follower with smooth exponential release.
  - Tanh soft-saturation safety ceiling at -0.1 dBFS to eliminate any digital clipping or harsh distortion.
  - Real-time Gain Reduction (GR) meter reporting.

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10+** (Python 3.11, 3.12, 3.13 supported)
- Audio output device (Speakers, Headphones, or USB Audio Interface)

### 1. Clone or Open Project
```bash
cd playlisterag
```

### 2. Create Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

*Note: `imageio-ffmpeg` bundles standalone FFmpeg binaries automatically for Windows, macOS, and Linux.*

---

## 🎮 Running the Application

Launch the desktop DJ application:
```bash
python run.py
```

### Generate Offline Demo Tracks (Optional)
To test beatmatching, looping, and crossfading without an internet connection:
```bash
python tests/generate_demo_tracks.py
```
This generates two house tracks:
- `demo_tracks/Demo_Track_A_124BPM.wav` (124.0 BPM)
- `demo_tracks/Demo_Track_B_128BPM.wav` (128.0 BPM)

---

## 🧪 Running Automated Tests

Run the full unit and integration test suite with `pytest`:
```bash
pytest -v
```

Tests include:
- `tests/test_dsp.py`: Validates biquad EQ, sweep filter, Freeverb reverb, resampler, WSOLA time stretch, BS.1770 loudness, and peak limiter.
- `tests/test_engine.py`: Validates Deck playback states, Pioneer CUE logic, equal-power crossfade mathematics ($G_A^2 + G_B^2 = 1.0$), and smart queue alternation.
- `tests/test_ingestion.py`: Validates local audio decoding and waveform peak summaries.
- `tests/test_end_to_end.py`: End-to-end integration test validating simulated audio playback, Auto-DJ countdown, and automated crossfade transitions.

---

## 🎛️ Keyboard & GUI Quick Reference

| Feature | Control | Description |
|---|---|---|
| **Play / Pause** | Large Green Button | Toggles playback on the deck |
| **CUE** | Large Red Button | Jumps to cue point when playing; sets cue point and plays preview when held while paused |
| **SYNC** | Amber SYNC Button | Automatically matches pitch slider to the other deck's current BPM |
| **Pitch Bend** | NUDGE - / NUDGE + | Momentary +/- 5% speed adjustment for nudging beat alignment |
| **Key Lock** | KEY LOCK Button | Toggles between Vinyl mode (resampling) and Key Lock mode (WSOLA time-stretch) |
| **EQ Kills** | KILL Buttons | Instantly cuts High, Mid, or Low band to -60 dB |
| **Filter** | FILTER Slider | Center is neutral; down = Resonant Low-Pass; up = Resonant High-Pass |
| **Reverb** | REV ON Button | Engages algorithmic Freeverb stereo reverb unit |
| **Crossfader** | Center Horizontal Slider | Smooth crossfade between Deck A and Deck B with Equal-Power curve |
| **Auto-DJ** | AUTO-DJ Button | Automatically triggers playback and crossfades when 5-10s remain on playing track |
| **Waveform** | Overview / Zoom Bar | Click anywhere on the overview waveform to seek instantly |
