"""An interrupted benchmark must reap its native child before returning."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import check_offline_memory as audit


class MemoryHarnessTests(unittest.TestCase):
    def test_keyboard_interrupt_terminates_and_reaps_child(self):
        children=[]
        native_popen=subprocess.Popen
        native_sleep=audit.time.sleep
        interrupted=False
        def interrupt_once(seconds):
            nonlocal interrupted
            if not interrupted:
                interrupted=True
                raise KeyboardInterrupt
            native_sleep(seconds)
        def spawn(command,**kwargs):
            child=native_popen([sys.executable,'-c','import time; time.sleep(30)'],**kwargs)
            children.append(child)
            return child
        spec={'module':str(audit.ROOT/'Resources/modules/Filters/StateVar2.c5')}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(audit.subprocess,'Popen',side_effect=spawn), \
                 patch.object(audit.time,'sleep',side_effect=interrupt_once):
                with self.assertRaises(KeyboardInterrupt):
                    audit.run_case(spec,Path(directory),120,1024**3)
            self.assertEqual(len(children),1)
            self.assertIsNotNone(children[0].poll(),'Benchmark child survived interruption')
            self.assertEqual(int((Path(directory)/'child.pid').read_text()),children[0].pid)




class NativeDependencyTests(unittest.TestCase):
    def test_coordinator_changes_do_not_mask_native_graph_changes(self):
        from offline_memory_sources import native_pipeline_hash
        source='def normalize(): return 1\nclass _HeadlessRenderWorker:\n def render(self): return 2\nclass OfflineRenderManager:\n def run(self): return 3\n'
        self.assertEqual(native_pipeline_hash(source),native_pipeline_hash(source.replace('return 3','return 4')))
        self.assertNotEqual(native_pipeline_hash(source),native_pipeline_hash(source.replace('return 2','return 4')))
        self.assertNotEqual(native_pipeline_hash(source),native_pipeline_hash(source.replace('return 1','return 4')))


if __name__=='__main__':
    unittest.main()
