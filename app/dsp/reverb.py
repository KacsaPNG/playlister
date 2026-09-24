"""
Algorithmic DSP Reverb Unit (Schroeder / Freeverb Architecture).
High-performance block-based stereo reverb with 8 parallel Lowpass Feedback Comb Filters
and 4 series All-Pass diffusion stages per channel.
"""
import numpy as np


class ReverbUnit:
    """
    Studio-grade algorithmic stereo reverb unit for DJ Decks.
    Features adjustable room size, high-frequency damping, stereo width,
    and smooth wet/dry mix controls.
    """

    # Prime delay lengths at 44.1 kHz
    COMB_TUNINGS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
    ALLPASS_TUNINGS = [556, 441, 341, 225]
    STEREO_SPREAD = 23

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        scale = sample_rate / 44100.0

        # Delay lengths
        self.comb_delays_L = [max(16, int(d * scale)) for d in self.COMB_TUNINGS]
        self.comb_delays_R = [max(16, int((d + self.STEREO_SPREAD) * scale)) for d in self.COMB_TUNINGS]
        self.ap_delays_L = [max(8, int(d * scale)) for d in self.ALLPASS_TUNINGS]
        self.ap_delays_R = [max(8, int((d + self.STEREO_SPREAD) * scale)) for d in self.ALLPASS_TUNINGS]

        # Circular buffers
        self.comb_bufs_L = [np.zeros(d, dtype=np.float32) for d in self.comb_delays_L]
        self.comb_bufs_R = [np.zeros(d, dtype=np.float32) for d in self.comb_delays_R]
        self.comb_idx_L = [0] * 8
        self.comb_idx_R = [0] * 8

        self.ap_bufs_L = [np.zeros(d, dtype=np.float32) for d in self.ap_delays_L]
        self.ap_bufs_R = [np.zeros(d, dtype=np.float32) for d in self.ap_delays_R]
        self.ap_idx_L = [0] * 4
        self.ap_idx_R = [0] * 4

        # Damping memory
        self.comb_damp_store_L = np.zeros(8, dtype=np.float32)
        self.comb_damp_store_R = np.zeros(8, dtype=np.float32)

        # Controls
        self._enabled = False
        self._wet = 0.35
        self._room_size = 0.75
        self._damping = 0.25
        self._width = 1.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool):
        self._enabled = bool(val)

    @property
    def wet(self) -> float:
        return self._wet

    @wet.setter
    def wet(self, val: float):
        self._wet = float(np.clip(val, 0.0, 1.0))

    @property
    def room_size(self) -> float:
        return self._room_size

    @room_size.setter
    def room_size(self, val: float):
        self._room_size = float(np.clip(val, 0.0, 0.98))

    @property
    def damping(self) -> float:
        return self._damping

    @damping.setter
    def damping(self, val: float):
        self._damping = float(np.clip(val, 0.0, 0.9))

    def reset_state(self):
        """Clear delay lines and filter memory."""
        for buf in self.comb_bufs_L:
            buf.fill(0)
        for buf in self.comb_bufs_R:
            buf.fill(0)
        for buf in self.ap_bufs_L:
            buf.fill(0)
        for buf in self.ap_bufs_R:
            buf.fill(0)
        self.comb_idx_L = [0] * 8
        self.comb_idx_R = [0] * 8
        self.ap_idx_L = [0] * 4
        self.ap_idx_R = [0] * 4
        self.comb_damp_store_L.fill(0)
        self.comb_damp_store_R.fill(0)

    def reset_defaults(self):
        """Restore all reverb parameters to factory defaults and clear memory."""
        self._enabled = False
        self._wet = 0.35
        self._room_size = 0.75
        self._damping = 0.25
        self._width = 1.0
        self.reset_state()

    def _process_comb(self, x: np.ndarray, buf: np.ndarray, idx: int, delay: int) -> tuple[np.ndarray, int]:
        """Vectorized Lowpass Feedback Comb Filter."""
        N = len(x)
        out = np.zeros(N, dtype=np.float32)
        pos = 0
        fb = 0.7 + (self._room_size * 0.28)
        damp = self._damping
        cur_idx = idx

        while pos < N:
            chunk = min(N - pos, delay)
            end = cur_idx + chunk
            if end <= delay:
                read_chunk = buf[cur_idx:end]
                out[pos:pos + chunk] = read_chunk
                buf[cur_idx:end] = x[pos:pos + chunk] + (read_chunk * fb * (1.0 - damp))
                cur_idx = (cur_idx + chunk) % delay
            else:
                n1 = delay - cur_idx
                n2 = chunk - n1
                read_chunk = np.concatenate([buf[cur_idx:], buf[:n2]])
                out[pos:pos + chunk] = read_chunk
                buf[cur_idx:] = x[pos:pos + n1] + (read_chunk[:n1] * fb * (1.0 - damp))
                buf[:n2] = x[pos + n1:pos + chunk] + (read_chunk[n1:] * fb * (1.0 - damp))
                cur_idx = n2
            pos += chunk
        return out, cur_idx

    def _process_allpass(self, x: np.ndarray, buf: np.ndarray, idx: int, delay: int) -> tuple[np.ndarray, int]:
        """Vectorized All-Pass Diffusion Filter."""
        N = len(x)
        out = np.zeros(N, dtype=np.float32)
        pos = 0
        cur_idx = idx
        g = 0.5

        while pos < N:
            chunk = min(N - pos, delay)
            end = cur_idx + chunk
            if end <= delay:
                buf_chunk = buf[cur_idx:end]
                x_chunk = x[pos:pos + chunk]
                # y[n] = -g*x[n] + buf[n]
                y_chunk = -g * x_chunk + buf_chunk
                out[pos:pos + chunk] = y_chunk
                # update buf: x[n] + g*y[n]
                buf[cur_idx:end] = x_chunk + (g * y_chunk)
                cur_idx = (cur_idx + chunk) % delay
            else:
                n1 = delay - cur_idx
                n2 = chunk - n1
                buf_chunk = np.concatenate([buf[cur_idx:], buf[:n2]])
                x_chunk = x[pos:pos + chunk]
                y_chunk = -g * x_chunk + buf_chunk
                out[pos:pos + chunk] = y_chunk
                new_buf = x_chunk + (g * y_chunk)
                buf[cur_idx:] = new_buf[:n1]
                buf[:n2] = new_buf[n1:]
                cur_idx = n2
            pos += chunk
        return out, cur_idx

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Process a stereo block x with shape (N, 2).
        Returns wet/dry blended audio.
        """
        if not self._enabled or self._wet <= 0.001 or x.shape[0] == 0:
            return x

        N = x.shape[0]
        # Mono mixdown for reverb injection
        mono = 0.5 * (x[:, 0] + x[:, 1])

        # 8 Parallel Comb Filters
        comb_out_L = np.zeros(N, dtype=np.float32)
        comb_out_R = np.zeros(N, dtype=np.float32)

        for i in range(8):
            cL, self.comb_idx_L[i] = self._process_comb(mono, self.comb_bufs_L[i], self.comb_idx_L[i], self.comb_delays_L[i])
            cR, self.comb_idx_R[i] = self._process_comb(mono, self.comb_bufs_R[i], self.comb_idx_R[i], self.comb_delays_R[i])
            comb_out_L += cL
            comb_out_R += cR

        # Scale down comb summation
        rev_L = comb_out_L * 0.125
        rev_R = comb_out_R * 0.125

        # 4 Series All-Pass Diffusion Stages
        for i in range(4):
            rev_L, self.ap_idx_L[i] = self._process_allpass(rev_L, self.ap_bufs_L[i], self.ap_idx_L[i], self.ap_delays_L[i])
            rev_R, self.ap_idx_R[i] = self._process_allpass(rev_R, self.ap_bufs_R[i], self.ap_idx_R[i], self.ap_delays_R[i])

        # Stereo width adjustment
        wet_1 = self._wet * (self._width * 0.5 + 0.5)
        wet_2 = self._wet * ((1.0 - self._width) * 0.5)
        dry = 1.0 - (self._wet * 0.5)

        out = np.empty_like(x)
        out[:, 0] = dry * x[:, 0] + wet_1 * rev_L + wet_2 * rev_R
        out[:, 1] = dry * x[:, 1] + wet_1 * rev_R + wet_2 * rev_L
        return out
