"""Representative simultaneous 1.125 GiB input/output checks under a 3 GiB watchdog."""
import json
from pathlib import Path
import shutil
import tempfile
from check_offline_memory import ROOT,CHANNELS,fixture,run_case


def main():
    report=ROOT/'tests/reports/offline_memory_paired.jsonl'
    size=1152*1024**2
    with tempfile.TemporaryDirectory(prefix='cecilia-paired-memory-') as directory:
        folder=Path(directory);small=folder/'small.wav';source=folder/'source.wav'
        fixture(small,1024**2);metadata=fixture(source,size)
        for module in ('Filters/StateVar2.c5','Multiband/MultiBandDelay.c5','Resonators&Verbs/ConvolutionReverb.c5'):
            scratch=folder/'job';scratch.mkdir()
            spec={'module':str(ROOT/'Resources/modules'/module),'small':str(small),'input':str(source),
                  'output':str(scratch/'output.wav'),'scratch':str(scratch),'frames':size//(CHANNELS*4)}
            try:row=run_case(spec,scratch,180,3*1024**3)
            finally:shutil.rmtree(scratch)
            row.update(module=module,target_audio_bytes=size,input_fixture=metadata,direction='paired')
            with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
            print(json.dumps({k:row.get(k) for k in ('module','status','elapsed_seconds','sampled_peak_rss_bytes')}),flush=True)


if __name__=='__main__':main()
