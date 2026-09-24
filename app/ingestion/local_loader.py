"""
Local Audio File Loader.
Supports WAV, FLAC, OGG, MP3, AAC, M4A, and AIFF.
Decodes via soundfile with ffmpeg fallback, resamples to engine sample rate,
normalizes stereo channels, and performs BS.1770 loudness analysis.
"""
from pathlib import Path
import logging
import subprocess
from typing import Optional, Callable
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from scipy import signal

from app.audio.buffer import AudioTrack, TrackMetadata
from app.config import DEFAULT_SAMPLE_RATE, TARGET_LUFS
from app.dsp.loudness import LoudnessAnalyzer
from app.dsp.time_stretch import BpmDetector

logger = logging.getLogger(__name__)


class LocalAudioLoader:
    """
    Decodes local audio files into uncompressed 32-bit float stereo PCM AudioTrack buffers.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.loudness_analyzer = LoudnessAnalyzer(sample_rate, target_lufs=TARGET_LUFS)
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def load_file(
        self,
        file_path: str | Path,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> AudioTrack:
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {path}")

        if progress_callback:
            progress_callback(f"Loading {path.name}...", 0.2)

        pcm = None
        sr = self.sample_rate

        # 1. Try reading with soundfile first
        try:
            data, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
            pcm = data
            sr = file_sr
        except Exception as sf_err:
            logger.debug(f"soundfile could not read {path} ({sf_err}), trying ffmpeg...")

        # 2. If soundfile failed (e.g. m4a/aac/mp3 without libsndfile mp3 support), use ffmpeg
        if pcm is None:
            cmd = [
                self.ffmpeg_exe,
                "-v", "error",
                "-vn",
                "-i", str(path),
                "-f", "f32le",
                "-ac", "2",
                "-ar", str(self.sample_rate),
                "-",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                raise RuntimeError(f"Failed to decode audio file {path.name}: {proc.stderr.decode('utf-8', errors='replace')}")
            pcm = np.frombuffer(proc.stdout, dtype=np.float32).reshape((-1, 2))
            sr = self.sample_rate

        # 3. Resample if necessary
        if sr != self.sample_rate:
            if progress_callback:
                progress_callback("Resampling to engine sample rate...", 0.5)
            num_output = int(round(len(pcm) * float(self.sample_rate) / sr))
            resampled = signal.resample(pcm, num_output, axis=0).astype(np.float32)
            pcm = resampled

        # Ensure stereo
        if pcm.shape[1] == 1:
            pcm = np.repeat(pcm, 2, axis=1)
        elif pcm.shape[1] > 2:
            pcm = pcm[:, :2]

        if progress_callback:
            progress_callback("Analyzing loudness and BPM...", 0.7)

        # BS.1770 Loudness
        loudness_report = self.loudness_analyzer.analyze(pcm)

        # BPM Detection
        bpm = BpmDetector.estimate_bpm(pcm, self.sample_rate)

        # Title from filename
        title = path.stem
        artist = "Local Library"
        if " - " in title:
            parts = title.split(" - ", 1)
            artist, title = parts[0].strip(), parts[1].strip()

        metadata = TrackMetadata(
            title=title,
            artist=artist,
            duration_sec=len(pcm) / float(self.sample_rate),
            source_url=str(path),
            bpm=bpm,
            loudness_lufs=loudness_report.integrated_lufs,
            true_peak_db=loudness_report.true_peak_db,
            auto_gain_db=loudness_report.recommended_gain_db,
        )

        if progress_callback:
            progress_callback("Loaded.", 1.0)

        return AudioTrack(pcm, self.sample_rate, metadata)
