#!/usr/bin/env python3
"""Draw the hybrid weight curves from results/hybrid.jsonl.

Small multiples, one panel per dataset, one line per dense model. The shaded band
marks the weight range pre-registered as the predicted optimum, so the figure shows
the prediction and the measurement in the same frame.

Panels use independent y-scales: the point is where each curve peaks, not which
dataset scores higher. Absolute levels are on the axes and in docs/results-week2.md.

    python scripts/plot_weight_curves.py --in results/hybrid.jsonl --outdir docs/img
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated with the dataviz palette validator: all checks pass in both modes.
THEME = {
    "light": {"surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e",
              "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
              "band": "#e1e0d9", "series": ["#2a78d6", "#eb6834"]},
    "dark": {"surface": "#1a1a19", "primary": "#ffffff", "secondary": "#c3c2b7",
             "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835",
             "band": "#2c2c2a", "series": ["#3987e5", "#d95926"]},
}
# Colour follows the model, not its rank in a panel.
MODEL_SLOT = {"multilingual-e5-small": 0, "multilingual-e5-large": 1}
PREREGISTERED_BAND = (0.2, 0.4)
DATASET_ORDER = ["AutoRAGRetrieval", "Ko-StrategyQA", "MIRACLRetrieval-ko"]


def load(path: str, normalizer: str):
    runs = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            model = r["model"].split("/")[-1]
            curve = r["curves"][normalizer]
            runs[(r["dataset"], model)] = {
                "w": [e["w_dense"] for e in curve],
                "y": [e["ndcg_at_10"] for e in curve],
                "lo": [e["ci95"][0] for e in curve],
                "hi": [e["ci95"][1] for e in curve],
                "n_queries": r["n_queries"],
                "n_documents": r["n_documents"],
            }
    return runs


def draw(runs, mode: str, out_path: str, normalizer: str):
    t = THEME[mode]
    datasets = [d for d in DATASET_ORDER if any(k[0] == d for k in runs)]
    fig, axes = plt.subplots(1, len(datasets), figsize=(4.7 * len(datasets), 4.5),
                             facecolor=t["surface"])
    if len(datasets) == 1:
        axes = [axes]

    for ax, ds in zip(axes, datasets):
        ax.set_facecolor(t["surface"])
        ax.axvspan(*PREREGISTERED_BAND, color=t["band"], zorder=0, lw=0)
        ax.grid(True, color=t["grid"], lw=0.8, zorder=1)
        ax.set_axisbelow(True)

        for model, slot in MODEL_SLOT.items():
            run = runs.get((ds, model))
            if run is None:
                continue
            colour = t["series"][slot]
            ax.fill_between(run["w"], run["lo"], run["hi"], color=colour,
                            alpha=0.15, lw=0, zorder=2)
            ax.plot(run["w"], run["y"], color=colour, lw=2.0, zorder=3,
                    label=model.replace("multilingual-", ""))
            bi = max(range(len(run["y"])), key=lambda i: run["y"][i])
            ax.plot([run["w"][bi]], [run["y"][bi]], "o", ms=8, color=colour,
                    mec=t["surface"], mew=2, zorder=4)
            peak_w = run["w"][bi]
            dy, va = ((0, 12), "bottom") if slot else ((0, -14), "top")
            ha = "right" if peak_w > 0.82 else "center"
            dx = -6 if ha == "right" else 0
            ax.annotate(f"w={peak_w:.2f}", (peak_w, run["y"][bi]),
                        textcoords="offset points", xytext=(dx, dy[1]), ha=ha, va=va,
                        fontsize=9, color=t["secondary"], zorder=5)

        any_run = next(r for (d, _), r in runs.items() if d == ds)
        ax.set_title(f"{ds}\n{any_run['n_documents']:,} docs · {any_run['n_queries']} queries",
                     fontsize=11, color=t["primary"], pad=10)
        ax.set_xlabel("dense weight  (0 = BM25 only, 1 = dense only)",
                      fontsize=9.5, color=t["secondary"])
        ax.set_xlim(-0.03, 1.05)
        ax.margins(y=0.14)
        ax.tick_params(colors=t["muted"], labelsize=9, length=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(t["axis"])

    axes[0].set_ylabel("nDCG@10", fontsize=9.5, color=t["secondary"])
    fig.suptitle("Hybrid weight curves — the pre-registered optimum (shaded) "
                 "is not where the peak is",
                 fontsize=13, color=t["primary"], y=0.985)
    handles, labels = [], []
    for model, slot in MODEL_SLOT.items():
        if any(k[1] == model for k in runs):
            handles.append(plt.Line2D([], [], color=t["series"][slot], lw=2.0))
            labels.append(model.replace("multilingual-", ""))
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.935),
               ncol=len(handles), frameon=False, fontsize=9.5,
               labelcolor=t["secondary"], handlelength=1.6, columnspacing=2.0)
    fig.text(0.5, 0.055,
             f"Character-bigram BM25 fused with dense scores, {normalizer} normalization per query.",
             ha="center", fontsize=8.5, color=t["muted"])
    fig.text(0.5, 0.020,
             "Bands are 95% bootstrap intervals (10,000 resamples at the query level). "
             "Panels have independent y-scales.",
             ha="center", fontsize=8.5, color=t["muted"])
    fig.tight_layout(rect=(0, 0.085, 1, 0.905))
    fig.savefig(out_path, dpi=200, facecolor=t["surface"])
    plt.close(fig)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="results/hybrid.jsonl")
    ap.add_argument("--outdir", default="docs/img")
    ap.add_argument("--normalizer", default="minmax", choices=["minmax", "zscore"])
    args = ap.parse_args()

    runs = load(args.inp, args.normalizer)
    os.makedirs(args.outdir, exist_ok=True)
    for mode in ("light", "dark"):
        path = os.path.join(args.outdir, f"weight-curves-{mode}.png")
        draw(runs, mode, path, args.normalizer)
        print(f"  wrote {path}  ({os.path.getsize(path)/1000:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
