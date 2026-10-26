#!/usr/bin/env python
"""Value-vs-time review plots for every canonical_v2 test series.

Each PNG shows the observed series and the seed-averaged forecasts at the
protocol evaluation origin, plus per-origin path RMSE for the main models.
The HTML index is for one-by-one manual inspection. This script does not
pool other study versions.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data" / "sapr_mamba_canonical_v2" / "synthetic"
RESULT = REPO_ROOT / "results" / "sapr_mamba_canonical_v2" / "synthetic"
OUT = REPO_ROOT / "docs" / "figures" / "sapr_canonical_v2" / "review"
SEEDS = (20262201, 20262202, 20262203, 20262204, 20262205)
MODELS = ("M0", "M1", "DLinear", "M2", "M3", "M3-constant-gate")
MODEL_STYLE = {
    "M0": {"color": "#7f7f7f", "ls": "--", "lw": 1.4, "label": "M0 persistence"},
    "M1": {"color": "#4e79a7", "ls": "-", "lw": 1.3, "label": "M1 linear residual"},
    "DLinear": {"color": "#f28e2b", "ls": "-", "lw": 1.3, "label": "DLinear"},
    "M2": {"color": "#e15759", "ls": "-", "lw": 1.6, "label": "M2 ungated residual"},
    "M3": {"color": "#59a14f", "ls": "-", "lw": 1.6, "label": "M3 state gate"},
    "M3-constant-gate": {"color": "#b07aa1", "ls": ":", "lw": 1.5, "label": "M3c constant gate"},
}
EVAL_LABEL = {
    "stable": "stable",
    "visible_level_shift": "visible_change",
    "future_jump": "unseen_change",
    "continuing_trend": "visible_change",
    "trend_break": "visible_change",
    "stable_season": "stable",
    "seasonal_change": "visible_change",
    "variance_shift": "visible_change",
    "random_walk": "stable",
    "gradual_drift": "visible_change",
    "weak_change": "visible_change",
}
MECHANISM_TITLE = {
    "stable": "T0 local stable",
    "visible_level_shift": "T1 visible level shift",
    "future_jump": "T2 unseen jump",
    "continuing_trend": "T3 continuing trend",
    "trend_break": "T4 visible trend break",
    "stable_season": "T5 stable season",
    "seasonal_change": "T6 seasonal change",
    "variance_shift": "T7 variance shift",
    "random_walk": "T8 random walk",
    "gradual_drift": "diag gradual drift",
    "weak_change": "diag weak change",
}
MECHANISM_TITLE_ZH = {
    "stable": "T0 局部稳定",
    "visible_level_shift": "T1 已见水平跳变",
    "future_jump": "T2 未见跳变",
    "continuing_trend": "T3 持续趋势",
    "trend_break": "T4 已见趋势折点",
    "stable_season": "T5 稳定季节",
    "seasonal_change": "T6 季节形态变化",
    "variance_shift": "T7 仅方差改变",
    "random_walk": "T8 近随机游走",
    "gradual_drift": "诊断 渐进漂移",
    "weak_change": "诊断 弱变化",
}
HISTORY = 384
HORIZON = 96
RMSE_H = 24


def load_mean_predictions() -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    meta = None
    for model in MODELS:
        acc = None
        for seed in SEEDS:
            path = RESULT / f"{model}_seed{seed}" / "predictions.npz"
            with np.load(path, allow_pickle=True) as payload:
                pred = np.asarray(payload["prediction"], dtype=np.float32)
                if acc is None:
                    acc = pred
                    if meta is None:
                        meta = {
                            "series_index": np.asarray(payload["series_index"], dtype=np.int64),
                            "origin": np.asarray(payload["origin"], dtype=np.int64),
                            "true_label": np.asarray(payload["true_label"]).astype(str),
                            "target": np.asarray(payload["target"], dtype=np.float32),
                            "state": np.asarray(payload["state"]),
                        }
                else:
                    acc += pred
        arrays[model] = acc / float(len(SEEDS))
    assert meta is not None
    arrays.update(meta)
    return arrays


def choose_eval_row(rows: list[int], origin: np.ndarray, labels: np.ndarray, mechanism: str, change_point: int) -> int:
    wanted = EVAL_LABEL[mechanism]
    matched = [row for row in rows if labels[row] == wanted]
    if not matched:
        matched = list(rows)
    if change_point >= 0:
        delayed = [row for row in matched if int(origin[row]) >= change_point + 12]
        if delayed:
            return delayed[0]
    mid = min(matched, key=lambda row: abs(int(origin[row]) - 1152))
    return mid


def path_rmse(pred: np.ndarray, target: np.ndarray, horizon: int) -> float:
    err = pred[:horizon] - target[:horizon]
    return float(np.sqrt(np.mean(np.square(err))))


def draw_series(
    series_index: int,
    values: np.ndarray,
    record: dict,
    rows: list[int],
    packed: dict[str, np.ndarray],
    output: Path,
) -> dict:
    origin = packed["origin"]
    labels = packed["true_label"]
    target = packed["target"]
    eval_row = choose_eval_row(rows, origin, labels, record["mechanism"], int(record["change_point"]))
    t0 = int(origin[eval_row])
    series = values[series_index]
    time = np.arange(series.shape[0])
    title = MECHANISM_TITLE.get(record["mechanism"], record["mechanism"])
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(11.2, 9.2),
        gridspec_kw={"height_ratios": [1.35, 1.15, 0.9]},
        constrained_layout=True,
    )
    ax_full, ax_zoom, ax_rmse = axes
    ax_full.plot(time, series, color="black", lw=0.85, label="observed")
    cp = int(record["change_point"])
    if cp >= 0:
        ax_full.axvline(cp, color="#d62728", ls="--", lw=1.0, label=f"change point t={cp}")
    ax_full.axvline(t0, color="#1f77b4", ls=":", lw=1.1, label=f"eval origin t={t0}")
    ax_full.axvspan(t0 - HISTORY, t0, color="#1f77b4", alpha=0.08, label="input window")
    ax_full.axvspan(t0, t0 + HORIZON, color="#ff7f0e", alpha=0.10, label="forecast window")
    ax_full.set_xlim(0, series.shape[0] - 1)
    ax_full.set_ylabel("value")
    ax_full.set_title(f"{record['series_id']}  |  {title}  |  label {labels[eval_row]}")
    ax_full.legend(loc="upper left", ncol=3, fontsize=8, frameon=False)
    ax_full.grid(True, alpha=0.25)

    left = max(0, t0 - HISTORY)
    right = min(series.shape[0], t0 + HORIZON)
    ax_zoom.plot(np.arange(left, t0 + 1), series[left : t0 + 1], color="black", lw=1.1, label="history/origin")
    ax_zoom.plot(np.arange(t0, right), series[t0:right], color="black", lw=1.6, label="true future")
    ax_zoom.axvline(t0, color="#1f77b4", ls=":", lw=1.0)
    if cp >= left and cp < right:
        ax_zoom.axvline(cp, color="#d62728", ls="--", lw=1.0)
    for model in MODELS:
        style = MODEL_STYLE[model]
        pred = packed[model][eval_row]
        ax_zoom.plot(np.arange(t0, t0 + HORIZON), pred, color=style["color"], ls=style["ls"], lw=style["lw"], label=style["label"])
    ax_zoom.set_xlim(left, right - 1)
    ax_zoom.set_ylabel("value")
    ax_zoom.set_title(f"H=96 forecasts at origin {t0} (mean of 5 seeds)")
    ax_zoom.legend(loc="upper left", ncol=4, fontsize=8, frameon=False)
    ax_zoom.grid(True, alpha=0.25)

    xs = [int(origin[row]) for row in rows]
    for model in MODELS:
        style = MODEL_STYLE[model]
        ys = [path_rmse(packed[model][row], target[row], RMSE_H) for row in rows]
        ax_rmse.plot(xs, ys, color=style["color"], ls=style["ls"], lw=1.3, marker="o", ms=3.2, label=style["label"])
    ax_rmse.axvline(t0, color="#1f77b4", ls=":", lw=1.0)
    if cp >= 0:
        ax_rmse.axvline(cp, color="#d62728", ls="--", lw=1.0)
    ax_rmse.set_xlabel("time (origin)")
    ax_rmse.set_ylabel(f"path RMSE (H={RMSE_H})")
    ax_rmse.set_title("path RMSE at all 17 test origins")
    ax_rmse.legend(loc="upper left", ncol=3, fontsize=8, frameon=False)
    ax_rmse.grid(True, alpha=0.25)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=110, facecolor="white")
    plt.close(fig)
    return {
        "series_id": record["series_id"],
        "mechanism": record["mechanism"],
        "title": title,
        "title_zh": MECHANISM_TITLE_ZH.get(record["mechanism"], record["mechanism"]),
        "change_point": cp,
        "eval_origin": t0,
        "eval_label": str(labels[eval_row]),
        "file": str(output.relative_to(OUT)).replace("\\", "/"),
    }


def write_index(items: list[dict]) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["mechanism"]].append(item)
    files = [item["file"] for item in items]
    payload = {"count": len(items), "items": items}
    (OUT / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    mechanism_links = []
    for mechanism, rows in grouped.items():
        title = MECHANISM_TITLE_ZH.get(mechanism, mechanism)
        mechanism_links.append(f'<button data-mechanism="{mechanism}">{title} ({len(rows)})</button>')
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<title>canonical_v2 序列人工校验</title>
<style>
body {{ font-family: sans-serif; margin: 16px; background: #f7f7f7; }}
h1 {{ font-size: 20px; }}
#nav button {{ margin: 0 6px 8px 0; padding: 6px 10px; }}
#nav button.active {{ background: #1f77b4; color: white; border-color: #1f77b4; }}
#meta {{ margin: 8px 0 12px; color: #333; }}
img {{ width: min(1120px, 100%); background: white; border: 1px solid #ddd; }}
.controls button {{ font-size: 16px; padding: 8px 14px; margin-right: 8px; }}
</style>
</head>
<body>
<h1>canonical_v2 数值 vs 时间（{len(items)} 条测试序列）</h1>
<p>方向键或按钮逐张查看。上图：整段序列；中图：评价原点预测；下图：全部测试原点的 H=24 路径 RMSE。</p>
<div id="nav">{"".join(mechanism_links)}<button data-mechanism="all">全部</button></div>
<div class="controls">
<button id="prev">上一张</button>
<button id="next">下一张</button>
<span id="pos"></span>
</div>
<div id="meta"></div>
<img id="plot" alt="series review plot"/>
<script>
const items = {json.dumps(items, ensure_ascii=False)};
let filtered = items.slice();
let idx = 0;
function show() {{
  if (!filtered.length) return;
  idx = (idx + filtered.length) % filtered.length;
  const it = filtered[idx];
  document.getElementById("plot").src = it.file;
  document.getElementById("pos").textContent = (idx+1) + " / " + filtered.length;
  document.getElementById("meta").textContent = it.series_id + " | " + (it.title_zh || it.title) + " | 变点 " + it.change_point + " | 评价原点 " + it.eval_origin + " | " + it.eval_label;
}}
function setMech(m) {{
  filtered = m === "all" ? items.slice() : items.filter(x => x.mechanism === m);
  idx = 0;
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("active", b.dataset.mechanism === m));
  show();
}}
document.getElementById("prev").onclick = () => {{ idx -= 1; show(); }};
document.getElementById("next").onclick = () => {{ idx += 1; show(); }};
document.querySelectorAll("#nav button").forEach(b => b.onclick = () => setMech(b.dataset.mechanism));
document.addEventListener("keydown", e => {{
  if (e.key === "ArrowRight") {{ idx += 1; show(); }}
  if (e.key === "ArrowLeft") {{ idx -= 1; show(); }}
}});
setMech("all");
</script>
</body>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    _ = files


def main() -> None:
    roster = json.loads((DATA / "test_roster.json").read_text(encoding="utf-8"))["records"]
    with np.load(DATA / "test.npz") as payload:
        values = np.asarray(payload["values"])
    packed = load_mean_predictions()
    rows_by_series: dict[int, list[int]] = defaultdict(list)
    for row, series_index in enumerate(packed["series_index"].tolist()):
        rows_by_series[int(series_index)].append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    for series_index, record in enumerate(roster):
        mechanism = record["mechanism"]
        path = OUT / mechanism / f"{record['series_id']}.png"
        item = draw_series(series_index, values, record, rows_by_series[series_index], packed, path)
        items.append(item)
        if (series_index + 1) % 50 == 0:
            print(f"wrote {series_index + 1}/{len(roster)}", flush=True)
    write_index(items)
    print(json.dumps({"status": "complete", "count": len(items), "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
