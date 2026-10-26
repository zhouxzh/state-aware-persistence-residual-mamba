#!/usr/bin/env python3
"""Metadata-only release gate. This script NEVER materializes or evaluates test."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/zhong/Documents/state-aware-persistence-residual-mamba')
RUN = ROOT / 'results/encoder_l_v1_r6'
CONFIG = ROOT / 'configs/encoder_l_v1_r6'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()

p=read(RUN/'protocol/protocol.json')
analysis=read(RUN/'protocol/analysis_freeze.json')
configuration=read(CONFIG/'protocol.json')
issues=[]
expected=p['registered_cells']
forbidden=[RUN/'data/test_once.npz',RUN/'protocol/test_access_ledger.json']
if any(f.exists() for f in forbidden): issues.append('test_already_accessed_or_attempted')
paths={'runner_sha256':ROOT/'scripts/encoder_l_v1.py','model_api_sha256':ROOT/'model/StateAwarePersistenceResidualMamba.py','feature_api_sha256':ROOT/'utils/sapr_mamba/features.py','model_spec_sha256':CONFIG/'model_spec.json','protocol_config_sha256':CONFIG/'protocol.json','synthetic_config_sha256':CONFIG/'synthetic.json'}
for key,path in paths.items():
    if digest(path)!=p['source_hashes'][key]: issues.append('hash_mismatch:'+key)
if digest(ROOT/'scripts/analyze_encoder_l_v1.py')!=analysis['analysis_script_sha256']: issues.append('analysis_hash_mismatch')
seed_set=sorted({c['seed'] for c in expected})
if seed_set!=sorted(p['training_seeds']): issues.append('registered_seed_set_mismatch')
if sorted(configuration['training_seeds'])!=seed_set: issues.append('configuration_seed_mismatch')
complete=[]
for cell in expected:
    key=f"L{cell['L']}-H24-{cell['model']}-s{cell['seed']}"
    directory=RUN/'bundles'/key
    f=directory/'manifest.json'
    if not f.exists(): issues.append('missing_manifest:'+key); continue
    m=read(f)
    if m.get('status')!='complete': issues.append('not_complete:'+key); continue
    if any(m.get(k)!=cell[k] for k in ('L','model','seed')): issues.append('identity_mismatch:'+key)
    if m.get('runner_sha256')!=p['source_hashes']['runner_sha256']: issues.append('cell_source_mismatch:'+key)
    if not math.isfinite(float(m.get('best_validation_mse',float('nan')))): issues.append('nonfinite_validation:'+key)
    checkpoint=directory/'model.pt'
    if not checkpoint.is_file(): issues.append('missing_checkpoint:'+key); continue
    complete.append({'cell':key,'manifest_sha256':digest(f),'checkpoint_sha256':digest(checkpoint)})
if not (RUN/'forecasts').is_dir(): issues.append('missing_forecast_output_directory')
output={'protocol':p['protocol_version'],'checked_at':datetime.now(timezone.utc).isoformat(),'expected':len(expected),'complete':len(complete),'technical_checks_pass':not issues,'issues':issues,'test_numeric_read':False,'run_root':str(RUN),'protocol_sha256':digest(RUN/'protocol/protocol.json'),'required_environment':{'PYTHONPATH':'.','ENCODER_L_CONFIG_DIR':'configs/encoder_l_v1_r6','ENCODER_L_RUN_ROOT':'results/encoder_l_v1_r6','ENCODER_L_PREFIX':p['series_id_prefix'],'ENCODER_L_SEEDS':','.join(map(str,seed_set))},'checkpoint_inventory':complete,'scientific_release_status':'HOLD: see pre-test deviations; technical pass does not erase protocol deviations','known_analyzer_manifest_version_error':'hardcoded encoder_l_v1.r3; must bind output to actual r6 via additive correction'}
print(json.dumps(output,indent=2))
