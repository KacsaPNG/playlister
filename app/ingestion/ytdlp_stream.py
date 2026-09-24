"""
YouTube and YouTube Music Audio Ingestion Engine.
Uses yt-dlp to extract high-quality audio streams and imageio-ffmpeg to stream-decode
uncompressed 32-bit float PCM data directly into memory without intermediate video files.
Calculates ITU-R BS.1770 loudness and estimates BPM automatically.
"""
import logging
import subprocess
from typing import Callable, Optional
import imageio_ffmpeg
import numpy as np
import yt_dlp

from app.audio.buffer import AudioTrack, TrackMetadata
from app.config import DEFAULT_SAMPLE_RATE, TARGET_LUFS
from app.dsp.loudness import LoudnessAnalyzer
from app.dsp.time_stretch import BpmDetector

logger = logging.getLogger(__name__)


class YouTubeIngestor:
    """
    Automated ingestion of YouTube / YouTube Music URLs into memory PCM buffers.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.loudness_analyzer = LoudnessAnalyzer(sample_rate, target_lufs=TARGET_LUFS)
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def ingest_url(
        self,
        url: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> AudioTrack:
        """
        Extract and stream-decode audio from a YouTube or YouTube Music URL.
        progress_callback(status_text, percent_0_to_1)
        """
        if progress_callback:
            progress_callback("Resolving stream metadata with yt-dlp...", 0.1)

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                logger.error(f"Failed to extract info from {url}: {e}")
                raise RuntimeError(f"Could not extract audio metadata from URL: {e}")

        if not info:
            raise RuntimeError("No stream information returned by yt-dlp.")

        title = info.get("title", "YouTube Track")
        artist = info.get("artist") or info.get("uploader") or info.get("channel", "Unknown Artist")
        duration = float(info.get("duration", 0.0))
        thumbnail = info.get("thumbnail", "")

        # Find best audio URL
        stream_url = info.get("url")
        if not stream_url and "formats" in info:
            audio_formats = [f for f in info["formats"] if f.get("acodec") != "none"]
            if audio_formats:
                # Pick highest abr
                audio_formats.sort(key=lambda f: f.get("abr", 0) or 0, reverse=True)
                stream_url = audio_formats[0].get("url")

        if not stream_url:
            raise RuntimeError("Could not obtain direct audio stream URL.")

        if progress_callback:
            progress_callback(f"Streaming and decoding PCM: {title}...", 0.3)

        # Pipe decoded f32le PCM directly from ffmpeg stdout
        cmd = [
            self.ffmpeg_exe,
            "-v", "error",
            "-vn",
            "-i", stream_url,
            "-f", "f32le",
            "-ac", "2",
            "-ar", str(self.sample_rate),
            "-",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            raw_pcm, stderr_data = proc.communicate()
            if proc.returncode != 0:
                err_msg = stderr_data.decode("utf-8", errors="replace")
                logger.warning(f"FFmpeg returned code {proc.returncode}: {err_msg}")
                # If direct URL failed (e.g. HTTP 403 or signature issue), fallback to yt-dlp stream download
                raw_pcm = self._fallback_ytdlp_download(url, progress_callback)
        except Exception as e:
            logger.error(f"FFmpeg decoding failed: {e}")
            raw_pcm = self._fallback_ytdlp_download(url, progress_callback)

        if not raw_pcm or len(raw_pcm) < 4:
            raise RuntimeError("Decoded audio stream is empty.")

        # Convert bytes to 32-bit float stereo array
        pcm_array = np.frombuffer(raw_pcm, dtype=np.float32).reshape((-1, 2))

        if progress_callback:
            progress_callback("Analyzing ITU-R BS.1770 loudness and BPM...", 0.8)

        # Run loudness normalization analysis
        loudness_report = self.loudness_analyzer.analyze(pcm_array)

        # Detect BPM
        bpm = BpmDetector.estimate_bpm(pcm_array, self.sample_rate)

        metadata = TrackMetadata(
            title=title,
            artist=artist,
            duration_sec=len(pcm_array) / float(self.sample_rate),
            source_url=url,
            thumbnail_url=thumbnail,
            bpm=bpm,
            loudness_lufs=loudness_report.integrated_lufs,
            true_peak_db=loudness_report.true_peak_db,
            auto_gain_db=loudness_report.recommended_gain_db,
        )

        if progress_callback:
            progress_callback("Track ready.", 1.0)

        return AudioTrack(pcm_array, self.sample_rate, metadata)

    def _fallback_ytdlp_download(
        self,
        url: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> bytes:
        """Fallback method: download best audio to memory via stdout using yt-dlp pipe."""
        if progress_callback:
            progress_callback("Streaming via yt-dlp pipe...", 0.4)

        cmd = [
            "yt-dlp",
            "-q", "--no-warnings",
            "-f", "bestaudio/best",
            "-o", "-",
            url,
        ]
        ytdlp_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        ffmpeg_cmd = [
            self.ffmpeg_exe,
            "-v", "error",
            "-vn",
            "-i", "pipe:0",
            "-f", "f32le",
            "-ac", "2",
            "-ar", str(self.sample_rate),
            "-",
        ]
        ff_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=ytdlp_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ytdlp_proc.stdout.close()
        raw_pcm, _ = ff_proc.communicate()
        return raw_pcm
