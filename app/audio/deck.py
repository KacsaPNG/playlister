"""
Deck Audio Processing Pipeline and State Machine.
Supports multi-threaded playback, sub-sample position seeking, Pioneer-style CUE logic,
resampling & WSOLA tempo manipulation, loop points, and real-time DSP filter chain.
"""
from dataclasses import dataclass
import threading
from typing import Optional
import numpy as np

from app.audio.buffer import AudioTrack
from app.config import DEFAULT_SAMPLE_RATE, PlaybackState, DeckId
from app.dsp.filter_chain import DeckFilterChain
from app.dsp.time_stretch import Resampler, WSOLATimeStretch, PitchBend


class Deck:
    """
    Independent DJ Deck playback engine and DSP processing pipeline.
    """

    def __init__(self, deck_id: DeckId, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.deck_id = deck_id
        self.sample_rate = sample_rate

        self.lock = threading.RLock()
        self.track: Optional[AudioTrack] = None

        # Playback position in floating-point sample index
        self.playhead_pos: float = 0.0
        self.cue_point: float = 0.0
        self.state: PlaybackState = PlaybackState.STOPPED

        # Tempo & Pitch controls
        self.pitch_slider: float = 0.0  # -16.0% to +16.0%
        self.key_lock: bool = False
        self.pitch_bend = PitchBend(step_size=0.05, ramp_speed=0.25)
        self.wsola = WSOLATimeStretch()

        # DSP Filter Chain (Gain, EQ, Sweep Filter, Reverb, Volume)
        self.dsp_chain = DeckFilterChain(sample_rate)

        # Looping
        self.loop_active: bool = False
        self.loop_start_pos: float = 0.0
        self.loop_end_pos: float = 0.0

        # Cue hold preview
        self.is_cue_holding: bool = False

    def load_track(self, track: AudioTrack):
        """Load a new AudioTrack into the deck."""
        with self.lock:
            self.track = track
            self.playhead_pos = 0.0
            self.cue_point = 0.0
            self.state = PlaybackState.STOPPED
            self.loop_active = False
            self.dsp_chain.reset_state()

            # Apply automatic gain normalization
            self.dsp_chain.auto_gain_db = track.metadata.auto_gain_db

    def unload_track(self):
        """Unload current track."""
        with self.lock:
            self.track = None
            self.playhead_pos = 0.0
            self.cue_point = 0.0
            self.state = PlaybackState.STOPPED
            self.loop_active = False
            self.dsp_chain.reset_state()

    def play(self):
        """Begin playback."""
        with self.lock:
            if self.track is not None and self.playhead_pos < self.track.total_samples:
                self.state = PlaybackState.PLAYING

    def pause(self):
        """Pause playback."""
        with self.lock:
            if self.state == PlaybackState.PLAYING:
                self.state = PlaybackState.PAUSED

    def play_pause_toggle(self):
        """Toggle between play and pause."""
        with self.lock:
            if self.state == PlaybackState.PLAYING:
                self.pause()
            else:
                self.play()

    def cue_press(self):
        """
        Pioneer DJ CUE behavior:
        - If playing: stops immediately and jumps to cue point.
        - If paused/stopped: sets cue point to current playhead and starts cue preview.
        """
        with self.lock:
            if self.state == PlaybackState.PLAYING:
                self.state = PlaybackState.PAUSED
                self.playhead_pos = self.cue_point
            else:
                # Set new cue point at current position
                self.cue_point = self.playhead_pos
                self.is_cue_holding = True
                self.state = PlaybackState.PLAYING

    def cue_release(self):
        """Release CUE button preview."""
        with self.lock:
            if self.is_cue_holding:
                self.is_cue_holding = False
                self.state = PlaybackState.PAUSED
                self.playhead_pos = self.cue_point

    def stop(self):
        """Stop playback and return to cue point."""
        with self.lock:
            self.state = PlaybackState.STOPPED
            self.playhead_pos = self.cue_point

    def seek_seconds(self, seconds: float):
        """Seek playhead to position in seconds."""
        with self.lock:
            if self.track is not None:
                target_samples = float(seconds) * self.sample_rate
                self.playhead_pos = float(np.clip(target_samples, 0, self.track.total_samples))

    def seek_fraction(self, fraction: float):
        """Seek playhead to normalized fraction [0.0, 1.0]."""
        with self.lock:
            if self.track is not None:
                self.seek_seconds(fraction * self.track.duration_sec)

    def set_loop_beats(self, num_beats: float):
        """Set a beat-quantized loop based on detected or current BPM."""
        with self.lock:
            if self.track is None:
                return

            bpm = self.track.metadata.bpm or 120.0
            beat_seconds = 60.0 / bpm
            loop_len_samples = beat_seconds * num_beats * self.sample_rate

            self.loop_start_pos = self.playhead_pos
            self.loop_end_pos = min(float(self.track.total_samples), self.playhead_pos + loop_len_samples)
            self.loop_active = True

    def toggle_loop(self):
        """Toggle loop state."""
        with self.lock:
            self.loop_active = not self.loop_active

    def sync_to_bpm(self, target_bpm: float):
        """Calculate and set pitch slider to beatmatch target BPM."""
        with self.lock:
            if self.track is None or not self.track.metadata.bpm or target_bpm <= 0:
                return

            track_bpm = self.track.metadata.bpm
            # Calculate required pitch slider percentage
            # target = track_bpm * (1 + slider/100) -> slider = (target / track_bpm - 1) * 100
            needed_percent = (target_bpm / track_bpm - 1.0) * 100.0
            self.pitch_slider = float(np.clip(needed_percent, -16.0, 16.0))

    @property
    def current_bpm(self) -> float:
        """Effective BPM including pitch slider and pitch bend."""
        if self.track is None or not self.track.metadata.bpm:
            return 120.0
        effective_rate = (1.0 + self.pitch_slider / 100.0) * (1.0 + self.pitch_bend.current_offset)
        return round(float(self.track.metadata.bpm * effective_rate), 1)

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed playback time in seconds."""
        return self.playhead_pos / float(self.sample_rate)

    @property
    def remaining_seconds(self) -> float:
        """Remaining playback time in seconds."""
        if self.track is None:
            return 0.0
        return max(0.0, self.track.duration_sec - self.elapsed_seconds)

    def render_block(self, num_samples: int) -> np.ndarray:
        """
        Audio callback rendering method.
        Renders num_samples stereo frames, advancing the playhead with pitch/rate interpolation.
        Called by real-time audio thread.
        """
        with self.lock:
            if self.track is None or self.state != PlaybackState.PLAYING or num_samples <= 0:
                return np.zeros((num_samples, 2), dtype=np.float32)

            # Calculate total playback rate factor
            nudge = self.pitch_bend.update()
            effective_rate = float((1.0 + self.pitch_slider / 100.0) * (1.0 + nudge))
            effective_rate = max(0.2, min(effective_rate, 3.0))

            needed_input_samples = int(np.ceil(num_samples * effective_rate)) + 4

            start_idx = int(np.floor(self.playhead_pos))

            # Looping check
            if self.loop_active and self.loop_end_pos > self.loop_start_pos:
                if self.playhead_pos >= self.loop_end_pos:
                    self.playhead_pos = self.loop_start_pos
                    start_idx = int(np.floor(self.playhead_pos))

            # Fetch uncompressed audio slice from track buffer
            raw_slice = self.track.get_slice(start_idx, needed_input_samples)

            if len(raw_slice) == 0:
                self.state = PlaybackState.STOPPED
                return np.zeros((num_samples, 2), dtype=np.float32)

            # Process tempo/pitch
            if self.key_lock and abs(effective_rate - 1.0) > 0.005:
                # Key Lock: WSOLA time-stretching preserves musical pitch
                rendered = self.wsola.stretch(raw_slice, effective_rate)
                if len(rendered) < num_samples:
                    pad = np.zeros((num_samples - len(rendered), 2), dtype=np.float32)
                    rendered = np.vstack([rendered, pad])
                else:
                    rendered = rendered[:num_samples]
            else:
                # Vinyl Mode: Resample audio slice
                rendered = Resampler.resample_block(raw_slice, effective_rate)
                if len(rendered) < num_samples:
                    pad = np.zeros((num_samples - len(rendered), 2), dtype=np.float32)
                    rendered = np.vstack([rendered, pad])
                else:
                    rendered = rendered[:num_samples]

            # Advance playhead position
            advance = num_samples * effective_rate
            self.playhead_pos += advance

            # Check track end
            if self.playhead_pos >= self.track.total_samples:
                if self.loop_active and self.loop_end_pos > self.loop_start_pos:
                    self.playhead_pos = self.loop_start_pos
                else:
                    self.playhead_pos = float(self.track.total_samples)
                    self.state = PlaybackState.STOPPED

            # Apply per-deck DSP filter chain (EQ, Reverb, Gain, Volume, Metering)
            out = self.dsp_chain.process(rendered)
            return out
