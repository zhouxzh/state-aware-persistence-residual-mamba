"""Read-only structural validation of compact encoder follow-up tables.

Does not load predictions or generate observations. It rejects missing, duplicate
or nonfinite data before the paper consumes frozen analysis output.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

FAMILIES = {'C1': 6, 'C2': 16, 'C2-interaction': 4,
            'C3': 2, 'C3-interaction': 2, 'C4': 12}
MODEL_LENGTHS = {(384, m) for m in ('LinPhi', 'MLPPhi', 'TransformerPhi',
                                  'Transformer0', 'MambaPhi', 'Mamba0')}
MODEL_LENGTHS |= {(length, model) for length in (96, 768)
                 for model in ('TransformerPhi', 'Transformer0', 'MambaPhi', 'Mamba0')}
MODEL_LENGTHS |= {(length, 'M0') for length in (96, 384, 768)}
GROUP_SIZES = {'S4': 100, 'S6': 100, 'N2': 100, 'N8': 100, 'ALL': 1100}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def validate(sequence_rows, comparison_rows, group_sizes=None):
    sizes = GROUP_SIZES if group_sizes is None else group_sizes
    errors, keys, populations, family_counts = [], set(), {}, Counter()
    for row in sequence_rows:
        try:
            length, horizon = int(row['L']), int(row['H'])
            model, group, series = row['model'], row['group'], row['series_id']
            key = (length, horizon, model, group, series)
            if key in keys:
                errors.append(f'duplicate sequence key: {key}')
            keys.add(key)
            if horizon != 24 or (length, model) not in MODEL_LENGTHS or group not in sizes:
                errors.append(f'unregistered sequence condition: {key}')
            mean, sd = float(row['seed_mean_rmse']), float(row['seed_sd_rmse'])
            if not all(math.isfinite(v) and v >= 0 for v in (mean, sd)):
                errors.append(f'nonfinite or negative RMSE: {key}')
            count = int(row['origin_count'])
            if count < 1:
                errors.append(f'empty origin group: {key}')
            populations.setdefault((length, model, group), {})[series] = count
        except (ValueError, KeyError) as exc:
            errors.append(f'invalid sequence row: {exc}')
    for length, model in sorted(MODEL_LENGTHS):
        for group, count in sizes.items():
            population = populations.get((length, model, group), {})
            if len(population) != count:
                errors.append(f'wrong population size: {(length, model, group)} {len(population)} != {count}')
            reference = populations.get((384, 'M0', group), {})
            if population != reference:
                errors.append(f'unpaired series/origin counts: {(length, model, group)}')
    contrast_keys = set()
    for row in comparison_rows:
        try:
            family = row['family']
            family_counts[family] += 1
            key = (family, row['contrast'], row['group'])
            if key in contrast_keys:
                errors.append(f'duplicate contrast: {key}')
            contrast_keys.add(key)
            if int(row['n_series']) != sizes[row['group']]:
                errors.append(f'wrong paired count: {key}')
            estimate, lo, hi = (float(row[k]) for k in ('estimate', 'ci_low', 'ci_high'))
            if not all(math.isfinite(v) for v in (estimate, lo, hi)) or lo > hi:
                errors.append(f'invalid effect interval: {key}')
            raw, adjusted = float(row['p_signflip_raw']), float(row['p_holm'])
            if not (0 <= raw <= adjusted <= 1):
                errors.append(f'invalid adjusted p-value: {key}')
        except (ValueError, KeyError) as exc:
            errors.append(f'invalid comparison row: {exc}')
    if dict(family_counts) != FAMILIES:
        errors.append(f'comparison family mismatch: {dict(family_counts)}')
    return {'passed': not errors, 'errors': errors,
            'sequence_rows': len(sequence_rows), 'comparison_rows': len(comparison_rows),
            'family_counts': dict(family_counts),
            'scope': 'structural integrity only; not a scientific validity certificate'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    args = parser.parse_args()
    result = validate(read_csv(args.run_root / 'metrics/sequence_rmse.csv'),
                      read_csv(args.run_root / 'metrics/paired_comparisons.csv'))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
