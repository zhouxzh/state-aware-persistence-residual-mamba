"""Validate completed r6 checkpoints on CPU without touching numeric test data."""
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import torch

ROOT=Path('/home/zhong/Documents/state-aware-persistence-residual-mamba')
RUN=ROOT/'results/encoder_l_v1_r6'
protocol=json.loads((RUN/'protocol/protocol.json').read_text())
os.environ.update({'ENCODER_L_CONFIG_DIR':'configs/encoder_l_v1_r6',
                   'ENCODER_L_RUN_ROOT':'results/encoder_l_v1_r6',
                   'ENCODER_L_PREFIX':protocol['series_id_prefix'],
                   'ENCODER_L_SEEDS':','.join(map(str,protocol['training_seeds']))})
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('checkpoint_runner',ROOT/'scripts/encoder_l_v1.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
assert r.sha(ROOT/'scripts/encoder_l_v1.py')==protocol['source_hashes']['runner_sha256']
errors,checked,not_complete=[],[],[]
for cell in protocol['registered_cells']:
    key=f"L{cell['L']}-H24-{cell['model']}-s{cell['seed']}"
    directory=RUN/'bundles'/key
    manifest=directory/'manifest.json'
    if not manifest.exists() or json.loads(manifest.read_text()).get('status')!='complete':
        not_complete.append(key);continue
    try:
        path=directory/'model.pt'
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        state=torch.load(path,map_location='cpu',weights_only=True)
        for name,tensor in state.items():
            if not torch.is_tensor(tensor): raise ValueError('Non-tensor state: '+name)
            if tensor.is_floating_point() and not torch.isfinite(tensor).all(): raise ValueError('Nonfinite weights: '+name)
        model=r.make_model(cell['model'],cell['L'])
        model.load_state_dict(state,strict=True)
        params=sum(p.numel() for p in model.parameters())
        declared=protocol['model_parameters'][f"L{cell['L']}_{cell['model']}"]
        if params!=declared:raise ValueError(f'Parameter mismatch: {params} != {declared}')
        checked.append({'cell':key,'checkpoint_sha256':h,'parameters':params,'strict_load':True,'finite_tensors':True})
        del model,state
    except Exception as exc:
        errors.append({'cell':key,'error':repr(exc)})
print(json.dumps({'protocol':protocol['protocol_version'],'checked_at':datetime.now(timezone.utc).isoformat(),'completed_checkpoints_checked':len(checked),'registered':len(protocol['registered_cells']),'errors':errors,'incomplete':not_complete,'ready':not errors and not not_complete,'test_numeric_access':False,'scope':'completed model states loaded on CPU; no forecasts or test values read','checkpoints':checked},indent=2))
