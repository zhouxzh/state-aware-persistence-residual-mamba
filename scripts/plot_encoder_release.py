"""Plot only complete, hash-bound encoder follow-up tables.

No data generation, fit, bootstrap or p-value recalculation takes place here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from check_encoder_release import read_csv, validate

GROUP_NAMES={'S4':'Seen trend break','S6':'Seasonal shape change','N2':'Unseen jump','N8':'Random walk'}


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def family_figure(rows, family, groups, title, destination, version):
    subsets=[[r for r in rows if r['family']==family and r['group']==g] for g in groups]
    height=max(3.0, .5*max(len(s) for s in subsets)+1.8)
    fig,axes=plt.subplots(1,len(groups),figsize=(12,height),squeeze=False,layout='constrained')
    for ax,g,subset in zip(axes[0],groups,subsets):
        if not subset: raise ValueError('Missing group '+g)
        for i,row in enumerate(subset):
            y=len(subset)-i-1
            lo,hi,estimate=(float(row[k]) for k in ('ci_low','ci_high','estimate'))
            ax.plot([lo,hi],[y,y],color='#26768b',linewidth=1.4)
            ax.scatter([estimate],[y],color='#26768b',s=24,zorder=3)
        ax.axvline(0,color='#666666',linewidth=.7,linestyle='--')
        ax.set_yticks(range(len(subset)))
        labels=[r['contrast'].replace('MambaPhi-L384 minus ','Mamba+phi minus ').replace('-L384','').replace(' at L384','').replace('persistence-relative error change','relative-error change') for r in subset]
        ax.set_yticklabels(labels[::-1],fontsize=8)
        ax.set_title(GROUP_NAMES[g],fontsize=10)
        ax.set_xlabel('Paired series-level RMSE difference',fontsize=9)
        ax.spines[['top','right']].set_visible(False)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    study_labels = {'encoder_l_v1.r6': 'Study 2: matched-encoder follow-up (disclosed amendments)'}
    scope = ('ARTIFICIAL UNIT-TEST FIXTURE: NOT EXPERIMENTAL RESULTS' if version.startswith('UNIT_')
             else study_labels.get(version, f'{version}: follow-up with documented deviations'))
    fig.suptitle(title+'\n'+scope,fontsize=11)
    fig.savefig(destination.with_suffix('.pdf'),bbox_inches='tight')
    fig.savefig(destination.with_suffix('.png'),dpi=250,bbox_inches='tight')
    plt.close(fig)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-root',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    root,out=args.run_root,args.output_dir
    protocol=json.loads((root/'protocol/protocol.json').read_text(encoding='utf-8-sig'))
    ledger=json.loads((root/'protocol/test_access_ledger.json').read_text(encoding='utf-8-sig'))
    analysis=json.loads((root/'metrics/analysis_manifest.json').read_text(encoding='utf-8-sig'))
    source=root/'metrics/sequence_rmse.csv'; comparison=root/'metrics/paired_comparisons.csv'
    if not ledger.get('test_numeric_materialized') or digest(source)!=ledger['metrics_sha256']:
        raise SystemExit('Test evidence incomplete or checksum mismatch')
    if digest(source)!=analysis['source_metrics_sha256'] or digest(comparison)!=analysis['output_sha256']:
        raise SystemExit('Analysis evidence hash mismatch')
    rows=read_csv(comparison); verdict=validate(read_csv(source),rows)
    if not verdict['passed']: raise SystemExit(json.dumps(verdict))
    out.mkdir(parents=True,exist_ok=True)
    tasks=[('C1',('S4','S6'),'Matched-input encoder comparisons','encoder_comparisons'),
           ('C3',('S4','S6'),'Mamba: summary-on minus summary-off','state_increment'),
           ('C3-interaction',('S4','S6'),'State-summary by encoder interaction','state_encoder_interaction'),
           ('C2-interaction',('S4','S6'),'Encoder by lookback interaction','lookback_interaction'),
           ('C4',('N2','N8'),'Negative controls: residual forecast minus persistence','negative_controls')]
    for _,_,_,slug in tasks:
        if any((out/(slug+ext)).exists() for ext in ('.pdf','.png')):
            raise SystemExit('Output exists; choose a new directory')
    manifest={'actual_protocol':protocol['protocol_version'],'comparisons_sha256':digest(comparison),'plot_script_sha256':digest(Path(__file__)),'scope':'ordinary percentile95% intervals; inferential decisions require separate Holm p-values','deviations_disclosed':True,'files':[]}
    for family,groups,title,slug in tasks:
        family_figure(rows,family,groups,title,out/slug,protocol['protocol_version'])
        for ext in ('.pdf','.png'):
            p=out/(slug+ext);manifest['files'].append({'path':p.name,'sha256':digest(p),'family':family})
    (out/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'plotted_from_verified_tables','actual_protocol':protocol['protocol_version'],'figures':len(tasks)},indent=2))


if __name__=='__main__': main()
