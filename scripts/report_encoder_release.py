"""Render verified compact encoder results without changing estimates or tests.

No training/data-generation code is contained here. Requires the actual sealed
protocol, one-time test ledger and frozen analysis outputs from the server.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

from check_encoder_release import read_csv, validate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verdict_rows(comparisons):
    rows = []
    for item in comparisons:
        estimate = float(item['estimate'])
        p = float(item['p_holm'])
        lo, hi = float(item['ci_low']), float(item['ci_high'])
        if item['family'] == 'C4':
            decision = 'review_required' if estimate < 0 and p < .05 else 'no_alarm_triggered'
        elif estimate < 0 and hi < 0 and p < .05:
            decision = 'negative_difference_supported'
        elif estimate > 0 and lo > 0 and p < .05:
            decision = 'positive_difference_supported'
        else:
            decision = 'direction_not_established'
        rows.append({**item, 'comparison_verdict': decision,
                     'evidence_scope': 'source-locked follow-up with pre-test deviations'})
    return rows


def markdown(comparisons, version, sequence_rows, resources, deviations):
    verdicts = verdict_rows(comparisons)
    lines = [f'# {version}: source-locked follow-up results', '',
             '**Status:** observed test results with documented pre-test deviations; not deviation-free preregistered confirmation.', '',
             'This report does not pool canonical_v2 or stopped encoder attempts. The deviations below must accompany any publication use:', '']
    lines.extend('- ' + item for item in deviations)
    c1 = [r for r in verdicts if r['family'] == 'C1']
    c3 = [r for r in verdicts if r['family'] == 'C3']
    alarms = [r for r in verdicts if r['family'] == 'C4' and r['comparison_verdict'] == 'review_required']
    lines += ['', '## Outcome summary', '',
              f'- C1 favorable comparisons: {sum(r["comparison_verdict"] == "negative_difference_supported" for r in c1)} / {len(c1)}. The full conjunction requires all six; absence of significance is not equivalence.',
              f'- C3 Mamba summary-on versus summary-off favorable comparisons: {sum(r["comparison_verdict"] == "negative_difference_supported" for r in c3)} / {len(c3)}.',
              f'- C4 negative-control alarms requiring review: {len(alarms)} / 12. No alarm does not certify absence of leakage.',
              '- C2 and interaction estimates are shown in full; do not infer an interaction from separate significance tests.',
              '- All conclusions are limited to H=24 and the listed implementations. No internal Mamba selectivity ablation was run.', '',
              '## L384 primary-subset RMSE', '',
              '| Model | S4 | S6 | N2 | N8 |', '|---|---:|---:|---:|---:|']
    models = ['M0', 'LinPhi', 'MLPPhi', 'TransformerPhi', 'Transformer0', 'MambaPhi', 'Mamba0']
    for model in models:
        values = []
        for group in ['S4', 'S6', 'N2', 'N8']:
            v = [float(r['seed_mean_rmse']) for r in sequence_rows
                 if int(r['L']) == 384 and r['model'] == model and r['group'] == group]
            values.append(f'{statistics.mean(v):.6f}')
        lines.append('| ' + ' | '.join([model] + values) + ' |')
    lines += ['', 'RMSE is averaged over independent series after each series\'s five seed-specific RMSEs have been averaged. These rows are not an ensemble-RMSE calculation.', '',
              '## Resource measurements', '',
              '| L | Model | Parameters | Median train seconds | Median peak memory MiB | Median inference seconds |',
              '|---:|---|---:|---:|---:|---:|']
    resource_groups = {}
    for item in resources:
        key = (int(item['L']), item['model'])
        resource_groups.setdefault(key, []).append(item)
    for (length, model), group_rows in sorted(resource_groups.items()):
        fields = []
        for name in ('parameters','train_seconds','peak_memory_mib','test_inference_seconds_mean'):
            fields.append(statistics.median(float(x[name]) for x in group_rows))
        lines.append(f'| {length} | {model} | {fields[0]:.0f} | {fields[1]:.3f} | {fields[2]:.3f} | {fields[3]:.4f} |')
    lines += ['', 'Resource medians are descriptive on the recorded hardware/runtime only; they do not establish general asymptotic superiority.', '',
              '## Complete contrast table', '',

              '| Family | Group | Contrast | Estimate | Ordinary 95% CI | Holm p | Decision |',
              '|---|---|---|---:|---|---:|---|']
    for r in verdicts:
        lines.append(f'| {r["family"]} | {r["group"]} | {r["contrast"]} | {float(r["estimate"]):.6f} | [{float(r["ci_low"]):.6f}, {float(r["ci_high"]):.6f}] | {float(r["p_holm"]):.6f} | {r["comparison_verdict"]} |')
    lines += ['', 'Intervals are ordinary paired-series percentile bootstrap intervals, not Holm-adjusted intervals. Sign-flip p-values assume a symmetric paired-difference null. C4 alarms pause favorable interpretation until generator/input review; a positive estimate means higher left-model error, not merely a failed test.', '']
    return '\n'.join(lines), verdicts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.run_root, args.output_dir
    protocol = load(root / 'protocol/protocol.json')
    ledger = load(root / 'protocol/test_access_ledger.json')
    analysis = load(root / 'metrics/analysis_manifest.json')
    metrics = root / 'metrics/sequence_rmse.csv'
    comparisons_file = root / 'metrics/paired_comparisons.csv'
    if not ledger.get('test_numeric_materialized'):
        raise SystemExit('No completed test evaluation; results must remain pending.')
    if digest(metrics) != ledger['metrics_sha256'] or digest(metrics) != analysis['source_metrics_sha256']:
        raise SystemExit('Input sequence-metrics checksum mismatch.')
    if digest(comparisons_file) != analysis['output_sha256']:
        raise SystemExit('Comparison checksum mismatch.')
    resources_file = root / 'resources/resource_metrics.csv'
    if not resources_file.is_file():
        raise SystemExit('Resource table missing; report cannot claim C5 completeness.')
    sequences, comparisons, resources = read_csv(metrics), read_csv(comparisons_file), read_csv(resources_file)
    integrity = validate(sequences, comparisons)
    resource_errors = []
    registered = {(int(c['L']), c['model'], int(c['seed'])) for c in protocol['registered_cells']}
    observed = set()
    for row in resources:
        try:
            key = (int(row['L']), row['model'], int(row['seed']))
            if key in observed: resource_errors.append(f'duplicate resource row: {key}')
            observed.add(key)
            for name in ('parameters', 'train_seconds', 'peak_memory_mib', 'test_inference_seconds_mean'):
                value = float(row[name])
                if not math.isfinite(value) or value < 0: resource_errors.append(f'invalid {name}: {key}')
        except (KeyError, ValueError) as exc:
            resource_errors.append(f'invalid resource row: {exc}')
    if observed != registered: resource_errors.append(f'resource cell set mismatch: expected={len(registered)}, observed={len(observed)}')
    integrity['resource_rows'] = len(resources)
    integrity['resource_errors'] = resource_errors
    integrity['passed'] = integrity['passed'] and not resource_errors
    if not integrity['passed']:
        raise SystemExit(json.dumps(integrity, indent=2))
    deviations = [
        'MLP was actually hidden=[125,125] at L384, whereas the descriptive model_spec retained [64,64]. The sealed runner and 68,024-parameter inventory determine actual execution.',
        'Sampling used one advancing replacement-sampler RNG per cell, not the seed_plus_epoch reseeding described in config.',
        'The locked C4 family contains six heads including Transformer0, while older prose listed five.',
        'The frozen analyzer manifest labels r3; the binding manifest preserves that field and assigns the output to the actual sealed run.',
        'Only recorded end-to-end timings/allocated memory are available; no warmed-up kernel throughput or FLOPs claims are supported.'
    ]
    text, verdicts = markdown(comparisons, protocol['protocol_version'], sequences, resources, deviations)
    out.mkdir(parents=True, exist_ok=True)
    report = out / 'encoder_results_report.md'
    table = out / 'comparison_verdicts.csv'
    binding = out / 'release_binding.json'
    if any(p.exists() for p in (report, table, binding)):
        raise SystemExit('Outputs exist; use a new report directory to preserve provenance.')
    report.write_text(text, encoding='utf-8')
    with table.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(verdicts[0]))
        writer.writeheader()
        writer.writerows(verdicts)
    record = {'actual_protocol': protocol['protocol_version'],
              'original_analyzer_protocol_field': analysis['protocol'],
              'protocol_sha256': digest(root / 'protocol/protocol.json'),
              'source_metrics_sha256': digest(metrics),
              'comparisons_sha256': digest(comparisons_file),
              'resources_sha256': digest(resources_file),
              'test_access_ledger_sha256': digest(root / 'protocol/test_access_ledger.json'),
              'report_script_sha256': digest(Path(__file__)),
              'report_sha256': digest(report), 'verdict_table_sha256': digest(table),
              'integrity_check': integrity, 'deviations': deviations,
              'status': 'follow-up with pre-test disclosed deviations; not full protocol compliance'}
    binding.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(report), 'binding': str(binding), 'actual_protocol': protocol['protocol_version']}, indent=2))


if __name__ == '__main__':
    main()
