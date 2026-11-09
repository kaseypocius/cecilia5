"""Exercise each non-primary file slot with real large inputs under the RSS watchdog."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from check_offline_memory import ROOT,SIZES,SR,fixture,run_case
from check_all_modules import inputs_for


def main():
    report=ROOT/'tests/reports/offline_memory_aux.jsonl'
    modules=sorted((ROOT/'Resources/modules').rglob('*.c5'))
    with tempfile.TemporaryDirectory(prefix='cecilia-aux-memory-') as directory:
        folder=Path(directory);small=folder/'small.wav';fixture(small,1024**2)
        for size in SIZES:
            source=folder/'source.wav';metadata=fixture(source,size)
            for module in modules:
                for slot in list(inputs_for(module))[1:]:
                    scratch=folder/'job';scratch.mkdir()
                    spec={'module':str(module),'small':str(small),'input':str(source),
                          'input_slot':slot,'output':str(scratch/'output.wav'),
                          'scratch':str(scratch),'frames':SR}
                    try:row=run_case(spec,scratch,120,3*1024**3)
                    finally:shutil.rmtree(scratch)
                    row.update(module=str(module.relative_to(ROOT/'Resources/modules')),
                               input_slot=slot,target_audio_bytes=size,input_fixture=metadata)
                    with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
                    print(json.dumps({k:row.get(k) for k in ('module','input_slot','target_audio_bytes','status','elapsed_seconds','sampled_peak_rss_bytes')}),flush=True)
            source.unlink()


if __name__=='__main__':main()
