"""Serial native offline stress audit with physical audio, RSS watchdog and JSONL evidence.

Run: cecillia/bin/python tests/check_offline_memory.py
Each native job runs in a fresh child; no worker pool is used. macOS RSS is sampled
externally so a native call holding the GIL cannot prevent memory-limit enforcement.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from offline_memory_sources import same_native_sources

SIZES = (1024**2, 64*1024**2, 1024**3, 1152*1024**2)
SR = 48000
CHANNELS = 8


def fingerprint(module):
    paths = [module, ROOT/'Resources/OfflineRender.py', ROOT/'Resources/AudioFileIO.py', ROOT/'Resources/audio.py']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def fixture(path, size):
    import numpy as np
    frames = size // (CHANNELS*4)
    size = frames*CHANNELS*4
    with open(path, 'wb') as stream:
        stream.write(b'RIFF'+struct.pack('<I',36+size)+b'WAVEfmt '+
                     struct.pack('<IHHIIHH',16,3,CHANNELS,SR,SR*CHANNELS*4,CHANNELS*4,32)+
                     b'data'+struct.pack('<I',size))
        t = np.arange(16384)/SR
        block = np.array([.04*np.sin(2*np.pi*(137+113*c)*t) for c in range(CHANNELS)],dtype='<f4').T.copy().tobytes()
        remaining = size
        while remaining:
            part = block[:min(remaining,len(block))]
            stream.write(part)
            remaining -= len(part)
    return {'bytes':path.stat().st_size, 'allocated_bytes':path.stat().st_blocks*512, 'frames':frames}


def child(spec_path):
    from check_all_modules import snapshot, inputs_for
    from Resources.OfflineRender import _HeadlessRenderWorker, apply_sound_to_snapshot, normalize_audio_file
    from Resources.AudioFileIO import AudioReader, audio_peak
    import resource
    spec = json.loads(Path(spec_path).read_text())
    module = Path(spec['module'])
    snap = snapshot(module, spec['small'])
    names = list(inputs_for(module))
    if names:
        snap = apply_sound_to_snapshot(snap, spec['input'], input_name=spec.get('input_slot') or names[0])
    for slot in snap['modules'][0]['settings']['userInputs'].values():
        slot['loopMode'] = 1
    frames = spec['frames']
    snap['output'].update(totalTime=frames/SR, nchnls=CHANNELS)
    native = _HeadlessRenderWorker(lambda event: None)
    result = native.render_snapshot({'job_id':'memory', 'snapshot':snap,
        'output_path':spec['output'], 'duration_override':frames/SR, 'nchnls_override':CHANNELS,
        'sr':SR, 'buffersize':256, 'audio_file_type':'wav', 'samp_size':3,
        'global_fade':.005, 'master_output':True, 'scratch_dir':spec['scratch'], 'module_outputs':{}})
    normalize_audio_file(spec['output'], -1, sr=SR, fileformat=0, sampletype=3)
    with AudioReader(spec['output']) as reader:
        info = reader.info
        if (info.frames, info.channels, info.sample_rate) != (frames,CHANNELS,SR):
            raise AssertionError(f'Wrong audio metadata: {info}')
    peak = audio_peak(spec['output']) # scans every sample, rejects NaN/Inf
    stat = os.stat(spec['output'])
    print('MEMORY_RESULT '+json.dumps({'frames':info.frames, 'channels':info.channels,
          'output_bytes':stat.st_size, 'allocated_output_bytes':stat.st_blocks*512,
          'peak':peak, 'silent':peak < 1e-8,
          'child_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


def rss(pid):
    if sys.platform == 'darwin':
        lib = ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
        lib.proc_pidinfo.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
        buf = ctypes.create_string_buffer(128)
        if lib.proc_pidinfo(pid,4,0,buf,128) >= 16:
            return struct.unpack_from('Q',buf.raw,8)[0]
        return 0
    try:
        return int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    except (OSError,IndexError):
        return 0


def run_case(spec, folder, timeout, memory_limit, cancel_event=None):
    request = folder/'request.json'
    request.write_text(json.dumps(spec))
    before = fingerprint(Path(spec['module']))
    start = time.monotonic()
    peak = 0
    status = None
    with (folder/'child.log').open('w+') as log:
        process = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--child',str(request)],
                                   cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        (folder/'child.pid').write_text(str(process.pid))
        try:
            while process.poll() is None:
                peak = max(peak,rss(process.pid))
                if cancel_event is not None and cancel_event.is_set():
                    status = 'cancelled'
                elif peak > memory_limit:
                    status = 'memory_limit'
                elif time.monotonic()-start > timeout:
                    status = 'timeout'
                if status:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    break
                time.sleep(.025)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        log.seek(0)
        output = log.read()
    details = None
    for line in output.splitlines():
        if line.startswith('MEMORY_RESULT '):
            details = json.loads(line[len('MEMORY_RESULT '):])
    changed = not same_native_sources(before, fingerprint(Path(spec['module'])))
    return {'status': status or ('pass' if process.returncode == 0 and details else 'error'),
            'elapsed_seconds':round(time.monotonic()-start,3), 'sampled_peak_rss_bytes':peak,
            'rss_limit_bytes':memory_limit, 'timeout_seconds':timeout,
            'returncode':process.returncode, 'result':details, 'error_tail':output[-3000:] if not details else '',
            'source_hashes':before, 'source_changed_during_case':changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child')
    parser.add_argument('--timeout',type=float,default=120)
    parser.add_argument('--memory-mib',type=int,default=3072)
    parser.add_argument('--sizes',default=','.join(str(s) for s in SIZES))
    parser.add_argument('--module',default='')
    parser.add_argument('--direction',choices=['input','output','both'],default='both')
    parser.add_argument('--report',default='tests/reports/offline_memory.jsonl')
    parser.add_argument('--resume',action='store_true',help='Skip cases with unchanged source fingerprints')
    parser.add_argument('--retry-status',action='append',default=[])
    args = parser.parse_args()
    if args.child:
        child(args.child)
        return
    from check_all_modules import inputs_for
    modules = sorted(p for p in (ROOT/'Resources/modules').rglob('*.c5') if args.module in str(p.relative_to(ROOT/'Resources/modules')))
    report = ROOT/args.report
    report.parent.mkdir(exist_ok=True)
    previous = {}
    if args.resume and report.exists():
        for line in report.read_text().splitlines():
            row = json.loads(line)
            previous[(row['module'],row['direction'],row['target_audio_bytes'])] = row
    with tempfile.TemporaryDirectory(prefix='cecilia-memory-') as directory:
        folder = Path(directory)
        small = folder/'small.wav'
        fixture(small,1024**2)
        for size in map(int,args.sizes.split(',')):
            source = folder/'source.wav'
            if shutil.disk_usage(folder).free < max(5*1024**3,size*5):
                raise RuntimeError('Insufficient disk headroom for safe audit')
            source_info = fixture(source,size) if args.direction != 'output' else None
            for module in modules:
                for direction in ('input','output'):
                    if args.direction not in ('both',direction):
                        continue
                    key = (str(module.relative_to(ROOT/'Resources/modules')),direction,size)
                    prior = previous.get(key)
                    if prior and prior['status'] not in args.retry_status:
                        if prior['status']=='not_applicable' or (not prior.get('source_changed_during_case',False)
                                and same_native_sources(prior.get('source_hashes',{}),fingerprint(module))):
                            continue
                    if direction == 'input' and not inputs_for(module):
                        row = {'module':str(module.relative_to(ROOT/'Resources/modules')),'direction':direction,
                               'target_audio_bytes':size,'status':'not_applicable','reason':'Module has no file input'}
                    else:
                        scratch = folder/'job'
                        scratch.mkdir()
                        spec = {'module':str(module),'small':str(small),
                                'input':str(source if direction=='input' else small),
                                'output':str(scratch/'output.wav'),'scratch':str(scratch),
                                'frames':SR if direction=='input' else size//(CHANNELS*4)}
                        try:
                            row = run_case(spec,scratch,args.timeout,args.memory_mib*1024**2)
                        finally:
                            shutil.rmtree(scratch)
                        row.update(module=str(module.relative_to(ROOT/'Resources/modules')),direction=direction,
                                   target_audio_bytes=size, input_fixture=source_info if direction=='input' else None)
                    with report.open('a') as stream:
                        stream.write(json.dumps(row)+'\n')
                    print(json.dumps({k:row.get(k) for k in ('module','direction','target_audio_bytes','status','elapsed_seconds','sampled_peak_rss_bytes')}),flush=True)
            if source.exists():
                source.unlink()


if __name__ == '__main__':
    main()
