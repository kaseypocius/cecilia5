"""Bounded-memory audio file I/O using pyo's native libsndfile dependency."""
import ctypes
import ctypes.util
import hashlib
import os
import sys
import struct
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

BLOCK_SAMPLES = 262144  # 2 MiB per float64 audio block, regardless of channel count.


class _Info(ctypes.Structure):
    _fields_ = [('frames', ctypes.c_int64), ('samplerate', ctypes.c_int),
                ('channels', ctypes.c_int), ('format', ctypes.c_int),
                ('sections', ctypes.c_int), ('seekable', ctypes.c_int)]


@lru_cache(maxsize=1)
def _library():
    candidates = [ctypes.util.find_library('sndfile'), 'libsndfile.so.1',
                  'libsndfile.dylib', 'libsndfile-1.dll', 'sndfile.dll']
    # A bundled pyo extension can resolve its linked libsndfile symbols even
    # when the library is not installed in a system search directory.
    for module_name in ('pyo._pyo', 'pyo64._pyo64'):
        native = sys.modules.get(module_name)
        if native is not None and getattr(native, '__file__', None):
            candidates.append(native.__file__)
    errors = []
    for name in candidates:
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
            lib.sf_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(_Info)]
            lib.sf_open.restype = ctypes.c_void_p
            lib.sf_close.argtypes = [ctypes.c_void_p]
            lib.sf_close.restype = ctypes.c_int
            lib.sf_strerror.argtypes = [ctypes.c_void_p]
            lib.sf_strerror.restype = ctypes.c_char_p
            lib.sf_seek.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int]
            lib.sf_seek.restype = ctypes.c_int64
            for function in (lib.sf_readf_double, lib.sf_writef_double):
                function.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_int64]
                function.restype = ctypes.c_int64
            return lib
        except (OSError, AttributeError) as exc:
            errors.append(str(exc))
    raise RuntimeError('Streaming audio I/O requires libsndfile (already used by pyo): ' + '; '.join(errors))


@dataclass(frozen=True)
class AudioInfo:
    frames: int
    sample_rate: int
    channels: int
    format: int


