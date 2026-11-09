"""Bounded-memory normalization, encoding, trimming, stitching and native branch-mix audit."""
import sys,json,time,resource,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from check_offline_memory import fixture,rss
if len(sys.argv)>1:
 import numpy as np
 from Resources.AudioFileIO import AudioReader,AudioWriter,audio_peak
 from Resources.OfflineRender import normalize_audio_file,_HeadlessRenderWorker
 op=sys.argv[1];size=int(sys.argv[2]);start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='cecilia-memory-utility-') as folder:
  folder=Path(folder);source=folder/'source.wav';out=folder/'output.wav'
  metadata=fixture(source,size);frames=metadata['frames']
  if op=='normalize':
   normalize_audio_file(str(source),-1);out=source
  elif op=='encode':
   out=folder/'output.aif'
   with AudioReader(source) as reader,AudioWriter(out,48000,8,frames,1,1) as writer:
    for block in reader.blocks():writer.write(block)
  elif op=='trim':
   _HeadlessRenderWorker._trim_audio_file(None,str(source),48000,8,frames-19,0,3,discard_frames=19,output_path=str(out),keep_source=True)
   frames-=19
  elif op=='mix':
   from check_all_modules import snapshot
   small=folder/'small.wav';fixture(small,1024**2)
   snap=snapshot(Path.cwd()/'Resources/modules/Filters/StateVar2.c5',small)
   snap['output'].update(totalTime=frames/48000,nchnls=8,gainSlider=0)
   worker=_HeadlessRenderWorker(lambda event:None)
   worker.mix_and_master_branches({'job_id':'utility','branch_files':[str(source)],
    'total_cables':1,'snapshot':snap,'output_path':str(out),'sr':48000,'nchnls':8,
    'buffersize':256,'total_time':frames/48000,'global_fade':0,'audio_file_type':'wav',
    'samp_size':3,'scratch_dir':str(folder)})
   # Verify every sample after the server's initial gain ramp, not just a peak.
   with AudioReader(source) as a,AudioReader(out) as b:
    for index,block in enumerate(a.blocks()):
     other=b.read(len(block))
     skip=1024 if index==0 else 0
     np.testing.assert_allclose(other[skip:],block[skip:],rtol=0,atol=1e-7)
  elif op=='stitch':
   _HeadlessRenderWorker.stitch_time_chunks(None,{'job_id':'utility','chunks':[{'path':str(source),'discard_frames':0,'a_frame':0,'b_frame':frames}], 'output_path':str(out),'sr':48000,'nchnls':8,'total_frames':frames,'xfade_frames':4800,'global_fade':.005,'audio_file_type':'wav','samp_size':3})
  with AudioReader(out) as reader:
   assert reader.info.frames==frames and reader.info.channels==8
  peak=audio_peak(out)
  print('RESULT '+json.dumps({'operation':op,'target_audio_bytes':size,'input_fixture':metadata,'output_bytes':out.stat().st_size,'peak':peak,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-start}),flush=True)
else:
 report=Path('tests/reports/offline_memory_utilities_final.jsonl')
 for size in (64*1024**2,1024**3,1152*1024**2):
  for op in ('normalize','encode','trim','stitch','mix'):
   with tempfile.TemporaryFile(mode='w+') as log:
    child=subprocess.Popen([sys.executable,__file__,op,str(size)],stdout=log,stderr=subprocess.STDOUT)
    status=None;start=time.monotonic()
    while child.poll() is None:
     if rss(child.pid)>3*1024**3 or time.monotonic()-start>120:
      status='watchdog_stop';child.kill();child.wait();break
     time.sleep(.025)
    log.seek(0);output=log.read()
   result=next((json.loads(line[7:]) for line in output.splitlines() if line.startswith('RESULT ')),None)
   row=result or {'operation':op,'target_audio_bytes':size,'status':status or 'error','log':output[-2000:]}
   if result:row['status']='pass'
   with report.open('a') as stream:stream.write(json.dumps(row)+'\n')
   print(json.dumps(row),flush=True)
