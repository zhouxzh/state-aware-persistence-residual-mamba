#!/usr/bin/env python
"""Frozen T0-T8 synthetic mechanism experiment for SAPR persistence residuals."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "sim_v1")

from model.StateAwarePersistenceResidualMamba import build_model
from utils.sapr_mamba.analysis import artifact_entry, write_csv
from utils.sapr_mamba.data import SeriesInfo, WindowDataset, make_origins
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import DATA_ROOT, RESULT_ROOT, RUNLOG_ROOT, atomic_write_json, code_hashes, git_state, sha256_path, utc_now, write_task_manifest


STUDY_VERSION = os.environ["SAPR_MAMBA_VERSION"]
if STUDY_VERSION not in {"sim_v1", "sim_v2", "sim_v3", "sim_v4", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_confirm_v1"} and not (STUDY_VERSION.startswith("bocpd_e") and STUDY_VERSION[7:].isdigit()):
    raise ValueError("sapr_sim runner requires a configured simulation namespace")
CONFIG = REPO_ROOT / "configs" / f"sapr_mamba_{STUDY_VERSION}"
DOCS = REPO_ROOT / "docs" / "current"
RESULTS = RESULT_ROOT / "synthetic"
REPRODUCIBILITY = REPO_ROOT / "reproducibility" / f"sapr_{STUDY_VERSION}"
TYPES = ("stable", "visible_level_shift", "future_jump", "continuing_trend", "trend_break", "stable_season", "seasonal_change", "variance_shift", "random_walk")
_DATASET_AUDIT_CACHE: dict[tuple[str, str, str], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def active_types(settings: dict) -> tuple[str, ...]:
    return tuple(str(item) for item in settings.get("mechanisms", TYPES))


def cfg(name: str) -> dict:
    return json.loads((CONFIG / f"{name}.json").read_text(encoding="utf-8"))


def preflight() -> dict:
    import subprocess
    payload = {"timestamp": utc_now(), "repository": str(REPO_ROOT), "git": git_state(), "code_hashes": code_hashes()}
    for name, command in (("processes", ["bash", "-lc", "ps -eo pid,ppid,stat,etime,cmd | rg -i 'python.*(sapr|mamba)|torchrun' || true"]), ("gpu", ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"]), ("disk", ["df", "-h", str(REPO_ROOT)])):
        try: payload[name] = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
        except Exception as exc: payload[name] = repr(exc)
    path = RUNLOG_ROOT / f"preflight_{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')}.json"
    atomic_write_json(path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def generate_one(mechanism: str, index: int, split: str, settings: dict, rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    base, length, period = settings["base"], int(settings["length"]), int(settings["seasonal_period"])
    noise = rng.normal(0.0, float(base["innovation_std"]), length)
    visible_points = tuple(int(value) for value in base["visible_change_points"])
    cp_visible = visible_points[index % len(visible_points)]
    future_origins = tuple(int(value) for value in base["future_jump_origins"])
    cp_future = future_origins[index % len(future_origins)] + int(base["future_jump_offset"])
    if mechanism == "variance_shift": noise[cp_visible:] *= float(base["variance_multiplier"])
    if mechanism == "random_walk" or (mechanism == "future_jump" and base.get("future_jump_baseline") == "random_walk"):
        values = np.cumsum(noise)
        cp = cp_future if mechanism == "future_jump" else -1
        if mechanism == "future_jump":
            direction = -1.0 if base.get("future_jump_direction_policy") == "balanced_by_index" and index % 2 == 0 else 1.0
            values[cp_future:] += direction * float(base["jump_strength"])
    else:
        values = np.empty(length, dtype=np.float64)
        values[0] = noise[0]
        for t in range(1, length): values[t] = float(base["ar"]) * values[t - 1] + noise[t]
        time = np.arange(length, dtype=np.float64)
        cp = cp_visible
        if mechanism == "continuing_trend": values += float(base["trend_slope"]) * time
        elif mechanism == "stable_season": values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * time / period)
        elif mechanism == "visible_level_shift": values[cp_visible:] += float(base["jump_strength"])
        elif mechanism == "future_jump":
            direction = -1.0 if base.get("future_jump_direction_policy") == "balanced_by_index" and index % 2 == 0 else 1.0
            values[cp_future:] += direction * float(base["jump_strength"]); cp = cp_future
        elif mechanism == "trend_break": values[cp_visible:] += (time[cp_visible:] - cp_visible) * float(base["trend_break_slope"])
        elif mechanism == "seasonal_change": values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * time / period); values[cp_visible:] += float(base["seasonal_change_amplitude"]) * np.sin(2 * np.pi * time[cp_visible:] / period + np.pi / 3)
        elif mechanism == "gradual_drift":
            duration = int(base.get("gradual_drift_duration", 96))
            ramp = np.clip((time - cp_visible) / max(duration, 1), 0.0, 1.0)
            values += ramp * float(base.get("gradual_drift_strength", 3.0))
        elif mechanism == "weak_change": values[cp_visible:] += float(base.get("weak_change_strength", 0.35))
        elif mechanism in {"stable", "variance_shift"}: pass
        else: raise ValueError(mechanism)
    return values.astype(np.float32), {"series_id": f"{split}_{mechanism}_{index:04d}", "mechanism": mechanism, "strength": 0.0 if mechanism in {"stable", "stable_season", "random_walk"} else 1.0, "change_point": cp, "period": period, "future_jump_direction": direction if mechanism == "future_jump" else 0.0, "train_end": length, "valid_end": length}


def generate() -> dict:
    settings, protocol = cfg("synthetic"), cfg("protocol")
    root = DATA_ROOT / "synthetic"; root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(settings["generator_seed"]))
    manifest = {"study": STUDY_VERSION, "generator_version": settings["generator_version"], "created_at": utc_now(), "splits": {}}
    for split in ("train", "validation", "test"):
        values=[]; records=[]
        for mechanism in active_types(settings):
            count = int(settings.get("mechanism_split_overrides", {}).get(mechanism, {}).get(split, settings["splits"][split]))
            for index in range(count):
                value, record = generate_one(mechanism, index, split, settings, rng); values.append(value); records.append(record)
        array = np.stack(values)
        path = root / f"{split}.npz"; np.savez_compressed(path, values=array)
        roster = root / f"{split}_roster.json"; atomic_write_json(roster, {"split": split, "records": records})
        manifest["splits"][split] = {"series_count": len(records), "data_sha256": sha256_path(path), "roster_sha256": sha256_path(roster)}
    atomic_write_json(root / "data_manifest.json", manifest)
    threshold, coverage = coverage_report(settings, protocol)
    atomic_write_json(root / "state_threshold.json", threshold)
    lock = {
        "study": STUDY_VERSION,
        "protocol_version": protocol["protocol_version"],
        "generator_version": settings["generator_version"],
        "created_at": utc_now(),
        "config_hashes": {path.name: sha256_path(path) for path in sorted(CONFIG.glob("*.json"))},
        "data_manifest_sha256": sha256_path(root / "data_manifest.json"),
        "state_threshold_sha256": sha256_path(root / "state_threshold.json"),
        "coverage_sha256": None,
        "runner_sha256": sha256_path(Path(__file__)),
    }
    atomic_write_json(DOCS / f"sapr_{STUDY_VERSION}_coverage.json", coverage)
    (DOCS / f"sapr_{STUDY_VERSION}_coverage.md").write_text(coverage_markdown(coverage), encoding="utf-8")
    lock["coverage_sha256"] = sha256_path(DOCS / f"sapr_{STUDY_VERSION}_coverage.json")
    atomic_write_json(REPRODUCIBILITY / "configuration_lock.json", lock)
    print(json.dumps({"manifest": manifest, "coverage_passed": coverage["passed"]}, indent=2, sort_keys=True))
    return coverage


def load(split: str) -> tuple[np.ndarray, list[dict]]:
    with np.load(DATA_ROOT / "synthetic" / f"{split}.npz") as payload: values = payload["values"]
    records = json.loads((DATA_ROOT / "synthetic" / f"{split}_roster.json").read_text(encoding="utf-8"))["records"]
    return values, records


def true_label(record: dict, origin: int, horizon: int, delay: int) -> str:
    mechanism, cp = record["mechanism"], int(record["change_point"])
    if mechanism in {"stable", "stable_season", "random_walk"}: return "stable"
    if mechanism == "continuing_trend": return "visible_change"
    # Targets cover [origin, origin + horizon); a jump at the first target is
    # still absent from the available history, while one at the exclusive end is not evaluated.
    if mechanism == "future_jump": return "unseen_change" if origin <= cp < origin + horizon else "stable"
    return "visible_change" if origin >= cp + delay else "stable"


def calibration_thresholds(values: np.ndarray, infos: list[SeriesInfo], settings: dict, policy: dict) -> np.ndarray:
    """Calibrate one causal trigger threshold per series from its early prefix."""
    input_length, horizon = int(settings["input_length"]), int(settings["maximum_horizon"])
    calibration_end = int(policy["calibration_end"])
    stride = int(settings["origin_stride"])
    rows = [(series_index, origin) for series_index in range(len(infos)) for origin in range(input_length, calibration_end + 1, stride) if origin + horizon <= values.shape[1]]
    if not rows:
        raise ValueError("per-series threshold calibration has no valid origins")
    origins = np.asarray(rows, dtype=np.int64)
    calibration = WindowDataset(
        values, infos, origins, input_length, horizon, 1e-6, float("inf"),
        state_score_mode=str(settings.get("state_score_mode", "max_abs_feature")),
    )
    thresholds = np.empty(len(infos), dtype=np.float64)
    for series_index in range(len(infos)):
        scores = calibration.audit_change_score[origins[:, 0] == series_index]
        if scores.size == 0:
            raise ValueError(f"missing calibration scores for series {series_index}")
        thresholds[series_index] = float(np.clip(np.quantile(scores, float(policy["quantile"])), float(policy["minimum"]), float(policy["maximum"])))
    return thresholds


def dataset(split: str, threshold: float, settings: dict, feature_permutation_seed: int | None = None) -> tuple[WindowDataset, list[dict], np.ndarray]:
    values, records = load(split); length = int(settings["length"]); horizon = int(settings["maximum_horizon"]); input_length = int(settings["input_length"])
    infos = [SeriesInfo(record["series_id"], int(settings["seasonal_period"]), length, length, STUDY_VERSION, record["mechanism"], float(record["strength"]), int(record["change_point"])) for record in records]
    origins = make_origins(values, infos, input_length, horizon, "all", int(settings["origin_stride"]))
    origin_start = int(settings.get("evaluation_origin_start", input_length))
    origins = origins[origins[:, 1] >= origin_start]
    effective_threshold = calibration_thresholds(values, infos, settings, threshold) if isinstance(threshold, dict) and threshold.get("mode") == "per_series_calibration_prefix" else threshold
    state_mode = str(settings.get("state_score_mode", "max_abs_feature"))
    cache_key = (split, state_mode, json.dumps(threshold, sort_keys=True) if isinstance(threshold, dict) else repr(threshold))
    ds = WindowDataset(
        values, infos, origins, input_length, horizon, 1e-6, effective_threshold,
        feature_permutation_seed=feature_permutation_seed,
        cached_features=_DATASET_AUDIT_CACHE.get(cache_key),
        state_score_mode=state_mode,
        state_score_parameters=dict(settings.get("state_score_parameters", {})),
    )
    _DATASET_AUDIT_CACHE.setdefault(cache_key, ds.cached_features())
    metadata = [{"series_id": r["series_id"], "mechanism": r["mechanism"], "strength": r["strength"], "training_std": max(float(np.std(values[i], ddof=0)), 1e-6)} for i, r in enumerate(records)]
    labels = np.asarray([true_label(records[int(s)], int(o), horizon, int(settings["change_signal_delay"])) for s, o in origins], dtype=object)
    return ds, metadata, labels


def coverage_report(settings: dict, protocol: dict) -> tuple[dict, dict]:
    policy = protocol["state_threshold"]
    if policy.get("mode") == "per_series_calibration_prefix":
        threshold_payload = {"mode": "per_series_calibration_prefix", "source": "each series causal calibration prefix", "quantile": policy["quantile"], "minimum": policy["minimum"], "maximum": policy["maximum"], "calibration_end": policy["calibration_end"]}
    else:
        train_ds, _, _ = dataset("train", 1e99, settings)
        scores = train_ds.audit_change_score
        threshold_payload = {"threshold": float(np.clip(np.quantile(scores, float(policy["quantile"])), float(policy["minimum"]), float(policy["maximum"]))), "source": "train origins only", "quantile": policy["quantile"], "scores": int(len(scores))}
    test_ds, _, labels = dataset("test", threshold_payload if "mode" in threshold_payload else threshold_payload["threshold"], settings)
    detector = np.where(test_ds.audit_state == 1, "change", "stable")
    rows=[]; gate=protocol["coverage_gate"]; passed=True
    discrimination = protocol.get("detector_discrimination", {})
    required_discrimination = set(discrimination.get("required_mechanisms", []))
    minimum_lift = float(discrimination.get("minimum_visible_minus_stable_rate", float("-inf")))
    diagnostics = set(str(item) for item in settings.get("diagnostic_mechanisms", []))
    for mechanism in active_types(settings):
        mask = np.asarray([info.mechanism == mechanism for info in test_ds.infos], dtype=bool)[test_ds.origins[:, 0]]
        true_counts = Counter(labels[mask]); det_counts = Counter(detector[mask])
        stable_mask, visible_mask = mask & (labels == "stable"), mask & (labels == "visible_change")
        stable_rate = float(np.mean(test_ds.audit_state[stable_mask])) if stable_mask.any() else None
        visible_rate = float(np.mean(test_ds.audit_state[visible_mask])) if visible_mask.any() else None
        lift = None if stable_rate is None or visible_rate is None else visible_rate - stable_rate
        row={"mechanism": mechanism, "true_stable_origins": true_counts["stable"], "true_visible_origins": true_counts["visible_change"], "true_unseen_origins": true_counts["unseen_change"], "detector_stable_origins": det_counts["stable"], "detector_change_origins": det_counts["change"], "detector_stable_rate": stable_rate, "detector_visible_rate": visible_rate, "detector_visible_minus_stable": lift}
        # Require only labels relevant to each type; detector support remains explicit.
        if mechanism in diagnostics:
            row["true_requirement"] = 0
        elif mechanism in {"stable", "stable_season", "random_walk"}: row["true_requirement"] = gate["minimum_true_stable_origins"]
        elif mechanism == "future_jump": row["true_requirement"] = gate["minimum_true_unseen_origins"]
        else: row["true_requirement"] = gate["minimum_true_visible_origins"]
        relevant = row["true_stable_origins"] if mechanism in {"stable", "stable_season", "random_walk"} else row["true_unseen_origins"] if mechanism == "future_jump" else row["true_visible_origins"]
        discrimination_pass = mechanism not in required_discrimination or (lift is not None and lift >= minimum_lift)
        row["detector_discrimination_required"] = mechanism in required_discrimination
        row["detector_discrimination_pass"] = discrimination_pass
        if mechanism in diagnostics:
            row["passed"] = bool(relevant >= row["true_requirement"])
        else:
            row["passed"] = bool(relevant >= row["true_requirement"] and row["detector_stable_origins"] >= gate["minimum_detector_stable_origins"] and row["detector_change_origins"] >= gate["minimum_detector_change_origins"] and discrimination_pass)
        passed &= row["passed"]; rows.append(row)
    return threshold_payload, {"study": STUDY_VERSION, "created_at": utc_now(), "threshold": threshold_payload, "rows": rows, "passed": passed}


def coverage_markdown(report: dict) -> str:
    lines=["# SAPR Sim V1 Coverage", "", f"Passed: `{report['passed']}`", "", "| Mechanism | true stable | true visible | true unseen | detector stable | detector change | passed |", "|---|---:|---:|---:|---:|---:|---|"]
    for row in report["rows"]: lines.append(f"| {row['mechanism']} | {row['true_stable_origins']} | {row['true_visible_origins']} | {row['true_unseen_origins']} | {row['detector_stable_origins']} | {row['detector_change_origins']} | {row['passed']} |")
    return "\n".join(lines)+"\n"


def validation_detector_report(settings: dict) -> dict:
    """Validation-only detector diagnostics for exploratory BOCPD selection."""
    payload = json.loads((DATA_ROOT / "synthetic" / "state_threshold.json").read_text())
    threshold = payload if "mode" in payload else payload["threshold"]
    ds, _, labels = dataset("validation", threshold, settings)
    mechanism = np.asarray([info.mechanism for info in ds.infos], dtype=object)[ds.origins[:, 0]]
    rows = []
    for item in ("continuing_trend", "trend_break", "seasonal_change", "stable", "random_walk"):
        selected = mechanism == item
        stable = selected & (labels == "stable")
        visible = selected & (labels == "visible_change")
        stable_rate = float(np.mean(ds.audit_state[stable])) if stable.any() else None
        visible_rate = float(np.mean(ds.audit_state[visible])) if visible.any() else None
        rows.append({"mechanism": item, "stable_origins": int(stable.sum()), "visible_origins": int(visible.sum()), "stable_rate": stable_rate, "visible_rate": visible_rate, "visible_minus_stable": None if stable_rate is None or visible_rate is None else visible_rate - stable_rate})
    result = {"study": STUDY_VERSION, "split": "validation", "uses_test_targets": False, "created_at": utc_now(), "rows": rows}
    output = REPO_ROOT / "docs" / "analysis" / f"sapr_{STUDY_VERSION}" / "validation_detector_selection.json"
    atomic_write_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def loader(ds: WindowDataset, seed: int, samples: int | None, batch: int, shuffle: bool) -> DataLoader:
    if shuffle:
        generator=torch.Generator(); generator.manual_seed(seed)
        return DataLoader(ds, batch_size=batch, sampler=RandomSampler(ds, replacement=True, num_samples=int(samples), generator=generator), num_workers=0, pin_memory=True)
    return DataLoader(ds, batch_size=batch, shuffle=False, num_workers=0, pin_memory=True)


def model_forward(model: torch.nn.Module, x: torch.Tensor, phi: torch.Tensor, state: torch.Tensor) -> dict[str, torch.Tensor]:
    """Supply the binary state only to the explicit trigger-gate architecture."""
    if getattr(model, "gate_mode", None) == "trigger":
        return model(x, phi, state)
    return model(x, phi)


def train(model: torch.nn.Module, train_ds: WindowDataset, valid_ds: WindowDataset, device: torch.device, seed: int, protocol: dict, checkpoint: Path) -> dict:
    if not any(p.requires_grad for p in model.parameters()): return {"status":"not_trainable","epochs":0}
    optim=torch.optim.AdamW(model.parameters(), lr=float(protocol['training']['learning_rate']), weight_decay=float(protocol['training']['weight_decay']))
    scaler=torch.amp.GradScaler('cuda', enabled=device.type=='cuda' and bool(protocol['training']['amp']))
    best=float('inf'); stale=0
    for epoch in range(1,int(protocol['training']['max_epochs'])+1):
        model.train()
        for batch in loader(train_ds, seed + epoch, protocol['training']['samples_per_epoch'], int(protocol['training']['batch_size']), True):
            x=batch['x'].to(device); y=batch['y'].to(device); phi=batch['phi'].to(device); state=batch['gate_state'].to(device)
            optim.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type=='cuda' and bool(protocol['training']['amp'])): loss=torch.mean((model_forward(model,x,phi,state)['forecast']-y)**2)
            scaler.scale(loss).backward(); scaler.unscale_(optim); torch.nn.utils.clip_grad_norm_(model.parameters(),float(protocol['training']['gradient_clip_norm'])); scaler.step(optim); scaler.update()
        model.eval(); total=0.; n=0
        with torch.no_grad():
            for batch in loader(valid_ds, seed, None, int(protocol['training']['batch_size']), False):
                x=batch['x'].to(device);y=batch['y'].to(device);phi=batch['phi'].to(device);state=batch['gate_state'].to(device); total+=float(torch.mean((model_forward(model,x,phi,state)['forecast']-y)**2))*len(x);n+=len(x)
        value=total/max(n,1)
        if value<best: best=value;stale=0;checkpoint.parent.mkdir(parents=True,exist_ok=True);torch.save({'model':model.state_dict(),'seed':seed,'validation_mse':best},checkpoint)
        else:
            stale+=1
            if stale>=int(protocol['training']['patience']): break
        atomic_write_json(checkpoint.parent / 'training_progress.json', {'status':'running','epoch':epoch,'best_validation_mse':best,'current_validation_mse':value,'stale_epochs':stale,'updated_at':utc_now()})
    model.load_state_dict(torch.load(checkpoint,map_location=device,weights_only=True)['model'])
    atomic_write_json(checkpoint.parent / 'training_progress.json', {'status':'complete','epochs':epoch,'best_validation_mse':best,'updated_at':utc_now()})
    return {"status":"complete","epochs":epoch,"best_validation_mse":best}


def collect(model: torch.nn.Module, ds: WindowDataset, device: torch.device, seed: int, true_labels: np.ndarray) -> dict[str,np.ndarray]:
    out=defaultdict(list); model.eval(); offset=0
    with torch.no_grad():
        for batch in loader(ds,seed,None,128,False):
            x=batch['x'].to(device);y=batch['y'].to(device);phi=batch['phi'].to(device);state=batch['gate_state'].to(device);value=model_forward(model,x,phi,state)
            out['prediction'].append(value['forecast'].cpu().numpy());out['target'].append(y.cpu().numpy());out['gate'].append(value['gate'].cpu().numpy());out['residual'].append(value['residual'].cpu().numpy())
            for key in ('state','change_score','series_index','origin','phi'):out[key].append(batch[key].numpy())
            size=len(x);out['true_label'].append(true_labels[offset:offset+size]);offset+=size
    return {key:np.concatenate(value) for key,value in out.items()}


def task(model_id: str, seed: int, settings: dict, protocol: dict, threshold: float | dict) -> dict:
    root=RESULTS/f'{model_id}_seed{seed}'; manifest=root/'task_manifest.json'
    if manifest.is_file() and json.loads(manifest.read_text()).get('status')=='complete': return json.loads(manifest.read_text())
    started=utc_now(); shuffle_seed = seed + 9001 if model_id == 'M3-shuffle' else None
    state_shuffle_seed = seed + 19001 if model_id == 'M3-bocpd-shuffle' else None
    write_task_manifest(manifest, {'status':'running','model':model_id,'seed':seed,'started_at':started,'feature_permutation_seed':shuffle_seed,'state_permutation_seed':state_shuffle_seed})
    try:
        device=torch.device(protocol['training']['device']);torch.manual_seed(seed);np.random.seed(seed)
        train_ds,_,train_labels=dataset('train',threshold,settings,shuffle_seed);valid_ds,_,valid_labels=dataset('validation',threshold,settings,shuffle_seed);test_ds,metadata,labels=dataset('test',threshold,settings,shuffle_seed)
        if state_shuffle_seed is not None:
            for ds in (train_ds, valid_ds, test_ds):
                ds.state_permutation = np.random.default_rng(state_shuffle_seed).permutation(len(ds))
        if model_id == 'M3-oracle':
            for ds, truth in ((train_ds, train_labels), (valid_ds, valid_labels), (test_ds, labels)):
                ds.state_override = (truth == 'visible_change').astype(np.int8)
        spec=cfg('model_spec'); model=build_model(model_id,int(settings['maximum_horizon']),len(FEATURE_NAMES),spec,int(settings['input_length']),int(settings['seasonal_period'])).to(device)
        info=train(model,train_ds,valid_ds,device,seed,protocol,root/'checkpoint.pt'); arr=collect(model,test_ds,device,seed,labels)
        rows=[]
        for series in np.unique(arr['series_index']):
            sm=arr['series_index']==series
            for horizon in settings['horizons']:
                for label in ('stable','visible_change','unseen_change'):
                    mask=sm&(arr['true_label']==label)
                    if not mask.any():continue
                    err=arr['prediction'][mask,:horizon]-arr['target'][mask,:horizon];rows.append({'mechanism':metadata[int(series)]['mechanism'],'series_id':metadata[int(series)]['series_id'],'model':model_id,'seed':seed,'horizon':horizon,'true_label':label,'origins':int(mask.sum()),'rmse':float(np.sqrt(np.mean(err**2))),'gate_mean':float(np.mean(arr['gate'][mask]))})
        root.mkdir(parents=True,exist_ok=True);metrics=root/'metrics.csv';write_csv(metrics,rows,('mechanism','series_id','model','seed','horizon','true_label','origins','rmse','gate_mean'))
        prediction_path = root/'predictions.npz'
        with prediction_path.with_name(f'.{prediction_path.name}.tmp').open('wb') as handle:
            np.savez_compressed(handle, **arr)
        prediction_path.with_name(f'.{prediction_path.name}.tmp').replace(prediction_path)
        payload={'status':'complete','model':model_id,'seed':seed,'started_at':started,'finished_at':utc_now(),'training':info,'data_manifest':str(DATA_ROOT/'synthetic'/'data_manifest.json'),'configuration_lock':str(REPRODUCIBILITY/'configuration_lock.json'),'runner_sha256':sha256_path(Path(__file__)),'state_threshold':threshold,'feature_permutation_seed':shuffle_seed,'state_permutation_seed':state_shuffle_seed,'artifacts':{'metrics':artifact_entry(metrics),'prediction_archive':artifact_entry(prediction_path),'checkpoint':artifact_entry(root/'checkpoint.pt') if (root/'checkpoint.pt').exists() else None,'origins':int(len(arr['origin']))}}
    except Exception as exc:
        payload={'status':'failed','model':model_id,'seed':seed,'started_at':started,'finished_at':utc_now(),'error':repr(exc)};write_task_manifest(manifest,payload);raise
    write_task_manifest(manifest,payload);return payload


def run() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('preflight','generate','validation_detector','train'),required=True);args=parser.parse_args()
    if args.stage=='preflight':preflight();return
    settings,protocol=cfg('synthetic'),cfg('protocol')
    if args.stage=='generate':
        coverage=generate()
        if not coverage['passed']:raise SystemExit('coverage_gate_failed')
        return
    if args.stage == 'validation_detector':
        validation_detector_report(settings)
        return
    threshold_payload=json.loads((DATA_ROOT/'synthetic'/'state_threshold.json').read_text()); threshold=threshold_payload if "mode" in threshold_payload else threshold_payload['threshold'];complete=[];fail=[]
    for model in protocol['models']:
        for seed in protocol['seeds']:
            error = None
            for attempt in range(1, 3):
                try:
                    complete.append(task(model,int(seed),settings,protocol,threshold)); error = None; break
                except Exception as exc:
                    error = repr(exc)
                    (RESULTS / f'{model}_seed{seed}' / 'retry.json').parent.mkdir(parents=True, exist_ok=True)
                    atomic_write_json(RESULTS / f'{model}_seed{seed}' / 'retry.json', {'model':model,'seed':seed,'attempt':attempt,'error':error,'updated_at':utc_now()})
            if error is not None: fail.append({'model':model,'seed':seed,'error':error,'attempts':2})
    rows=[]
    for p in RESULTS.glob('*_seed*/metrics.csv'):
        rows.extend(csv.DictReader(p.open()))
    write_csv(RESULTS/'metrics_all.csv',rows,('mechanism','series_id','model','seed','horizon','true_label','origins','rmse','gate_mean'))
    write_csv(RESULTS/'failures.csv',fail,('model','seed','error','attempts'))
    atomic_write_json(RESULTS/'campaign_manifest.json',{'planned':len(protocol['models'])*len(protocol['seeds']),'completed':len(complete),'failures':fail,'created_at':utc_now()})
    print(json.dumps({'completed':len(complete),'failures':fail},indent=2))


if __name__=='__main__':run()
