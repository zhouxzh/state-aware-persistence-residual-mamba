#!/usr/bin/env python
"""Render an evidence-bound V3 manuscript draft from verified local tables."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


STUDY = "sapr_mamba_v3"
ANALYSIS = REPO_ROOT / "docs" / "analysis" / STUDY
RESULTS = REPO_ROOT / "results" / STUDY
MANUSCRIPT = REPO_ROOT / "manuscript" / STUDY
STATE = RESULTS / "pipeline_state.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: str, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "not estimable"


def _analysis_status() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"status": "complete_with_limitations", "limitations": ["pipeline state not found"]}


def build() -> dict:
    MANUSCRIPT.mkdir(parents=True, exist_ok=True)
    state = _analysis_status()
    synthetic_path = ANALYSIS / "synthetic_primary_comparisons.csv"
    real_path = ANALYSIS / "real_primary_comparisons.csv"
    claims = []
    sources = [
        {"source_id": "E001", "path": "configs/sapr_mamba_v3/protocol.lock.json", "verification": "automated_hash_only", "human_verified": False},
        {"source_id": "E002", "path": "data/sapr_mamba_v3/real/source_extensions/v3.1/prepared_manifest.json", "verification": "automated_hash_only", "human_verified": False},
        {"source_id": "E003", "path": "docs/analysis/sapr_mamba_v3/real_verification_manifest.json", "verification": "automated_hash_only", "human_verified": False},
        {"source_id": "E004", "path": "https://arxiv.org/abs/2609.00065v2", "verification": "metadata_fetched", "human_verified": False},
    ]
    protocol_path = REPO_ROOT / "configs" / STUDY / "protocol.lock.json"
    claims.extend([
        {"claim_id": "C001", "artifact": str(protocol_path.relative_to(REPO_ROOT)), "filter": "protocol boundary", "sha256": sha256_path(protocol_path)},
        {"claim_id": "C002", "artifact": str(protocol_path.relative_to(REPO_ROOT)), "filter": "human declarations required", "sha256": sha256_path(protocol_path)},
    ])
    external_claim_path = ANALYSIS / "external_holdout_primary_comparisons.csv"
    if external_claim_path.is_file():
        claims.append({"claim_id": "C_EXT_HOLDOUT", "artifact": str(external_claim_path.relative_to(REPO_ROOT)), "filter": "all rows", "sha256": sha256_path(external_claim_path)})
    lines = [
        "# SAPR-Mamba V3: State-Aware Persistence-Residual Forecasting",
        "",
        "> Automatically generated evidence-bound draft. It is not submission-ready until all required sections, citations, declarations, and author approvals are present.",
        "",
        "## Abstract",
        "",
        "[Generated only after V3 analysis and external validation complete.]",
        "",
        "## Methods",
        "",
        "The V3 study follows the frozen protocol in `configs/sapr_mamba_v3/protocol.lock.json`. V2 is retained as development evidence and is not pooled with V3. [claim:C001] [evidence:E001]",
        "",
        "## Results",
        "",
    ]
    if synthetic_path.is_file():
        lines.extend(["### Synthetic confirmation", "", "| Comparison | Horizon | Independent sequences | Estimate | 95% CI | Holm p |", "|---|---:|---:|---:|---:|---:|"])
        for index, row in enumerate(read_csv(synthetic_path), start=1):
            claim_id = f"C_SYN_{index:03d}"
            artifact = str(synthetic_path.relative_to(REPO_ROOT))
            filters = f"comparison={row['comparison']}; horizon={row['horizon']}"
            claims.append({"claim_id": claim_id, "artifact": artifact, "filter": filters, "sha256": sha256_path(synthetic_path)})
            lines.append(
                f"| {row['comparison']} | {row['horizon']} | {row['n']} | {_num(row['estimate'])} | "
                f"[{_num(row['ci_low'])}, {_num(row['ci_high'])}] | {_num(row.get('p_holm', row.get('p_two_sided', '')))} |"
            )
        lines.extend(["", f"Evidence: `{artifact}` (SHA-256 `{sha256_path(synthetic_path)}`).", ""])
    else:
        lines.extend(["Synthetic primary results are not yet available.", ""])
    if real_path.is_file():
        lines.extend(["### Source-stratified real-panel results", "", "| Source | Comparison | Horizon | n sequences | Estimate | 95% CI | Holm p | Status |", "|---|---|---:|---:|---:|---:|---:|---|"])
        for index, row in enumerate(read_csv(real_path), start=1):
            claim_id = f"C_REAL_{index:03d}"
            artifact = str(real_path.relative_to(REPO_ROOT))
            filters = f"source={row['source']}; comparison={row['comparison']}; horizon={row['horizon']}"
            claims.append({"claim_id": claim_id, "artifact": artifact, "filter": filters, "sha256": sha256_path(real_path)})
            lines.append(
                f"| {row['source']} | {row['comparison']} | {row['horizon']} | {row['n']} | {_num(row['estimate'])} | "
                f"[{_num(row['ci_low'])}, {_num(row['ci_high'])}] | {_num(row.get('p_holm', ''))} | {row['evidence_status']} |"
            )
        lines.extend(["", f"Evidence: `{artifact}` (SHA-256 `{sha256_path(real_path)}`).", ""])
    else:
        lines.extend(["Real-panel analysis is not yet available; no real-data claims are emitted.", ""])
    external_path = ANALYSIS / "external_holdout_primary_comparisons.csv"
    if external_path.is_file():
        lines.extend([
            "### External holdout paired comparisons", "",
            "The declared external holdout clusters are reported separately from the base source pool; no universal cross-domain claim is inferred. [claim:C_EXT_HOLDOUT] [evidence:E002]",
            "",
            "| Source cluster | Comparison | Horizon | n | Estimate | 95% CI | Holm p | Status |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ])
        for row in read_csv(external_path):
            lines.append(
                f"| {row['source']} | {row['comparison']} | {row['horizon']} | {row['n']} | {_num(row['estimate'])} | "
                f"[{_num(row['ci_low'])}, {_num(row['ci_high'])}] | {_num(row.get('p_holm', ''))} | {row['evidence_status']} |"
            )
        lines.extend(["", f"Evidence: `{external_path.relative_to(REPO_ROOT)}` (SHA-256 `{sha256_path(external_path)}`).", ""])
    extension_manifest = RESULTS.parent.parent / "data" / STUDY / "real" / "source_extensions" / "v3.1" / "prepared_manifest.json"
    if extension_manifest.is_file():
        extension = read_json(extension_manifest)
        lines.extend([
            "### External source and state coverage", "",
            "| Panel | Source cluster | Series | Stable test series | Change test series | External holdout | Stable endpoint |",
            "|---|---|---:|---:|---:|---|---|",
        ])
        for index, row in enumerate(extension.get("sources", []), start=1):
            claim_id = f"C_EXT_{index:03d}"
            artifact = str(extension_manifest.relative_to(REPO_ROOT))
            claims.append({"claim_id": claim_id, "artifact": artifact, "filter": f"panel={row.get('panel_id')}", "sha256": sha256_path(extension_manifest)})
            lines.append(
                f"| {row.get('panel_id', '')} | {row.get('source_cluster', '')} | {row.get('series_count', '')} | "
                f"{row.get('stable_test_series', '')} | {row.get('change_test_series', '')} | "
                f"{str(bool(row.get('external_holdout', False))).lower()} | "
                f"{str(bool(row.get('stable_coverage_eligible', False))).lower()} |"
            )
        lines.extend(["", f"Evidence: `{artifact}` (SHA-256 `{sha256_path(extension_manifest)}`).", ""])
    verification = read_json(ANALYSIS / "real_verification_manifest.json")
    if verification:
        lines.extend([
            "### Independent recomputation", "",
            f"Real-task metric recomputation status: **{verification.get('status', 'unknown')}** "
            f"({verification.get('tasks', 0)} tasks; {len(verification.get('metric_recompute_failures', []))} failures).",
            f"Evidence: `docs/analysis/{STUDY}/real_verification_manifest.json`.", "",
        ])
    lines.extend(["## Limitations", ""])
    limitations = state.get("limitations", [])
    if limitations:
        lines.extend(f"- {item}" for item in limitations)
    else:
        lines.append("No automated limitations have been recorded; complete analysis before interpreting this draft.")
    lines.extend([
        "- V2 is a development baseline and is not pooled into V3 confirmation estimates.",
        "- State coverage, independent source-cluster count, and external-holdout status must be reported from V3 manifests.",
        "",
        "## Declarations (unresolved placeholders)",
        "",
        "Authorship, funding, conflicts, ethics/data-use declarations, and AI-use disclosure are not inferred by automation and must not be fabricated. [claim:C002] [evidence:E001]",
        "",
        "## Software and Procedural Guidance",
        "",
        "Evidence binding, limitation disclosure, and manuscript audit structure were informed by Scientific Agent Skills: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents* (arXiv:2609.00065v2; doi:10.48550/arXiv.2609.00065).",
    ])
    manuscript_path = MANUSCRIPT / "manuscript.md"
    manuscript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    claims_path = MANUSCRIPT / "claim_evidence_map.csv"
    with claims_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("claim_id", "artifact", "filter", "sha256"))
        writer.writeheader()
        writer.writerows(claims)
    source_path = MANUSCRIPT / "source_manifest.json"
    for source in sources:
        local_path = REPO_ROOT / source["path"] if not str(source["path"]).startswith("http") else None
        if local_path is not None and local_path.is_file():
            source["sha256"] = sha256_path(local_path)
        source["verification_note"] = "Human verifier must open source and record locator before submission."
    atomic_write_json(source_path, {
        "study": STUDY,
        "generated_at": utc_now(),
        "status": "unverified",
        "human_verification_required": True,
        "sources": sources,
    })
    manifest = {
        "study": STUDY,
        "generated_at": utc_now(),
        "status": "draft",
        "study_design": "forecasting benchmark with synthetic confirmation and public time-series panels",
        "pipeline_status": state.get("status", "unknown"),
        "numeric_claim_count": len(claims),
        "manuscript": {"path": str(manuscript_path.relative_to(REPO_ROOT)), "sha256": sha256_path(manuscript_path)},
        "claim_evidence_map": {"path": str(claims_path.relative_to(REPO_ROOT)), "sha256": sha256_path(claims_path)},
        "source_manifest": {"path": str(source_path.relative_to(REPO_ROOT)), "sha256": sha256_path(source_path)},
        "confidentiality_review": {
            "completed": False,
            "policy_checked": False,
            "scope": "local public and synthetic evidence only",
            "reason": "accountable human review is required before external disclosure",
        },
        "human_declarations_required": True,
        "submission_ready": False,
    }
    atomic_write_json(MANUSCRIPT / "manuscript_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def main() -> None:
    build()


if __name__ == "__main__":
    main()
