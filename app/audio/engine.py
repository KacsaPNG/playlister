"""
Dual-Deck Master Audio Engine.
Coordinates Deck A, Deck B, Smart Queue, Equal-Power Crossfader, and Master Lookahead Limiter.
Operates low-latency sounddevice PortAudio stereo output stream with thread-safe callbacks.
"""
import logging
import threading
import time
from typing import Optional, List, Callable
import numpy as np
import sounddevice as sd

from app.audio.deck import Deck
from app.config import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_BLOCK_SIZE,
    DeckId,
    PlaybackState,
    CrossfadeCurve,
)
from app.dsp.limiter import PeakLimiter
from app.queue.crossfader import Crossfader
from app.queue.smart_queue import SmartQueue

logger = logging.getLogger(__name__)


class DualDeckAudioEngine:
    """
    Central Audio Engine managing two independent decks, master mixing,
    crossfading, auto-gain peak limiting, and real-time audio output.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE, block_size: int = DEFAULT_BLOCK_SIZE):
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Independent Decks
        self.deck_a = Deck(DeckId.DECK_A, sample_rate)
        self.deck_b = Deck(DeckId.DECK_B, sample_rate)

        # Crossfader and Queue
        self.crossfader = Crossfader(CrossfadeCurve.EQUAL_POWER)
        self.queue = SmartQueue()

        # Master Limiter
        self.master_limiter = PeakLimiter(sample_rate, threshold_db=-0.5, ceiling_db=-0.1)
        self.master_volume: float = 1.0  # 0.0 to 1.25

        # Master VU levels [peak_L, peak_R, rms_L, rms_R]
        self.master_peak_levels = np.zeros(2, dtype=np.float32)
        self.master_rms_levels = np.zeros(2, dtype=np.float32)

        # Audio stream
        self.stream: Optional[sd.OutputStream] = None
        self._is_running = False
        self._stream_device: Optional[int] = None

        # Performance monitoring
        self.callback_duration_ms: float = 0.0
        self.dsp_cpu_percent: float = 0.0

        # Auto-DJ transition tracking
        self._auto_dj_active_outgoing: Optional[str] = None
        self._auto_dj_active_incoming: Optional[str] = None

    def start(self, device_index: Optional[int] = None):
        """Start real-time audio playback stream."""
        if self._is_running:
            return

        self._stream_device = device_index
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                device=device_index,
                channels=2,
                dtype="float32",
                callback=self._audio_callback,
            )
            self.stream.start()
            self._is_running = True
            logger.info(f"Audio stream started at {self.sample_rate} Hz (block size: {self.block_size})")
        except Exception as e:
            logger.error(f"Failed to open sounddevice output stream: {e}")
            raise

    def stop(self):
        """Stop real-time audio playback stream."""
        if not self._is_running:
            return

        self._is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
            self.stream = None

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """Real-time audio rendering callback executed on dedicated PortAudio thread."""
        t_start = time.perf_counter()

        if status:
            logger.warning(f"PortAudio status warning: {status}")

        # 1. Update automated crossfader position if Auto-DJ is interpolating
        is_transitioning = self.crossfader.update_auto_transition(frames=frames, sample_rate=self.sample_rate)

        # 2. Render Deck A and Deck B stereo blocks
        block_a = self.deck_a.render_block(frames)
        block_b = self.deck_b.render_block(frames)

        # 3. Calculate crossfade curve gains
        gain_a, gain_b = self.crossfader.get_gains()

        # 4. Mix decks together
        mix = (block_a * gain_a) + (block_b * gain_b)

        # 5. Apply master volume
        if abs(self.master_volume - 1.0) > 0.01:
            mix *= self.master_volume

        # 6. Apply master lookahead peak limiter & soft ceiling
        limited = self.master_limiter.process(mix)

        # 7. Update master peak/RMS meters
        if limited.shape[0] > 0:
            self.master_peak_levels[0] = float(np.max(np.abs(limited[:, 0])))
            self.master_peak_levels[1] = float(np.max(np.abs(limited[:, 1])))
            self.master_rms_levels[0] = float(np.sqrt(np.mean(limited[:, 0] ** 2) + 1e-12))
            self.master_rms_levels[1] = float(np.sqrt(np.mean(limited[:, 1] ** 2) + 1e-12))

        # 8. Copy to output buffer
        outdata[:] = limited

        # Measure DSP callback time and CPU usage
        t_end = time.perf_counter()
        dur_ms = (t_end - t_start) * 1000.0
        self.callback_duration_ms = dur_ms
        nominal_buffer_ms = (frames / float(self.sample_rate)) * 1000.0
        self.dsp_cpu_percent = min(100.0, (dur_ms / max(0.1, nominal_buffer_ms)) * 100.0)

    def _trigger_beat_synced_transition(
        self,
        outgoing: Deck,
        incoming: Deck,
        outgoing_name: str,
        incoming_name: str,
        xfade_sec: float,
    ) -> bool:
        """
        Check if outgoing deck is on a beat boundary, sync tempos, align beat phase,
        and trigger automated crossfade transition with beat-quantized duration.
        Returns True if transition was triggered.
        """
        rem = outgoing.remaining_seconds
        if rem <= 0.1 or rem > xfade_sec:
            return False

        # Preload incoming deck if empty
        if incoming.track is None:
            next_track = self.queue.get_next_for_deck(incoming_name)
            if next_track is not None:
                incoming.load_track(next_track)

        if incoming.track is None:
            return False

        # Calculate musical beat parameters
        bpm = outgoing.current_bpm
        spb = 60.0 / max(30.0, bpm)
        elapsed = outgoing.elapsed_seconds
        phase = elapsed % spb
        time_to_beat = (spb - phase) % spb

        # Beat snap window (within 80ms of beat) or force trigger if running out of audio
        on_beat = (time_to_beat <= 0.08) or (phase <= 0.08)
        force_trigger = (rem <= 0.5) or (rem <= xfade_sec - (spb * 2.0))

        if not (on_beat or force_trigger):
            return False  # Wait for upcoming beat boundary so beats drop together

        # 1. Beatmatch: sync incoming deck tempo to outgoing deck
        incoming.sync_to_bpm(outgoing.current_bpm)

        # 2. Phase alignment: ensure incoming beat lands synchronously with outgoing beat
        if incoming.state == PlaybackState.PLAYING:
            inc_spb = 60.0 / max(30.0, incoming.current_bpm)
            inc_phase = incoming.elapsed_seconds % inc_spb
            out_phase = outgoing.elapsed_seconds % spb
            phase_diff = (out_phase - inc_phase) % inc_spb
            if phase_diff > inc_spb / 2.0:
                phase_diff -= inc_spb
            with incoming.lock:
                new_pos = incoming.playhead_pos + phase_diff * self.sample_rate
                incoming.playhead_pos = float(np.clip(new_pos, 0, incoming.track.total_samples))
        else:
            with incoming.lock:
                incoming.playhead_pos = incoming.cue_point

        # 3. Start incoming playback
        incoming.play()
        self.queue.mark_playing(incoming.track.metadata.id)
        self._auto_dj_active_outgoing = outgoing_name
        self._auto_dj_active_incoming = incoming_name

        # 4. Musical phrase quantization: snap transition duration to nearest 4-beat bars
        bar_sec = 4.0 * spb
        num_bars = max(1, round(xfade_sec / bar_sec))
        beat_duration = num_bars * bar_sec

        self.crossfader.start_auto_transition(target_deck=incoming_name, duration=beat_duration)
        logger.info(
            f"Beat-synced Auto-DJ transition started: Deck {outgoing_name} -> Deck {incoming_name} "
            f"({bpm:.1f} BPM, {num_bars} bars / {beat_duration:.2f}s)"
        )
        return True

    def check_auto_dj(self):
        """
        Auto-DJ logic loop called periodically (e.g. at 20-40 Hz from GUI timer).
        Detects when remaining playback time reaches threshold, waits for next beat boundary,
        synchronizes tempos and beat phases so beats start together, and executes automated transition.
        Preloads next tracks from smart queue when transitions complete.
        """
        if not self.crossfader.auto_dj_enabled:
            return

        xfade_sec = self.crossfader.crossfade_duration

        # Case 1: Deck A is playing toward Deck B
        if (
            self.deck_a.state == PlaybackState.PLAYING
            and self.crossfader.position < 0.2
            and not self.crossfader.is_transitioning
        ):
            self._trigger_beat_synced_transition(
                outgoing=self.deck_a,
                incoming=self.deck_b,
                outgoing_name="A",
                incoming_name="B",
                xfade_sec=xfade_sec,
            )

        # Case 2: Deck B is playing toward Deck A
        elif (
            self.deck_b.state == PlaybackState.PLAYING
            and self.crossfader.position > -0.2
            and not self.crossfader.is_transitioning
        ):
            self._trigger_beat_synced_transition(
                outgoing=self.deck_b,
                incoming=self.deck_a,
                outgoing_name="B",
                incoming_name="A",
                xfade_sec=xfade_sec,
            )


        # Check if an auto-transition just finished
        if not self.crossfader.is_transitioning and self._auto_dj_active_outgoing is not None:
            outgoing = self._auto_dj_active_outgoing
            self._auto_dj_active_outgoing = None
            self._auto_dj_active_incoming = None

            if outgoing == "A":
                if self.deck_a.track is not None:
                    self.queue.mark_played(self.deck_a.track.metadata.id)
                self.deck_a.pause()
                # Preload next track for Deck A from queue
                next_track = self.queue.get_next_for_deck("A")
                if next_track is not None:
                    self.deck_a.load_track(next_track)

            elif outgoing == "B":
                if self.deck_b.track is not None:
                    self.queue.mark_played(self.deck_b.track.metadata.id)
                self.deck_b.pause()
                # Preload next track for Deck B from queue
                next_track = self.queue.get_next_for_deck("B")
                if next_track is not None:
                    self.deck_b.load_track(next_track)
