#!/usr/bin/env python
"""Run the final Mamba candidates under the audited financial reference protocol.

The legacy test targets have already been observed for the frozen baselines.  This
entry point therefore labels the output as a retrospective, protocol-matched result
and never writes into the legacy ``financial_confirmatory`` result tree.
"""

from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.common import atomic_write_json, sha256_path
from scripts.evaluation.run_evaluation import evaluate_horizons, load_dataset_manifest
from scripts.audit_legacy_baselines import DEFAULT_OUTPUT as AUDIT_OUTPUT
from scripts.audit_legacy_baselines import audit
from scripts.registry import public_name, runtime_model_name


PUBLICATION_CONFIG = REPO_ROOT / "configs" / "financial_reference_evaluation_v1.json"
OUTPUT_ROOT = REPO_ROOT / "results" / "financial_reference_evaluation_v1"


def load_config(path: Path = PUBLICATION_CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def selected(values: list[str], available: list[str], description: str) -> list[str]:
    if values == ["ALL"]:
        return available
    invalid = sorted(set(values) - set(available))
    if invalid:
        raise ValueError(f"Unknown {description}: {invalid}; available={available}")
    return values


def require_cuda() -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for publication candidate training")


def load_v3_params(config: dict, task: str) -> tuple[dict, Path]:
    path = REPO_ROOT / config["candidate_parameter_selection_snapshot"] / task / "mamba_best_params.json"
    if not path.is_file():
        raise RuntimeError(f"Missing V3 selection snapshot: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dataset") != task:
        raise RuntimeError(f"V3 selection dataset mismatch: {path}")
    if not payload.get("search_space_version", "").startswith("pms_v3"):
        raise RuntimeError(f"V3 selection search-space mismatch: {path}")
    # The frozen selection snapshot predates the canonical release names.
    model = payload.get("models", {}).get("PMS_Mamba-PD", {})
    if model.get("selection_eval_flag") != "val" or not model.get("params"):
        raise RuntimeError(f"V3 selection is incomplete: {path}")
    return dict(model["params"]), path


def runner_args(args: argparse.Namespace, output_root: Path, seed: int) -> Namespace:
    configured_checkpoint_root = getattr(args, "checkpoint_root", None)
    checkpoint_root = Path(configured_checkpoint_root or output_root / "checkpoints").resolve()
    return Namespace(
        # ``format_setting`` embeds phase and stage tags twice. Keep publication
        # path components below the filesystem filename limit; full provenance is
        # persisted in ``meta.json`` and ``final_runs.json``.
        phase="pub",
        seed=int(seed),
        cpu=False,
        require_cuda=True,
        gpu=int(args.gpu),
        train_epochs=int(args.train_epochs),
        patience=int(args.patience),
        num_workers=int(args.num_workers),
        tensorboard_dir=str(output_root / "tensorboard"),
        checkpoints=str(checkpoint_root),
        results_root=str(output_root / "runs"),
        no_save_final_artifacts=False,
        discard_final_checkpoints=not bool(getattr(args, "retain_final_checkpoints", False)),
    )


def compact_stage_tag(candidate_id: str, seed: int, smoke: bool = False) -> str:
    """Return a deterministic tag that remains safe inside a setting directory."""
    short_candidate = {
        "RegimeGatedMamba": "rgm",
        "MultiScalePatchMamba": "msp",
    }.get(candidate_id, candidate_id.lower())
    return f"{'smk' if smoke else 'pub'}_{short_candidate}_s{seed}"


def complete_run(
    record: dict,
    horizons: list[int],
    output_root: Path,
    checkpoint_root: Path | None = None,
) -> bool:
    if record.get("status") != "complete":
        return False
    settings = record.get("settings", {})
    for horizon in horizons:
        setting = settings.get(str(horizon), settings.get(horizon))
        if not setting or not (output_root / "runs" / setting / "meta.json").is_file():
            return False
        if checkpoint_root is not None and not (
            checkpoint_root / setting / "checkpoint.pth"
        ).is_file():
            return False
    return True


def persist_publication_metadata(
    output_root: Path,
    settings: dict,
    candidate_id: str,
    candidate: dict,
    selection_path: Path,
    parameter_sha256: str,
) -> None:
    for setting in settings.values():
        meta_path = output_root / "runs" / setting / "meta.json"
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata.update(
            publication_protocol_version="financial_reference_evaluation_v1",
            publication_model_id=candidate_id,
            source_model_id=candidate["source_model_id"],
            publication_public_name=public_name(candidate_id),
            publication_role=candidate["role"],
            runtime_model_label=runtime_model_name(candidate_id),
            selection_source=str(selection_path.relative_to(REPO_ROOT)),
            selection_source_sha256=parameter_sha256,
            evaluation_status="retrospective_protocol_matched",
        )
        atomic_write_json(meta_path, metadata)


def run(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    base = config["base_protocol"]
    manifest_path = REPO_ROOT / base["training_manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = selected(args.tasks, sorted(manifest), "task IDs")
    candidate_ids = selected(args.candidates, list(config["candidates"]), "candidate IDs")
    horizons = [int(value) for value in base["horizons"]]
    seeds = selected([str(value) for value in args.seeds], [str(value) for value in base["seeds"]], "seeds")
    seeds = [int(value) for value in seeds]

    report = audit(
        REPO_ROOT / base["path"], manifest_path, REPO_ROOT / base["legacy_final_summary"],
        REPO_ROOT / base["legacy_run_root"],
    )
    if not report["compatible"]:
        raise RuntimeError("Legacy baseline audit failed; publication candidates cannot be compared to it")
    atomic_write_json(AUDIT_OUTPUT, report)
    if args.stage == "preflight":
        require_cuda()
        return {"status": "preflight_passed", "audit": "passed"}

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "final_runs.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {"runs": {}}
    if summary.get("runs") and summary.get("protocol_version") != config["protocol_version"]:
        raise RuntimeError("Existing candidate summary belongs to another publication protocol")
    summary.update(
        protocol_version=config["protocol_version"],
        base_protocol_version=base["protocol_version"],
        base_protocol_sha256=base["protocol_sha256"],
        evaluation_status="retrospective_protocol_matched",
        horizons=horizons,
        seeds=seeds,
        candidates=candidate_ids,
    )

    if args.stage == "dry-run":
        planned = len(tasks) * len(candidate_ids) * len(seeds) * len(horizons)
        return {"status": "dry_run", "planned_horizon_runs": planned, "audit": "passed"}
    if args.stage == "final" and not args.unlock_retrospective_test:
        raise RuntimeError("Final candidate evaluation requires --unlock-retrospective-test")
    require_cuda()

    if args.stage == "smoke":
        tasks, candidate_ids, seeds, horizons = tasks[:1], candidate_ids[:1], seeds[:1], horizons[:1]
    max_runs = int(args.max_runs)
    completed_now = 0
    for task in tasks:
        dataset_cfg = load_dataset_manifest(manifest_path, task, REPO_ROOT)
        for candidate_id in candidate_ids:
            candidate = config["candidates"][candidate_id]
            selected_params, selection_path = load_v3_params(config, task)
            params = dict(selected_params)
            params.update(candidate["parameter_overrides"])
            params.update(loss="MSE", horizon_weighting="balanced")
            for seed in seeds:
                key = f"{task}|{candidate_id}|{seed}"
                checkpoint_root = None
                if getattr(args, "retain_final_checkpoints", False):
                    checkpoint_root = Path(
                        getattr(args, "checkpoint_root", None) or output_root / "checkpoints"
                    ).resolve()
                if complete_run(
                    summary["runs"].get(key, {}), horizons, output_root, checkpoint_root
                ):
                    print(f"skip complete {key}", flush=True)
                    continue
                if max_runs and completed_now >= max_runs:
                    atomic_write_json(summary_path, summary)
                    return {"status": "partial", "completed_horizon_runs": completed_now, "audit": "passed"}
                if args.stage == "smoke":
                    # Smoke output is deliberately not retained and never joins publication tables.
                    cli = runner_args(args, output_root, seed)
                    stage_tag = compact_stage_tag(candidate_id, seed, smoke=True)
                    evaluate_horizons(cli, dataset_cfg, runtime_model_name(candidate_id), params, horizons,
                                      stage_tag, save_artifacts=False,
                                      eval_flag="val")
                    completed_now += len(horizons)
                    continue
                cli = runner_args(args, output_root, seed)
                stage_tag = compact_stage_tag(candidate_id, seed)
                metrics, aggregate, settings = evaluate_horizons(
                    cli, dataset_cfg, runtime_model_name(candidate_id), params, horizons,
                    stage_tag, save_artifacts=True,
                    eval_flag="test",
                )
                persist_publication_metadata(
                    output_root, settings, candidate_id, candidate, selection_path, sha256_path(selection_path)
                )
                summary["runs"][key] = {
                    "status": "complete",
                    "dataset": task,
                    "model_id": candidate_id,
                    "source_model_id": candidate["source_model_id"],
                    "public_name": public_name(candidate_id),
                    "runtime_model": runtime_model_name(candidate_id),
                    "seed": seed,
                    "params": params,
                    "per_horizon_metrics": metrics,
                    "aggregate": aggregate,
                    "settings": settings,
                }
                atomic_write_json(summary_path, summary)
                completed_now += len(horizons)
    if args.stage == "smoke":
        return {"status": "smoke_passed", "completed_horizon_runs": completed_now, "audit": "passed"}
    return {"status": "complete", "completed_horizon_runs": completed_now, "audit": "passed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["preflight", "dry-run", "smoke", "final"], required=True)
    parser.add_argument("--config", type=Path, default=PUBLICATION_CONFIG)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=None,
        help="Checkpoint root. Defaults to <output-root>/checkpoints.",
    )
    parser.add_argument("--tasks", nargs="+", default=["ALL"])
    parser.add_argument("--candidates", nargs="+", default=["ALL"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[2023, 2024, 2025, 2026, 2027])
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--max-runs", type=int, default=0)
    parser.add_argument("--unlock-retrospective-test", action="store_true")
    parser.add_argument(
        "--retain-final-checkpoints",
        action="store_true",
        help="Keep final checkpoint.pth files for later checkpoint-only replay.",
    )
    return parser.parse_args()


def main() -> None:
    outcome = run(parse_args())
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Publication candidate run blocked: {exc}") from None
