"""Repeat 150 PCM32 MultiBandDelay jobs to expose native circular-read NaNs."""
import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
import check_multichannel_formats as audit
from Resources.OfflineRender import RenderJob
from pyo import Server
scenario=next(s for s in audit.SCENARIOS if s[0]=='stereo_eight_pcm32')
server=Server(sr=48000,nchnls=8,audio='manual',duplex=0).boot();server.verbosity=0
with tempfile.TemporaryDirectory(prefix='cecilia-delay-stress-') as folder:
 folder=Path(folder);source,_=audit.write_fixture(folder,scenario)
 frames=int(.75*48000)+17
 module=Path.cwd()/'Resources/modules/Multiband/MultiBandDelay.c5'
 jobs=[RenderJob(str(i),str(i),str(folder/f'{i}.wav'),audit.make_snapshot(module,source,frames,48000,8)) for i in range(150)]
 result=audit.run_jobs(jobs,48000,8,'wav',2,'single')
 errors=[{'job':j.job_id,'error':j.error} for j in jobs if j.status!='Done']
 Path('tests/reports/offline_memory_delay_stress.json').write_text(json.dumps({'cases':len(jobs),'passed':result.completed,'failed':result.failed,'errors':errors},indent=2)+'\n')
 print(result.completed,result.failed,flush=True)
server.shutdown()
sys.exit(1 if result.failed else 0)
