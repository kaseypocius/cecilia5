"""Retry large analysis/impulse inputs serially with 6 GiB RSS and 300 seconds."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from check_offline_memory import ROOT,SR,fixture,run_case

CASES=(('Spectral/BinWarper.c5',None),
       ('Spectral/SpectralWarper.c5',None),
       ('Resonators&Verbs/ConvolutionReverb.c5','impulse'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory-mib',type=int,default=6144)
    parser.add_argument('--module',default='')
    parser.add_argument('--report',default='offline_memory_extended.jsonl')
    args=parser.parse_args()
    from Resources.RenderMemory import render_memory_budget
    allowance=args.memory_mib*1024**2
    if allowance > render_memory_budget():
        raise RuntimeError('Requested retry allowance exceeds the conservative system memory budget')
    report=ROOT/'tests/reports'/args.report
    with tempfile.TemporaryDirectory(prefix='cecilia-extended-memory-') as directory:
        folder=Path(directory);small=folder/'small.wav';fixture(small,1024**2)
        for size in (1024**3,1152*1024**2):
            source=folder/'source.wav';metadata=fixture(source,size)
            for module,slot in CASES:
                if args.module not in module:continue
                scratch=folder/'job';scratch.mkdir()
                spec={'module':str(ROOT/'Resources/modules'/module),'small':str(small),
                      'input':str(source),'input_slot':slot,'output':str(scratch/'output.wav'),
                      'scratch':str(scratch),'frames':SR}
                try:row=run_case(spec,scratch,300,allowance)
                finally:shutil.rmtree(scratch)
                row.update(module=module,input_slot=slot,target_audio_bytes=size,input_fixture=metadata)
                with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
                print(json.dumps({k:row.get(k) for k in ('module','input_slot','target_audio_bytes','status','elapsed_seconds','sampled_peak_rss_bytes')}),flush=True)
            source.unlink()


if __name__=='__main__':main()