class AudioReader:
    def __init__(self, path):
        self.lib = _library()
        info = _Info()
        self.handle = self.lib.sf_open(os.fsencode(path), 0x10, ctypes.byref(info))
        if not self.handle:
            raise OSError(self.lib.sf_strerror(None).decode(errors='replace'))
        self.info = AudioInfo(info.frames, info.samplerate, info.channels, info.format)
        self.position = 0

    @property
    def block_frames(self):
        return max(1, BLOCK_SAMPLES // self.info.channels)

    def seek(self, frame):
        result = self.lib.sf_seek(self.handle, int(frame), 0)
        if result != frame:
            raise OSError(f'Could not seek to audio frame {frame}')
        self.position = result

    def read(self, frames):
        frames = min(int(frames), self.info.frames - self.position)
        if frames < 0:
            raise ValueError('Invalid audio read range')
        result = np.empty((frames, self.info.channels), dtype=np.float64)
        count = self.lib.sf_readf_double(self.handle, result.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), frames)
        if count != frames:
            raise OSError(f'Incomplete audio read: expected {frames}, got {count}')
        self.position += count
        return result

    def blocks(self, start=0, frames=None):
        self.seek(start)
        remaining = self.info.frames-start if frames is None else int(frames)
        if remaining < 0 or start+remaining > self.info.frames:
            raise ValueError('Audio segment exceeds file length')
        while remaining:
            count = min(remaining, self.block_frames)
            yield self.read(count)
            remaining -= count

    def close(self):
        if self.handle:
            self.lib.sf_close(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AudioWriter:
    def __init__(self, path, sample_rate, channels, frames, fileformat=0, sampletype=3, native_format=None):
        self.lib = _library()
        self.channels = int(channels)
        self.frames = int(frames)
        self.written = 0
        majors = {0:0x010000, 1:0x020000, 2:0x030000, 4:0x160000,
                  5:0x170000, 6:0x180000, 7:0x200000}
        subtypes = {0:0x0002, 1:0x0003, 2:0x0004, 3:0x0006, 4:0x0007, 5:0x0010, 6:0x0011}
        self.format = native_format if native_format is not None else (
            majors[fileformat] | (0x0060 if fileformat == 7 else subtypes[sampletype]))
        self.bits = {2:16, 3:24, 4:32}.get(self.format & 0xffff)
        self.scale = 2**(self.bits-1) if self.bits else None
        self.clip_max = 1.0 - 2.0**(1-self.bits) if self.bits else None
        self.wav = None
        if (self.format & 0x0fff0000) == 0x010000 and self.bits:
            self.handle = None
            size = self.frames * self.channels * (self.bits // 8)
            if 36 + size + (size & 1) > 0xffffffff:
                raise ValueError('PCM RIFF export exceeds 4 GiB; use CAF or a smaller render')
            align = self.channels * (self.bits // 8)
            self.wav = open(path, 'wb')
            self.wav.write(b'RIFF'+struct.pack('<I',36+size+(size&1))+b'WAVEfmt '+
                           struct.pack('<IHHIIHH',16,1,self.channels,int(sample_rate),
                                       int(sample_rate)*align,align,self.bits)+
                           b'data'+struct.pack('<I',size))
            return
        info = _Info(0, int(sample_rate), self.channels, self.format, 0, 0)
        self.handle = self.lib.sf_open(os.fsencode(path), 0x20, ctypes.byref(info))
        if not self.handle:
            raise OSError(self.lib.sf_strerror(None).decode(errors='replace'))

    def write(self, samples):
        data = np.ascontiguousarray(samples, dtype=np.float64)
        if data.ndim != 2 or data.shape[1] != self.channels or not np.isfinite(data).all():
            raise ValueError('Invalid channel shape or non-finite audio samples')
        if self.wav is not None:
            scale = self.scale
            integers = np.clip(np.rint(data*scale),-scale,scale-1).astype('<i4')
            if self.bits == 16:
                raw = integers.astype('<i2').tobytes()
            elif self.bits == 24:
                raw = integers.view(np.uint8).reshape(-1,4)[:,:3].tobytes()
            else:
                raw = integers.tobytes()
            self.wav.write(raw)
            self.written += len(data)
            return
        if self.bits:
            data = np.clip(data, -1.0, self.clip_max)
        count = self.lib.sf_writef_double(self.handle, data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(data))
        if count != len(data):
            raise OSError(f'Incomplete audio write: expected {len(data)}, got {count}')
        self.written += count

    def close(self, check=True):
        if self.wav is not None:
            if (self.written*self.channels*(self.bits//8)) & 1:
                self.wav.write(b'\x00')
            self.wav.close()
            self.wav = None
            if check and self.written != self.frames:
                raise OSError(f'Incomplete output: expected {self.frames}, wrote {self.written}')
        if self.handle:
            status = self.lib.sf_close(self.handle)
            self.handle = None
            if check and (status != 0 or self.written != self.frames):
                raise OSError(f'Incomplete output: expected {self.frames} frames, wrote {self.written}')

    def __enter__(self):
        return self

    def __exit__(self, kind, *args):
        self.close(check=kind is None)


def audio_peak(path):
    peak = 0.0
    with AudioReader(path) as source:
        for block in source.blocks():
            if not np.isfinite(block).all():
                raise ValueError('Non-finite audio samples')
            peak = max(peak, float(np.max(np.abs(block))))
    return peak


def encoding_temp_prefix(path):
    """Identify interrupted atomic encodes belonging to one destination."""
    digest = hashlib.sha256(os.fsencode(os.path.abspath(path))).hexdigest()[:24]
    return '.cec_encode_' + digest + '_'
