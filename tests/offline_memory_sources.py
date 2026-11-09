"""Track native render dependencies separately from unused coordinator classes."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'tests/reports/offline_memory_source_versions.json'
CORE='Resources/OfflineRender.py'


def native_pipeline_hash(source):
    tree=ast.parse(source)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.ClassDef) and
               node.name in ('OfflineRenderManager','_WorkerPool','_SubprocessWorkerHandle'))]
    return hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()


def register_core_version():
    source=(ROOT/CORE).read_bytes()
    versions=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    digest=hashlib.sha256(source).hexdigest()
    versions[digest]={'native_pipeline_sha256':native_pipeline_hash(source.decode()),
                     'scope':'All AST nodes except coordinator/worker-pool/process-handle classes; direct size probes do not invoke these classes.'}
    MANIFEST.write_text(json.dumps(versions,indent=2)+'\n')
    return digest


def same_native_sources(before,after):
    if before==after:return True
    if set(before)!=set(after):return False
    versions=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for path,digest in before.items():
        if digest==after[path]:continue
        if path!=CORE:return False
        prior=versions.get(digest,{}).get('native_pipeline_sha256')
        current=versions.get(after[path],{}).get('native_pipeline_sha256')
        if not prior or prior!=current:return False
    return True
