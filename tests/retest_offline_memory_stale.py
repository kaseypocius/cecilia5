"""Repeat only recorded size cases invalidated by relevant source edits."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from check_offline_memory import ROOT,SR,CHANNELS,fixture,run_case
from check_all_modules import inputs_for
from offline_memory_sources import same_native_sources


def main():
    report=ROOT/'tests/reports/offline_memory.jsonl'
    latest={}
    for line in report.read_text().splitlines():
        row=json.loads(line);latest[(row['module'],row['direction'],row['target_audio_bytes'])]=row
    stale=[]
    for row in latest.values():
        if row['status']=='not_applicable':continue
        current={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in row['source_hashes']}
        if row.get('source_changed_during_case') or not same_native_sources(row['source_hashes'],current):stale.append(row)
    with tempfile.TemporaryDirectory(prefix='cecilia-memory-stale-') as directory:
        folder=Path(directory);small=folder/'small.wav';fixture(small,1024**2)
        for prior in sorted(stale,key=lambda r:(r['target_audio_bytes'],r['module'],r['direction'])):
            size=prior['target_audio_bytes'];source=folder/'source.wav'
            metadata=fixture(source,size) if prior['direction']=='input' else None
            scratch=folder/'job';scratch.mkdir()
            spec={'module':str(ROOT/'Resources/modules'/prior['module']),'small':str(small),
                  'input':str(source if metadata else small),'output':str(scratch/'output.wav'),
                  'scratch':str(scratch),'frames':SR if metadata else size//(CHANNELS*4)}
            try:row=run_case(spec,scratch,120,3*1024**3)
            finally:shutil.rmtree(scratch)
            row.update(module=prior['module'],direction=prior['direction'],target_audio_bytes=size,input_fixture=metadata)
            with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
            print(json.dumps({k:row.get(k) for k in ('module','direction','target_audio_bytes','status')}),flush=True)
            if source.exists():source.unlink()


if __name__=='__main__':main()
