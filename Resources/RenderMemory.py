"""Conservative admission estimates for table-based offline DSP workers.

Output length is deliberately absent: post-processing streams audio in blocks.
Native module scratch buffers can exceed these estimates; this is not an allocator
limit or a guarantee that an arbitrary user module will fit.
"""
import os
import math
import re
import subprocess
import sys
import threading

MIB = 1024**2


def render_memory_budget():
    """Budget memory for offline render workers.

    Defaults to at most 75% of physical RAM and 85% of currently available RAM,
    allowing concurrency to scale up to available resources while preventing
    system memory exhaustion.

    Supports overrides via:
      - CECILIA_RAM_BUDGET_BYTES: absolute byte budget
      - CECILIA_RAM_BUDGET_MB: absolute MB budget
      - CECILIA_RAM_BUDGET_GB: absolute GB budget
      - CECILIA_RAM_BUDGET_FRACTION: custom fraction (0.05 - 1.0) of system/free RAM
      - Preferences: offlineRamBudgetMB / offlineRamBudgetFraction
    """
    # 1. Environment variable byte/MB/GB overrides
    env_bytes = os.environ.get("CECILIA_RAM_BUDGET_BYTES")
    if env_bytes:
        try:
            val = int(env_bytes)
            if val > 0:
                return max(256 * MIB, val)
        except ValueError:
            pass

    env_mb = os.environ.get("CECILIA_RAM_BUDGET_MB")
    if env_mb:
        try:
            val = float(env_mb)
            if val > 0:
                return max(256 * MIB, int(val * MIB))
        except ValueError:
            pass

    env_gb = os.environ.get("CECILIA_RAM_BUDGET_GB")
    if env_gb:
        try:
            val = float(env_gb)
            if val > 0:
                return max(256 * MIB, int(val * 1024 * MIB))
        except ValueError:
            pass

    # 2. Preference variable override in CeciliaLib (if loaded)
    cecilia_lib = sys.modules.get('Resources.CeciliaLib')
    if cecilia_lib and hasattr(cecilia_lib, "getVar"):
        try:
            pref_mb = cecilia_lib.getVar("offlineRamBudgetMB")
            if pref_mb and int(pref_mb) > 0:
                return max(256 * MIB, int(pref_mb) * MIB)
        except Exception:
            pass

    # 3. Fraction determination (default: 75% physical, 85% available)
    phys_frac = 0.75
    avail_frac = 0.85
    env_frac = os.environ.get("CECILIA_RAM_BUDGET_FRACTION")
    if env_frac:
        try:
            f = float(env_frac)
            if 0.05 <= f <= 1.0:
                phys_frac = avail_frac = f
        except ValueError:
            pass
    elif cecilia_lib and hasattr(cecilia_lib, "getVar"):
        try:
            pref_frac = cecilia_lib.getVar("offlineRamBudgetFraction")
            if pref_frac:
                f = float(pref_frac)
                if 0.05 <= f <= 1.0:
                    phys_frac = avail_frac = f
        except Exception:
            pass

    total = available = None
    try:
        if sys.platform == 'darwin':
            report = subprocess.check_output(['memory_pressure', '-Q'], text=True, timeout=2)
            match = re.search(r'system has (\d+)', report)
            free = re.search(r'free percentage:\s*(\d+)%', report)
            if match:
                total = int(match.group(1))
                if free:
                    available = total * int(free.group(1)) // 100
        elif sys.platform.startswith('linux'):
            with open('/proc/meminfo') as stream:
                values = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in stream}
            total, available = values['MemTotal'], values['MemAvailable']
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass

    if total is None:
        try:
            total = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
        except (AttributeError, ValueError, OSError):
            return 8 * 1024**3

    if available is not None:
        budget = min(int(total * phys_frac), int(available * avail_frac))
    else:
        budget = int(total * phys_frac)

    return max(256 * MIB, budget)


def delay_buffer_seconds(maximum, values, sample_rate):
    """Bound fixed offline controls; unknown/automated values need full capacity."""
    if not values or any(value is None for value in values):
        return maximum
    try:
        values = [float(value) for value in values]
        if any(not math.isfinite(value) or value < 0 for value in values):
            return maximum
        return min(maximum, max(values) + 4/float(sample_rate))
    except (ValueError, TypeError, ZeroDivisionError):
        return maximum


