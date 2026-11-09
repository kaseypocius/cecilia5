"""Reproduce a 402s/48kHz/50ch source -> 60s/96kHz/50ch MultiBandDelay render.

Uses generated dense float32 audio, init parameters, Auto mode, six requested
workers, and a 600-second external watchdog. No user audio is accessed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from check_all_modules import snapshot
from check_offline_memory import rss
from Resources.AudioFileIO import AudioReader,AudioWriter,audio_peak
from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob
from Resources.RenderMemory import estimate_snapshot_memory
import numpy as np

CHANNELS=50
INPUT_SR=48000
OUTPUT_SR=96000
INPUT_SECONDS=402
OUTPUT_SECONDS=60


def hashes():
    paths=['Resources/OfflineRender.py','Resources/OfflineRenderDialog.py','Resources/RenderMemory.py',
           'Resources/AudioFileIO.py','Resources/audio.py','Resources/modules/Multiband/MultiBandDelay.c5']
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}


def main():
    report=ROOT/'tests/reports/multiband_delay_50ch_48k_96k.json'
    data_bytes=INPUT_SR*INPUT_SECONDS*CHANNELS*4
    if shutil.disk_usage(tempfile.gettempdir()).free < data_bytes+2*OUTPUT_SR*OUTPUT_SECONDS*CHANNELS*4+4*1024**3:
        raise RuntimeError('Insufficient disk headroom for the reproduction')
    before=hashes()
    with tempfile.TemporaryDirectory(prefix='cecilia-50ch-delay-') as directory:
        folder=Path(directory);source=folder/'source.wav';target=folder/'output.wav'
        frequencies=130+30*np.arange(CHANNELS)
        t=np.arange(INPUT_SR//10)/INPUT_SR
        block=.04*np.sin(2*np.pi*t[:,None]*frequencies[None,:])
        with AudioWriter(source,INPUT_SR,CHANNELS,INPUT_SR*INPUT_SECONDS) as writer:
            for _ in range(INPUT_SECONDS*10):writer.write(block)
        stat=source.stat()
        source_meta={'frames':INPUT_SR*INPUT_SECONDS,'sample_rate':INPUT_SR,'channels':CHANNELS,
                     'bytes':stat.st_size,'allocated_bytes':stat.st_blocks*512}
        print(json.dumps({'stage':'fixture_ready','input':source_meta}),flush=True)
        snap=snapshot(ROOT/'Resources/modules/Multiband/MultiBandDelay.c5',source)
        snap['output'].update(totalTime=OUTPUT_SECONDS,nchnls=CHANNELS)
        settings=RenderSettings(sr=OUTPUT_SR,nchnls=CHANNELS,buffersize=256,num_threads=6,
                                accel_mode='auto',samp_size=3,normalize=False)
        events=[];pool_sizes=[];budget=[];peak=[0];reason=[None];pids=set()
        manager=OfflineRenderManager(settings,on_progress=events.append)
        stopped=threading.Event();start=time.monotonic()
        def watch():
            last_print=0
            while not stopped.wait(.025):
                pool=manager._pool
                resident=0
                if pool:
                    pool_sizes.append(pool.max_workers)
                    budget.append(pool.memory_limit_bytes)
                    with pool._handles_lock:handles=list(pool._all_handles)
                    for handle in handles:
                        process=handle._proc
                        if process and process.poll() is None:
                            pids.add(process.pid);resident+=rss(process.pid)
                    peak[0]=max(peak[0],resident)
                elapsed=time.monotonic()-start
                if resident>11*1024**3:reason[0]='external_memory_stop'
                if elapsed>600:reason[0]='external_timeout'
                if reason[0]:manager.cancel();return
                if elapsed-last_print>=15:
                    last_print=elapsed
                    print(json.dumps({'stage':'rendering','seconds':round(elapsed,1),
                        'worker_rss_bytes':resident,'output_bytes':target.stat().st_size if target.exists() else 0}),flush=True)
        thread=threading.Thread(target=watch,daemon=True);thread.start()
        job=RenderJob('50ch','MultiBandDelay 50ch 48k to 96k',str(target),snap)
        try:result=manager.run_blocking([job])
        finally:stopped.set();thread.join(timeout=5)
        row={'status':reason[0] or ('pass' if result.completed==1 and result.failed==0 else 'error'),
             'error':job.error,'input':source_meta,'output_seconds':OUTPUT_SECONDS,
             'requested_workers':6,'accel_mode':'auto','preset':'init','sample_type':'float32',
             'estimated_memory_bytes':estimate_snapshot_memory(snap,CHANNELS),
             'worker_rss_limit_bytes':max(budget,default=0),'pool_workers':max(pool_sizes,default=0),
             'sampled_worker_peak_rss_bytes':peak[0],'elapsed_seconds':time.monotonic()-start,
             'worker_pids':sorted(pids),'activity_seen':any(any(w.get('active') for w in e.get('workers',[])) for e in events),
             'source_hashes':before,'source_changed':before!=hashes()}
        if row['status']=='pass':
            with AudioReader(target) as reader:
                info=reader.info
                assert (info.frames,info.sample_rate,info.channels)==(OUTPUT_SR*OUTPUT_SECONDS,OUTPUT_SR,CHANNELS),info
                reader.seek(30*OUTPUT_SR)
                samples=reader.read(OUTPUT_SR)
            spectra=np.abs(np.fft.rfft(samples,axis=0))
            detected=np.argmax(spectra[1:],axis=0)+1
            errors=abs(detected-frequencies)
            assert np.all(errors<=1),f'Channel/pitch mismatch: {detected.tolist()}'
            peak_amp=audio_peak(target)
            assert peak_amp>1e-7,'Silent output'
            assert max(pool_sizes)==1,'Expected a single monitored worker'
            assert row['activity_seen']
            assert manager._pool is None and not manager._temp_dirs
            row.update(output_frames=info.frames,output_sample_rate=info.sample_rate,output_channels=info.channels,
                       output_bytes=target.stat().st_size,allocated_output_bytes=target.stat().st_blocks*512,
                       peak=peak_amp,detected_frequencies_hz=detected.tolist(),max_frequency_error_hz=int(errors.max()))
        report.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
    return int(row['status']!='pass' or row['source_changed'])


if __name__=='__main__':raise SystemExit(main())
