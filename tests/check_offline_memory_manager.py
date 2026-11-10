"""Verify real coordinator admission, chunk scheduling and cleanup with >1 GiB inputs."""
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
from check_offline_memory import ROOT,SR,CHANNELS,fixture,rss
from check_all_modules import snapshot
from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob,apply_sound_to_snapshot
from Resources.AudioFileIO import AudioReader,audio_peak


def main():
    rows=[]
    report=ROOT/'tests/reports/offline_memory_manager.json'
    with tempfile.TemporaryDirectory(prefix='cecilia-manager-memory-') as directory:
        folder=Path(directory);small=folder/'small.wav';source=folder/'source.wav'
        fixture(small,1024**2);metadata=fixture(source,1152*1024**2)
        for relative,slot in (('Spectral/BinWarper.c5','snd'),
                              ('Resonators&Verbs/ConvolutionReverb.c5','impulse')):
            output=folder/'output.wav'
            snap=snapshot(ROOT/'Resources/modules'/relative,small)
            snap=apply_sound_to_snapshot(snap,str(source),input_name=slot)
            for item in snap['modules'][0]['settings']['userInputs'].values():item['loopMode']=1
            snap['output'].update(totalTime=4,nchnls=CHANNELS)
            events=[]
            manager=OfflineRenderManager(RenderSettings(sr=SR,nchnls=CHANNELS,buffersize=256,
                        num_threads=6,accel_mode='chunks',samp_size=3,normalize=True),
                        on_progress=lambda event:events.append(event))
            stop=threading.Event();peak=[0];pool_size=[0];limits=[0];reason=[None]
            start=time.monotonic()
            def watch():
                while not stop.wait(.025):
                    pool=manager._pool
                    if pool is not None:
                        pool_size[0]=max(pool_size[0],pool.max_workers)
                        limits[0]=max(limits[0],getattr(pool,'memory_limit_bytes',0))
                        with pool._handles_lock:handles=list(pool._all_handles)
                        resident=sum(rss(h._proc.pid) for h in handles if h._proc and h._proc.poll() is None)
                        peak[0]=max(peak[0],resident)
                        if resident>10*1024**3:reason[0]='test_memory_stop'
                    if time.monotonic()-start>300:reason[0]='test_timeout'
                    if reason[0]:manager.cancel();return
            thread=threading.Thread(target=watch,daemon=True);thread.start()
            job=RenderJob('managed','managed',str(output),snap)
            try:result=manager.run_blocking([job])
            finally:stop.set();thread.join(timeout=5)
            status=reason[0] or ('pass' if result.completed==1 else 'error')
            row={'module':relative,'input_slot':slot,'input_fixture':metadata,'requested_workers':6,
                 'pool_workers':pool_size[0],'worker_rss_limit_bytes':limits[0],
                 'sampled_worker_peak_rss_bytes':peak[0],'elapsed_seconds':time.monotonic()-start,
                 'status':status,'job_error':job.error,
                 'activity_seen':any(any(w.get('active') for w in e.get('workers',[])) for e in events)}
            if status=='pass':
                with AudioReader(output) as reader:
                    assert (reader.info.frames,reader.info.channels,reader.info.sample_rate)==(4*SR,CHANNELS,SR)
                row['peak']=audio_peak(output)
                assert 1 <= pool_size[0] <= manager.settings.num_threads,'Invalid worker allowance'
                assert row['activity_seen'],'Coordinator did not report worker activity'
                assert manager._pool is None and not manager._temp_dirs,'Coordinator left workers or scratch registrations'
            rows.append(row);report.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
            if output.exists():output.unlink()
    return int(any(row['status']!='pass' for row in rows))


if __name__=='__main__':raise SystemExit(main())