def estimate_snapshot_memory(snapshot, output_channels, sample_rate=None):
    """Include decoded inputs, mono cfilein replication, and native-copy headroom."""
    from .AudioFileIO import AudioReader
    # File encoding (16/24/32-bit PCM) does not determine native table precision.
    # Normal pyo tables are float32; pyo64 tables use float64. Keep the larger
    # analysis/IR allowances until those module-specific buffers are measured.
    sample_bytes = 4
    lib = sys.modules.get('Resources.CeciliaLib')
    if lib is not None:
        try:
            if lib.getVar('samplePrecision') == '64 bit':
                sample_bytes = 8
        except (AttributeError, KeyError):
            pass
    working_set = 0
    rate = int(sample_rate or snapshot.get('output', {}).get('sr', 44100))
    for module in snapshot.get('modules',[]):
        module_name = os.path.basename(module.get('module_path',''))
        # Delay capacity grows with output sample rate/channel count, even for
        # a tiny input. Include the largest fixed delay banks in shipped modules.
        delay_seconds = {'4Delays.c5': 20, 'DelayMod.c5': 20,
                         'BucketBrigadeDevice.c5': 4, 'DetunedResonators.c5': 8,
                         'Resonators.c5': .4}.get(module_name, 0)
        if module_name == 'WGuideBank.c5':
            # Its existing graph builds 8*C pitches and duplicates each C
            # times: 8*C*C waveguides, each reserving 1/minfreq seconds.
            # Preserve that sound here; admission must account for the graph
            # it actually constructs, rather than assuming linear scaling.
            delay_seconds = .8*output_channels
        if module_name == 'MultiBandDelay.c5':
            sliders = module.get('settings', {}).get('userSliders', {})
            controls = [sliders.get(name, [value, 0]) for name, value in
                        [('del1', .5), ('del2', .25), ('del3', .33), ('del4', .66)]]
            values = [state[0] if len(state) > 1 and not state[1] else None for state in controls]
            delay_seconds = 4*delay_buffer_seconds(15, values, rate)
        working_set += int(delay_seconds*rate*output_channels*sample_bytes)
        for name, slot in module.get('settings',{}).get('userInputs',{}).items():
            path = slot.get('path')
            if int(slot.get('mode',0)) != 0 or not path or not os.path.isfile(path):
                continue
            try:
                with AudioReader(path) as source:
                    info = source.info
                frames = max(0, info.frames-int(float(slot.get('off'+name,0))*info.sample_rate))
                channels = output_channels if info.channels == 1 and slot.get('type') == 'cfilein' else info.channels
                copies = 2
                native_bytes = sample_bytes
                if module_name in ('BinWarper.c5','SpectralWarper.c5'):
                    # Full-input spectral histories exist for every output stream.
                    channels = max(channels, output_channels)
                    copies = 3
                    native_bytes = 8
                elif module_name == 'ConvolutionReverb.c5' and name == 'impulse':
                    # Partitioned IR filters are replicated for output streams.
                    channels = max(channels, output_channels)
                    copies = 4
                    native_bytes = 8
                working_set += frames*channels*native_bytes*copies
            except (OSError,ValueError,RuntimeError):
                continue # normal worker error reporting handles an unreadable file
    return 256*MIB + working_set


def worker_limit(estimates, requested, budget):
    return max(1,min(int(requested),int(budget)//max([256*MIB,*estimates])))


def batch_worker_limit(estimates, requested, budget):
    """Allow small independent jobs to run together despite a large queue item.

    Runtime reservations enforce each actual combination. A lone oversized job
    can still be attempted with the resident-memory guard.
    """
    used = count = 0
    for estimate in sorted(estimates)[:max(1, int(requested))]:
        estimate = max(256*MIB, int(estimate))
        if used + estimate > budget:
            break
        used += estimate
        count += 1
    return max(1, count)


class MemoryReservations:
    """Admit tasks by their own estimates instead of dividing RAM into slots."""

    def __init__(self, budget):
        self.budget = int(budget)
        self.used = 0
        self._condition = threading.Condition()

    def acquire(self, estimate, cancel_event):
        amount = min(self.budget, max(256*MIB, int(estimate)))
        with self._condition:
            while self.used + amount > self.budget:
                if cancel_event.is_set():
                    raise InterruptedError('Render cancelled.')
                self._condition.wait(.05)
            if cancel_event.is_set():
                raise InterruptedError('Render cancelled.')
            self.used += amount
        return amount

    def release(self, amount):
        with self._condition:
            self.used -= amount
            self._condition.notify_all()


def process_rss(pid):
    """Read a worker's resident bytes without importing optional packages."""
    try:
        if sys.platform == 'darwin':
            import ctypes
            import struct
            lib = ctypes.CDLL('/usr/lib/libproc.dylib')
            lib.proc_pidinfo.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
            buffer = ctypes.create_string_buffer(128)
            if lib.proc_pidinfo(pid,4,0,buffer,128) >= 16:
                return struct.unpack_from('Q',buffer.raw,8)[0]
        elif sys.platform.startswith('linux'):
            with open(f'/proc/{pid}/statm') as stream:
                return int(stream.read().split()[1])*os.sysconf('SC_PAGE_SIZE')
    except (OSError,ValueError,IndexError):
        pass
    return None
