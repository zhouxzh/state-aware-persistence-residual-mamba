#!/usr/bin/env python3
"""Resumable cell runner for sealed encoder_l_v1.r2; never opens test."""
from __future__ import annotations
import json, os, subprocess, sys, time, traceback
from pathlib import Path
ROOT=Path('/home/zhong/Documents/state-aware-persistence-residual-mamba')
os.chdir(ROOT)
os.environ['PYTHONPATH']='.'
os.environ['ENCODER_L_CONFIG_DIR']='configs/encoder_l_v1_r6'
os.environ['ENCODER_L_RUN_ROOT']='results/encoder_l_v1_r6'
os.environ['ENCODER_L_PREFIX']='enc_l_v1_r6_'
os.environ['ENCODER_L_SEEDS']='20261521,20261522,20261523,20261524,20261525'
sys.path.insert(0,str(ROOT))
import scripts.encoder_l_v1 as runner
RUN=ROOT/'results/encoder_l_v1_r6'; LOG=RUN/'logs'; FAIL=RUN/'failures'; MON=RUN/'monitor'
LOG.mkdir(parents=True,exist_ok=True); FAIL.mkdir(parents=True,exist_ok=True); MON.mkdir(parents=True,exist_ok=True)
protocol=json.loads((RUN/'protocol/protocol.json').read_text())
actual=runner.sha(ROOT/'scripts/encoder_l_v1.py')
if actual != protocol['source_hashes']['runner_sha256']:
 raise SystemExit('runner hash differs from sealed protocol')
max_seconds=float(protocol.get('budget',{}).get('max_gpu_hours',30))*3600
cells=list(runner.cells()); seeds=runner.SEEDS
start=time.time(); finished=failed=skipped=0
for idx,(L,model) in enumerate(cells):
 for seed in seeds:
  key=f'L{L}-H24-{model}-s{seed}'; out=RUN/'bundles'/key; manifest=out/'manifest.json'
  if manifest.exists() and json.loads(manifest.read_text()).get('status')=='complete':
   skipped+=1; continue
  elapsed=sum(float(json.loads(p.read_text()).get('elapsed_seconds',0)) for p in RUN.glob('bundles/*/manifest.json') if json.loads(p.read_text()).get('status')=='complete')
  if elapsed>=max_seconds:
   (RUN/'protocol'/'matrix_status.json').write_text(json.dumps({'status':'budget_stopped','completed':finished,'failed':failed,'skipped':skipped,'training_seconds':elapsed,'test_loaded':False},indent=2))
   raise SystemExit('30 GPU-hour training budget reached; test remains locked')
  try:
   runner.train_one(model,L,seed); finished+=1
  except Exception as exc:
   failed+=1; out.mkdir(parents=True,exist_ok=True)
   payload={'status':'failed','model':model,'L':L,'H':24,'seed':seed,'error':repr(exc),'traceback':traceback.format_exc(),'split_access':['train','validation'],'test_loaded':False}
   (out/'manifest.json').write_text(json.dumps(payload,indent=2))
   (FAIL/f'{key}.json').write_text(json.dumps(payload,indent=2))
  status={'status':'running','cells_total':len(cells)*len(seeds),'completed':finished,'failed':failed,'skipped':skipped,'last_cell':key,'training_seconds':elapsed,'test_loaded':False,'updated_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
  (RUN/'protocol'/'matrix_status.json').write_text(json.dumps(status,indent=2))
  if (finished+failed+skipped)%5==0:
   (MON/'supervisor_snapshot.json').write_text(json.dumps(status,indent=2))
completed_manifests=sum(1 for p in RUN.glob('bundles/*/manifest.json') if json.loads(p.read_text()).get('status')=='complete')
status={'status':'matrix_complete' if completed_manifests==70 and failed==0 else 'matrix_incomplete','cells_total':70,'completed_manifests':completed_manifests,'newly_completed':finished,'failed':failed,'skipped':skipped,'elapsed_seconds':time.time()-start,'test_loaded':False,'finished_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
(RUN/'protocol'/'matrix_status.json').write_text(json.dumps(status,indent=2)); print(json.dumps(status,indent=2))
