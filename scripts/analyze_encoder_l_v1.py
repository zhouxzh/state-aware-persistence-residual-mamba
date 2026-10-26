#!/usr/bin/env python3
"""Frozen paired-series analysis for encoder_l_v1; no model/threshold selection."""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
B=10000; RNG_SEED=20261220

def sha(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def rows_csv(p):
 with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def p_signflip(d,rng):
 obs=abs(float(np.mean(d))); signs=rng.choice(np.array([-1.,1.]),size=(B,len(d))); null=np.abs((signs*d).mean(axis=1)); return float((1+np.sum(null>=obs))/(B+1))
def summarize(name,family,group,ids,d,rng):
 n=len(d); ix=rng.integers(0,n,size=(B,n)); boot=d[ix].mean(axis=1); lo,hi=np.quantile(boot,[.025,.975]); return {'family':family,'contrast':name,'group':group,'n_series':n,'estimate':float(d.mean()),'ci_low':float(lo),'ci_high':float(hi),'p_signflip_raw':p_signflip(d,rng)}
def holm(p):
 p=np.asarray(p); order=np.argsort(p); adjusted=np.empty_like(p); running=0.
 for rank,i in enumerate(order): running=max(running,min(1.,(len(p)-rank)*p[i])); adjusted[i]=running
 return adjusted
def map_series(rows,group,L,model):
 return {r['series_id']:float(r['seed_mean_rmse']) for r in rows if r['group']==group and int(r['L'])==L and r['model']==model}
def pair(rows,group,L,left,right):
 a,b=map_series(rows,group,L,left),map_series(rows,group,L,right); ids=sorted(set(a)&set(b));
 if not ids: raise ValueError(f'empty pair: {group} L{L} {left}-{right}')
 return ids,np.asarray([a[i]-b[i] for i in ids])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--run-root',type=Path,required=True); a=ap.parse_args(); root=a.run_root; inp=root/'metrics/sequence_rmse.csv'; rows=rows_csv(inp); rng=np.random.default_rng(RNG_SEED); out=[]
 # C1 family: registered Mamba-phi comparisons at L384/H24 on S4/S6.
 for g in ('S4','S6'):
  for ref in ('LinPhi','MLPPhi','TransformerPhi'):
   ids,d=pair(rows,g,384,'MambaPhi',ref); out.append(summarize(f'MambaPhi-L384 minus {ref}-L384','C1',g,ids,d,rng))
 # C2: paired lookback change in persistence-relative error; interaction Mamba vs Transformer.
 for g in ('S4','S6'):
  for model in ('MambaPhi','Mamba0','TransformerPhi','Transformer0'):
   for lo,hi in ((96,384),(384,768)):
    predlo,maplo=map_series(rows,g,lo,model),map_series(rows,g,lo,'M0'); predhi,maphi=map_series(rows,g,hi,model),map_series(rows,g,hi,'M0'); ids=sorted(set(predlo)&set(maplo)&set(predhi)&set(maphi)); d=np.asarray([(predhi[i]-maphi[i])-(predlo[i]-maplo[i]) for i in ids]); out.append(summarize(f'{model} persistence-relative error change L{hi}-L{lo}','C2',g,ids,d,rng))
  for lo,hi in ((96,384),(384,768)):
   mlo,mhi=map_series(rows,g,lo,'MambaPhi'),map_series(rows,g,hi,'MambaPhi'); tlo,thi=map_series(rows,g,lo,'TransformerPhi'),map_series(rows,g,hi,'TransformerPhi'); ids=sorted(set(mlo)&set(mhi)&set(tlo)&set(thi)); d=np.asarray([(mhi[i]-mlo[i])-(thi[i]-tlo[i]) for i in ids]); out.append(summarize(f'encoder-by-lookback interaction L{hi}-L{lo}','C2-interaction',g,ids,d,rng))
 # C3: state-summary increment and state-by-encoder interaction.
 for g in ('S4','S6'):
  ids,d=pair(rows,g,384,'MambaPhi','Mamba0'); out.append(summarize('Mamba phi-on minus phi-zero at L384','C3',g,ids,d,rng))
  mp,m0=map_series(rows,g,384,'MambaPhi'),map_series(rows,g,384,'Mamba0'); tp,t0=map_series(rows,g,384,'TransformerPhi'),map_series(rows,g,384,'Transformer0'); ids=sorted(set(mp)&set(m0)&set(tp)&set(t0)); d=np.asarray([(mp[i]-m0[i])-(tp[i]-t0[i]) for i in ids]); out.append(summarize('state-by-encoder interaction Mamba vs Transformer','C3-interaction',g,ids,d,rng))
 # C4: residual models against persistence on N2/N8 at L384.
 for g in ('N2','N8'):
  for model in ('LinPhi','MLPPhi','TransformerPhi','Transformer0','MambaPhi','Mamba0'):
   ids,d=pair(rows,g,384,model,'M0'); out.append(summarize(f'{model}-M0 at L384','C4',g,ids,d,rng))
 for family in sorted({r['family'] for r in out}):
  ix=[i for i,r in enumerate(out) if r['family']==family]; adj=holm([out[i]['p_signflip_raw'] for i in ix])
  for j,i in enumerate(ix):out[i]['p_holm']=float(adj[j])
 output=root/'metrics/paired_comparisons.csv'; output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 manifest={'protocol':'encoder_l_v1.r3','source_metrics_sha256':sha(inp),'analysis_script_sha256':sha(Path(__file__)),'bootstrap_replicates':B,'bootstrap_seed':RNG_SEED,'bootstrap_interval':'paired percentile 95% over independent series','p_value':'paired random sign-flip test under symmetric null, Monte Carlo +1 correction','holm':'within family listed in comparison_family column','unit':'independent series after matched seed-averaged per-series RMSE','rows':len(out),'output_sha256':sha(output)}
 (root/'metrics/analysis_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
