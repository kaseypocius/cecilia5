"""Long-output retries: two small-input children, 512 MiB RSS/600 seconds each."""
import concurrent.futures
import json
from pathlib import Path
import shutil
import tempfile
import threading
from check_offline_memory import ROOT,CHANNELS,fixture,run_case

MODULES=('Dynamics/UpDistoRes.c5','Pitch/LooperBank.c5',
         'Resonators&Verbs/Convolve.c5','Resonators&Verbs/WGuideBank.c5',
         'Spectral/AddResynth.c5','Time/UltimateGrainer.c5','Filters/BrickWall.c5')


def main():
    report=ROOT/'tests/reports/offline_memory_output_extended.jsonl'
    cancel=threading.Event()
    with tempfile.TemporaryDirectory(prefix='cecilia-long-outputs-') as directory:
        folder=Path(directory);small=folder/'small.wav';fixture(small,1024**2)
        cases=[(module,size) for module in MODULES for size in (1024**3,1152*1024**2)]
        cases.append(('Filters/Binaural.c5',64*1024**2))
        def render(item):
            index,(module,size)=item
            if cancel.is_set():return None
            if shutil.disk_usage(folder).free<5*1024**3:
                raise RuntimeError('Insufficient disk headroom for long-output retry')
            scratch=folder/str(index);scratch.mkdir()
            spec={'module':str(ROOT/'Resources/modules'/module),'small':str(small),'input':str(small),
                  'output':str(scratch/'output.wav'),'scratch':str(scratch),'frames':size//(CHANNELS*4)}
            try:row=run_case(spec,scratch,600,512*1024**2,cancel_event=cancel)
            finally:shutil.rmtree(scratch)
            row.update(module=module,target_audio_bytes=size,direction='output',parallel_children=2)
            return row
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(render,item) for item in enumerate(cases)]
            try:
                for future in concurrent.futures.as_completed(futures):
                    row=future.result()
                    if row is None:continue
                    with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
                    print(json.dumps({k:row.get(k) for k in ('module','target_audio_bytes','status','elapsed_seconds','sampled_peak_rss_bytes')}),flush=True)
            except BaseException:
                cancel.set()
                raise


if __name__=='__main__':main()
