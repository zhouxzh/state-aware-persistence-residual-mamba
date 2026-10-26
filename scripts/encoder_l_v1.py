#!/usr/bin/env python3
"""Test-locked runner for the independent encoder_l_v1 residual study.

Only the explicit evaluate-once command materializes numeric test data.
OCRA files are read only for roster/seed blacklisting; OCRA code/results are not
modified or used to select models, features, horizons, or thresholds.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, random, subprocess, sys, time
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, RandomSampler

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/os.environ.get('ENCODER_L_CONFIG_DIR','configs/encoder_l_v1')
RUN=ROOT/os.environ.get('ENCODER_L_RUN_ROOT','results/encoder_l_v1')
PREFIX=os.environ.get('ENCODER_L_PREFIX','enc_l_v1_')
MECHS=['stable','visible_level_shift','future_jump','continuing_trend','trend_break','stable_season','seasonal_change','variance_shift','random_walk']
LENS=[96,384,768]; H=24; MAXL=768; STRIDE=96; SEEDS=[int(v) for v in os.environ.get('ENCODER_L_SEEDS','20261121,20261122,20261123,20261124,20261125').split(',')]

from utils.sapr_mamba.features import causal_features
from utils.sapr_mamba.data import SeriesInfo, make_origins
from mamba_ssm import Mamba


def sha(path):
 h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()
def dump(path,obj):
 p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+'.tmp'); q.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8'); q.replace(p)
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def seed_all(seed):
 random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False

def split_seed(master,split): return int(master)+{'train':11,'validation':29,'test':47}[split]
def make_id(split,mech,index): return f'{PREFIX}{split}_{mech}_{index:04d}'

def generate_one(mech,index,cfg,rng,split):
 b=cfg['base']; T=int(cfg['length']); P=int(cfg['seasonal_period']); noise=rng.normal(0,float(b['innovation_std']),T)
 vis=int(b['visible_change_points'][index%len(b['visible_change_points'])]); fut=int(b['future_jump_origins'][index%len(b['future_jump_origins'])])+int(b['future_jump_offset']); direction=-1. if index%2==0 else 1.
 if mech=='variance_shift': noise[vis:]*=float(b['variance_multiplier'])
 if mech=='random_walk' or (mech=='future_jump' and b['future_jump_baseline']=='random_walk'):
  x=np.cumsum(noise); cp=-1 if mech=='random_walk' else fut
  if mech=='future_jump': x[fut:]+=direction*float(b['jump_strength'])
 else:
  x=np.empty(T,dtype=np.float64); x[0]=noise[0]
  for t in range(1,T): x[t]=float(b['ar'])*x[t-1]+noise[t]
  t=np.arange(T,dtype=np.float64); cp=vis
  if mech=='continuing_trend': x+=float(b['trend_slope'])*t
  elif mech=='stable_season': x+=float(b['seasonal_amplitude'])*np.sin(2*np.pi*t/P)
  elif mech=='visible_level_shift': x[vis:]+=float(b['jump_strength'])
  elif mech=='trend_break': x[vis:]+=(t[vis:]-vis)*float(b['trend_break_slope'])
  elif mech=='seasonal_change':
   x+=float(b['seasonal_amplitude'])*np.sin(2*np.pi*t/P); x[vis:]+=float(b['seasonal_change_amplitude'])*np.sin(2*np.pi*t[vis:]/P+np.pi/3)
  elif mech=='future_jump': x[fut:]+=direction*float(b['jump_strength']); cp=fut
 return x.astype(np.float32), {'series_id':make_id(split,mech,index),'mechanism':mech,'change_point':int(cp),'split':split}

def record_only(mech,index,split,cfg):
 b=cfg['base']; vis=int(b['visible_change_points'][index%len(b['visible_change_points'])]); fut=int(b['future_jump_origins'][index%len(b['future_jump_origins'])])+int(b['future_jump_offset']); cp=-1 if mech in {'stable','stable_season','random_walk'} else (fut if mech=='future_jump' else vis)
 return {'series_id':make_id(split,mech,index),'mechanism':mech,'change_point':cp,'split':split}

def build_split(split,materialize):
 cfg=load(CONFIG/'synthetic.json'); rng=np.random.default_rng(split_seed(cfg['generator_seed'],split)); counts=cfg.get('mechanism_split_overrides',{}); default=cfg['splits'][split]; values=[]; records=[]
 for mech in MECHS:
  n=int(counts.get(mech,{}).get(split,default))
  for i in range(n):
   rec=record_only(mech,i,split,cfg); records.append(rec)
   if materialize: values.append(generate_one(mech,i,cfg,rng,split)[0])
 return (np.stack(values) if materialize else None),records

def labels_for(records,origins,H,main_lookback=96):
 # Main labels use the shortest registered lookback so S4/S6 are identical across L.
 delay=int(load(CONFIG/'synthetic.json')['change_signal_delay']); out=[]
 for si,o in origins:
  r=records[int(si)]; m=r['mechanism']; cp=int(r['change_point']); origin=int(o)
  if m in {'stable','stable_season','random_walk','variance_shift'}: lab='stable'
  elif m=='continuing_trend': lab='visible_change'
  elif m=='future_jump': lab='unseen_change' if origin<=cp<origin+H else 'stable'
  else: lab='visible_change' if origin-main_lookback<=cp<origin and origin>=cp+delay else 'stable'
  out.append(lab)
 return np.asarray(out)

class OriginData(Dataset):
 def __init__(self,values,origins,L,state_on):
  self.values=values; self.origins=origins; self.L=L; self.features=[]
  for si,o in origins:
   # State summary uses the same 96-point suffix at every L.
   hist=values[int(si),int(o)-96:int(o)]
   self.features.append(causal_features(hist,48).astype(np.float32) if state_on else np.zeros(9,dtype=np.float32))
  self.features=np.stack(self.features)
 def __len__(self): return len(self.origins)
 def __getitem__(self,i):
  si,o=map(int,self.origins[i]); return {'x':torch.from_numpy(self.values[si,o-self.L:o].copy()),'y':torch.from_numpy(self.values[si,o:o+H].copy()),'phi':torch.from_numpy(self.features[i].copy()),'series':si,'origin':o}

class LinearFull(nn.Module):
 def __init__(self,L): super().__init__(); self.fc=nn.Linear(L-1+9,H)
 def forward(self,x,phi):
  base=x[:,-1:]; scale=x.std(1,keepdim=True,unbiased=False).clamp_min(1e-6); z=(x-base)/scale; d=z[:,1:]-z[:,:-1]; return base.expand(-1,H)+self.fc(torch.cat((d,phi),1))*scale
class MLPFull(nn.Module):
 WIDTH={96:203,384:125,768:77}
 def __init__(self,L):
  super().__init__(); d=self.WIDTH[L]; self.net=nn.Sequential(nn.Linear(L+9,d),nn.GELU(),nn.Linear(d,d),nn.GELU(),nn.Linear(d,H))
 def forward(self,x,phi):
  base=x[:,-1:]; scale=x.std(1,keepdim=True,unbiased=False).clamp_min(1e-6); z=(x-base)/scale; return base.expand(-1,H)+self.net(torch.cat((z,phi),1))*scale
class TransformerFull(nn.Module):
 def __init__(self,L,state_on=True):
  super().__init__(); d=64; self.L=L; self.state_on=bool(state_on); self.proj=nn.Linear(1+9,d); layer=nn.TransformerEncoderLayer(d,4,128,dropout=.1,batch_first=True,norm_first=True); self.enc=nn.TransformerEncoder(layer,2); self.head=nn.Linear(d,H)
  pos=torch.arange(L,dtype=torch.float32).unsqueeze(1); div=torch.exp(torch.arange(0,d,2,dtype=torch.float32)*(-math.log(10000.0)/d)); pe=torch.zeros(L,d); pe[:,0::2]=torch.sin(pos*div); pe[:,1::2]=torch.cos(pos*div); self.register_buffer('pos',pe.unsqueeze(0),persistent=True)
 def forward(self,x,phi):
  base=x[:,-1:]; scale=x.std(1,keepdim=True,unbiased=False).clamp_min(1e-6); z=(x-base)/scale
  if not self.state_on: phi=torch.zeros_like(phi)
  f=phi[:,None,:].expand(-1,self.L,-1); h=self.enc(self.proj(torch.cat((z.unsqueeze(-1),f),-1))+self.pos)[:,-1]; return base.expand(-1,H)+self.head(h)*scale
class MambaFull(nn.Module):
 def __init__(self,L,state_on):
  super().__init__(); self.L=L; self.state_on=state_on; self.proj=nn.Linear(10,64); self.blocks=nn.ModuleList([Mamba(d_model=64,d_state=16,d_conv=4,expand=2) for _ in range(2)]); self.norms=nn.ModuleList([nn.LayerNorm(64) for _ in range(2)]); self.drop=nn.Dropout(.1); self.head=nn.Linear(64,H)
 def forward(self,x,phi):
  base=x[:,-1:]; scale=x.std(1,keepdim=True,unbiased=False).clamp_min(1e-6); z=(x-base)/scale
  if not self.state_on: phi=torch.zeros_like(phi)
  f=phi[:,None,:].expand(-1,self.L,-1); h=self.proj(torch.cat((z.unsqueeze(-1),f),-1))
  for block,norm in zip(self.blocks,self.norms): h=norm(h+self.drop(block(h)))
  return base.expand(-1,H)+self.head(h[:,-1])*scale

def make_model(name,L):
 if name=='LinPhi': return LinearFull(L)
 if name=='MLPPhi': return MLPFull(L)
 if name.startswith('Transformer'): return TransformerFull(L,name.endswith('Phi'))
 if name.startswith('Mamba'): return MambaFull(L,name.endswith('Phi'))
 raise ValueError(name)
def cells():
 for m in ['LinPhi','MLPPhi','TransformerPhi','Transformer0','MambaPhi','Mamba0']: yield 384,m
 for L in (96,768):
  for m in ['TransformerPhi','Transformer0','MambaPhi','Mamba0']: yield L,m

def _manifest_source_hashes():
 return {'runner_sha256':sha(Path(__file__)),'model_api_sha256':sha(ROOT/'model/StateAwarePersistenceResidualMamba.py'),'feature_api_sha256':sha(ROOT/'utils/sapr_mamba/features.py'),'protocol_config_sha256':sha(CONFIG/'protocol.json'),'synthetic_config_sha256':sha(CONFIG/'synthetic.json'),'model_spec_sha256':sha(CONFIG/'model_spec.json')}

def _old_rosters_and_seeds():
 ids=set(); seeds={20262200,20262201,20262202,20262203,20262204,20262205}
 for roster in sorted(list((ROOT/'results').glob('ocra*/data/*_roster.json')) + list((ROOT/'results').glob('encoder_l_v*/data/*_roster.json'))):
  try: ids.update(str(r['series_id']) for r in json.loads(roster.read_text()).get('records',[]))
  except Exception: pass
 for p in sorted(list((ROOT/'results').glob('ocra*/protocol/*.json')) + list((ROOT/'results').glob('encoder_l_v*/protocol/*.json'))):
  if p.name not in {'seed_manifest.json','protocol.json'}: continue
  try:
   o=json.loads(p.read_text()); seeds.update(map(int,o.get('training_seeds',[])))
   for k in ('generator_seed',):
    if k in o: seeds.add(int(o[k]))
  except Exception: pass
 return ids,seeds

def seal():
 if (RUN/'protocol/protocol.json').exists(): raise RuntimeError('protocol already sealed; use a new protocol directory')
 cfg=load(CONFIG/'synthetic.json'); prot=load(CONFIG/'protocol.json'); train,tr=build_split('train',True); val,vr=build_split('validation',True); _,te=build_split('test',False)
 old_ids,old_seeds=_old_rosters_and_seeds(); all_new=tr+vr+te; ids={r['series_id'] for r in all_new}; overlap=sorted(ids&old_ids); seed_values={int(cfg['generator_seed']),*map(int,SEEDS),*(split_seed(cfg['generator_seed'],s) for s in ('train','validation','test'))}; seed_overlap=sorted(seed_values&old_seeds)
 if overlap or seed_overlap: raise RuntimeError(f'blacklist collision ids={len(overlap)} seeds={seed_overlap}')
 RUN.mkdir(parents=True,exist_ok=True); (RUN/'protocol').mkdir(exist_ok=True); (RUN/'data').mkdir(exist_ok=True)
 np.savez_compressed(RUN/'data/train.npz',values=train); np.savez_compressed(RUN/'data/validation.npz',values=val)
 for n,recs in [('train',tr),('validation',vr),('test',te)]: dump(RUN/'data'/f'{n}_roster.json',{'records':recs})
 common={}; cfgsplit={'train':train,'validation':val,'test':np.zeros((len(te),int(cfg['length'])),dtype=np.float32)}
 for split,arr,recs in [('train',train,tr),('validation',val,vr),('test',cfgsplit['test'],te)]:
  infos=[SeriesInfo(r['series_id'],int(cfg['seasonal_period']),arr.shape[1],arr.shape[1],split,r['mechanism'],0.,int(r['change_point'])) for r in recs]
  common[split]=make_origins(arr,infos,MAXL,H,'all',STRIDE).tolist()
 dump(RUN/'protocol/common_origins.json',common)
 if len(list(cells()))*len(SEEDS)!=70: raise RuntimeError('registered cell count is not 70')
 model_counts={}
 for L,name in cells(): model_counts[f'L{L}_{name}']=sum(p.numel() for p in make_model(name,L).parameters())
 # Validate label counts and that the future-jump event is within the main horizon.
 test_orig=np.asarray(common['test'],dtype=np.int64); labels=labels_for(te,test_orig,H); n2=int(np.sum((labels=='unseen_change') & np.asarray([te[int(si)]['mechanism']=='future_jump' for si,o in test_orig])))
 if n2<1: raise RuntimeError('N2 has no true unseen-jump origins under the frozen H=24 window')
 blacklist={'prior_series_count':len(old_ids),'new_series_count':len(ids),'series_intersection':overlap,'prior_seed_blacklist_count':len(old_seeds),'new_seed_streams':sorted(seed_values),'seed_intersection':seed_overlap,'passed':True}
 dump(RUN/'protocol/blacklist_check.json',blacklist)
 prot.update({'sealed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'status':'sealed_before_training','test_access':'locked','test_numeric_materialized':False,'source_hashes':_manifest_source_hashes(),'series_roster_hashes':{n:sha(RUN/'data'/f'{n}_roster.json') for n in ('train','validation','test')},'common_origin_hash':hashlib.sha256(json.dumps(common,sort_keys=True).encode()).hexdigest(),'model_parameters':model_counts,'registered_cells':[{'L':L,'model':m,'seed':s} for L,m in cells() for s in SEEDS],'expected_runs':70,'n2_test_origin_count':n2})
 dump(RUN/'protocol/protocol.json',prot); dump(RUN/'protocol/e1_audit.json',{'status':'passed','test_numeric_loaded':False,'future_fields_used':False,'mechanism_labels_as_inputs':False,'series_id_as_input':False,'phi_window':96,'same_common_origins_all_lookbacks':True,'n2_test_origins':n2})
 print(json.dumps({'status':'sealed','runs':70,'train_series':len(tr),'validation_series':len(vr),'test_series':len(te),'test_numeric_materialized':False,'n2_test_origins':n2,'blacklist_passed':True,'model_parameters':model_counts},indent=2))

def train_one(name,L,seed):
 sealed=load(RUN/'protocol/protocol.json')
 if sealed.get('status')!='sealed_before_training' or not load(RUN/'protocol/blacklist_check.json').get('passed'): raise RuntimeError('E0 seal/blacklist required')
 if not any(c['L']==L and c['model']==name and c['seed']==seed for c in sealed['registered_cells']): raise ValueError('cell not registered')
 out=RUN/'bundles'/f'L{L}-H24-{name}-s{seed}'; manifest=out/'manifest.json'
 if manifest.exists() and load(manifest).get('status')=='complete': print('skip completed',out.name); return
 train=np.load(RUN/'data/train.npz')['values']; val=np.load(RUN/'data/validation.npz')['values']; tr=load(RUN/'data/train_roster.json')['records']; vr=load(RUN/'data/validation_roster.json')['records']; common=load(RUN/'protocol/common_origins.json'); ot=np.asarray(common['train'],dtype=np.int64); ov=np.asarray(common['validation'],dtype=np.int64)
 state_on=name.endswith('Phi'); ds=OriginData(train,ot,L,state_on); vd=OriginData(val,ov,L,state_on); dev=torch.device('cuda:0'); seed_all(seed); m=make_model(name,L).to(dev); params=sum(p.numel() for p in m.parameters()); opt=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4); batch=64
 samples=int(load(CONFIG/'protocol.json')['training']['samples_per_epoch']); sampler_gen=torch.Generator().manual_seed(seed); sampler=RandomSampler(ds,replacement=True,num_samples=samples,generator=sampler_gen); dl=DataLoader(ds,batch_size=batch,sampler=sampler,num_workers=0); vdl=DataLoader(vd,batch_size=128,shuffle=False,num_workers=0)
 out.mkdir(parents=True,exist_ok=True); started=time.time(); torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); best=float('inf'); beststate=None; stale=0; bestep=0
 training=load(CONFIG/'protocol.json')['training']; use_amp=bool(training.get('amp',False)); scaler=torch.amp.GradScaler('cuda',enabled=use_amp)
 manifest.write_text(json.dumps({'status':'running','model':name,'L':L,'H':H,'seed':seed,'split_access':['train','validation'],'amp':use_amp},indent=2))
 for ep in range(1,41):
  m.train()
  for b in dl:
   x,y,p=b['x'].to(dev),b['y'].to(dev),b['phi'].to(dev); opt.zero_grad(set_to_none=True)
   with torch.autocast(device_type='cuda',enabled=use_amp): loss=((m(x,p)-y)**2).mean()
   scaler.scale(loss).backward(); scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(m.parameters(),1.0); scaler.step(opt); scaler.update()
  m.eval(); total=cnt=0
  with torch.no_grad():
   for b in vdl:
    with torch.autocast(device_type='cuda',enabled=use_amp): pred=m(b['x'].to(dev),b['phi'].to(dev))
    total+=float(((pred-b['y'].to(dev))**2).sum()); cnt+=pred.numel()
  score=total/max(cnt,1)
  if score<best: best=score; bestep=ep; stale=0; beststate={k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
  else:
   stale+=1
   if stale>=7: break
  torch.cuda.synchronize()
 if beststate: m.load_state_dict(beststate)
 torch.save(m.state_dict(),out/'model.pt'); torch.cuda.synchronize(); payload={'status':'complete','model':name,'L':L,'H':H,'seed':seed,'state_on':state_on,'parameters':params,'best_validation_mse':best,'best_epoch':bestep,'elapsed_seconds':time.time()-started,'peak_memory_mib':torch.cuda.max_memory_allocated()/2**20,'split_access':['train','validation'],'runner_sha256':sha(Path(__file__))}; dump(manifest,payload); print(json.dumps(payload))

def evaluate_once():
 sealed=load(RUN/'protocol/protocol.json')
 if sealed.get('test_access')!='locked' or not load(RUN/'protocol/blacklist_check.json').get('passed'): raise RuntimeError('E0 not passed')
 if (RUN/'protocol/test_access_ledger.json').exists(): raise RuntimeError('test evaluation already attempted; preserve and version')
 missing=[]
 for cell in sealed['registered_cells']:
  p=RUN/'bundles'/f"L{cell['L']}-H24-{cell['model']}-s{cell['seed']}"/'manifest.json'
  if not p.exists() or load(p).get('status')!='complete': missing.append((cell['L'],cell['model'],cell['seed']))
 if missing: raise RuntimeError(f'incomplete matrix; missing {len(missing)} cells')
 dump(RUN/'protocol/test_access_ledger.json',{'test_access':'authorized_once','authorized_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'protocol_sha256':sha(RUN/'protocol/protocol.json')})
 cfg=load(CONFIG/'synthetic.json'); records=load(RUN/'data/test_roster.json')['records']; rng=np.random.default_rng(split_seed(cfg['generator_seed'],'test')); vals=[]; generated=[]
 for mech in MECHS:
  n=int(cfg.get('mechanism_split_overrides',{}).get(mech,{}).get('test',cfg['splits']['test']))
  for i in range(n):
   v,r=generate_one(mech,i,cfg,rng,'test'); vals.append(v); generated.append(r)
 if [r['series_id'] for r in generated] != [r['series_id'] for r in records]: raise RuntimeError('test roster mismatch')
 values=np.stack(vals); np.savez_compressed(RUN/'data/test_once.npz',values=values); common=load(RUN/'protocol/common_origins.json'); origins=np.asarray(common['test'],dtype=np.int64); labels=labels_for(records,origins,H); groups=[]
 for (si,o),lab in zip(origins,labels):
  m=records[int(si)]['mechanism']
  groups.append('S4' if m=='trend_break' and lab=='visible_change' else 'S6' if m=='seasonal_change' and lab=='visible_change' else 'N2' if m=='future_jump' and lab=='unseen_change' else 'N8' if m=='random_walk' else 'other')
 groups=np.asarray(groups); target=np.stack([values[int(si),int(o):int(o)+H] for si,o in origins]); base=values[origins[:,0],origins[:,1]-1][:,None]; pred_store={}; rows=[]; resources=[]; dev=torch.device('cuda:0')
 configs=sorted(set((c['L'],c['model']) for c in sealed['registered_cells']))
 for L,name in configs:
  seed_origin_preds=[]; elapsed=[]
  for seed in SEEDS:
   model=make_model(name,L).to(dev); model.load_state_dict(torch.load(RUN/'bundles'/f'L{L}-H24-{name}-s{seed}'/'model.pt',map_location=dev,weights_only=True)); model.eval(); ds=OriginData(values,origins,L,name.endswith('Phi')); dl=DataLoader(ds,batch_size=128,shuffle=False,num_workers=0); pieces=[]; torch.cuda.synchronize(); t0=time.time()
   with torch.no_grad():
    for b in dl: pieces.append(model(b['x'].to(dev),b['phi'].to(dev)).cpu().numpy())
   torch.cuda.synchronize(); elapsed.append(time.time()-t0); seed_origin_preds.append(np.concatenate(pieces))
  pred_store[f'L{L}_{name}']=np.mean(seed_origin_preds,axis=0)
  for group in ['S4','S6','N2','N8','ALL']:
   mask=np.ones(len(origins),dtype=bool) if group=='ALL' else groups==group
   if not mask.any(): continue
   for si in np.unique(origins[mask,0]):
    mm=mask&(origins[:,0]==si); per_seed=[]
    for pred in seed_origin_preds: per_seed.append(float(np.sqrt(np.mean((pred[mm]-target[mm])**2))))
    rows.append({'L':L,'H':H,'model':name,'group':group,'series_id':records[int(si)]['series_id'],'seed_mean_rmse':float(np.mean(per_seed)),'seed_sd_rmse':float(np.std(per_seed,ddof=1)),'origin_count':int(mm.sum())})
  for seed in SEEDS:
   man=load(RUN/'bundles'/f'L{L}-H24-{name}-s{seed}'/'manifest.json'); resources.append({'L':L,'model':name,'seed':seed,'parameters':man['parameters'],'train_seconds':man['elapsed_seconds'],'peak_memory_mib':man['peak_memory_mib'],'test_inference_seconds_mean':float(np.mean(elapsed))})
 base_rows=[]
 for group in ['S4','S6','N2','N8','ALL']:
  mask=np.ones(len(origins),dtype=bool) if group=='ALL' else groups==group
  if not mask.any(): continue
  for si in np.unique(origins[mask,0]):
   mm=mask&(origins[:,0]==si); rmse=float(np.sqrt(np.mean((np.broadcast_to(base,target.shape)[mm]-target[mm])**2)))
   for L in LENS: rows.append({'L':L,'H':H,'model':'M0','group':group,'series_id':records[int(si)]['series_id'],'seed_mean_rmse':rmse,'seed_sd_rmse':0.0,'origin_count':int(mm.sum())})
 np.savez_compressed(RUN/'forecasts/test_predictions_once.npz',origins=origins,group=groups,target=target,**pred_store)
 out=RUN/'metrics/sequence_rmse.csv'; out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 resource=RUN/'resources/resource_metrics.csv'; resource.parent.mkdir(parents=True,exist_ok=True)
 with resource.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(resources[0])); w.writeheader(); w.writerows(resources)
 dump(RUN/'protocol/test_access_ledger.json',{**load(RUN/'protocol/test_access_ledger.json'),'test_numeric_materialized':True,'test_series':len(records),'forecast_rows':len(origins),'metrics_sha256':sha(out),'predictions_sha256':sha(RUN/'forecasts/test_predictions_once.npz'),'resources_sha256':sha(resource)})
 dump(RUN/'protocol/protocol_status.json',{'status':'test_evaluated_once','protocol_version':sealed['protocol_version'],'test_accessed':True,'metrics_sha256':sha(out)})
 print(json.dumps({'status':'test_evaluated_once','metrics':str(out),'rows':len(rows)},indent=2))

def main():
 ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('seal'); t=sub.add_parser('train'); t.add_argument('--L',type=int,required=True); t.add_argument('--model',required=True); t.add_argument('--seed',type=int,required=True); sub.add_parser('evaluate-once'); a=ap.parse_args()
 if a.cmd=='seal': seal()
 elif a.cmd=='train': train_one(a.model,a.L,a.seed)
 else: evaluate_once()
if __name__=='__main__': main()
