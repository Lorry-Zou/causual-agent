"""Visualization: coefficient plots, DiD plots, balance plots, publication-quality styling."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils import logger, configure_matplotlib_font

configure_matplotlib_font()
sns.set_style("whitegrid")


def setup_dir(output_dir: str) -> Path:
    p = Path(output_dir) / "graphs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_fig(fig: plt.Figure, path: str, dpi: int = 150) -> str:
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    logger().debug("图表: %s", path)
    return path


def coefficient_forest(coefs: dict[str, float], ci_lower: dict[str, float],
                       ci_upper: dict[str, float], pvalues: dict[str, float],
                       title: str = "Coefficient Estimates", output_path: str = "") -> str:
    """Forest plot of coefficients with CIs."""
    names = list(coefs.keys())
    vals = [coefs[n] for n in names]
    ci_l = [ci_lower.get(n, np.nan) for n in names]
    ci_u = [ci_upper.get(n, np.nan) for n in names]
    pv = [pvalues.get(n, 1.0) for n in names]
    fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 0.4)))
    colors = ["#2ECC71" if p < 0.05 else "#E74C3C" if p < 0.01 else "#95A5A6" for p in pv]
    for i in range(len(names)):
        ax.errorbar(vals[i], i, xerr=[[vals[i] - ci_l[i]] if not np.isnan(ci_l[i]) else [0],
                                       [ci_u[i] - vals[i]] if not np.isnan(ci_u[i]) else [0]],
                    fmt="o", capsize=3, ecolor=colors[i], color="#34495E")
        ax.scatter([vals[i]], [i], s=60, color=colors[i], zorder=5)
    ax.axvline(x=0, color="red", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([f"{n} (p={p:.3f})" for n, p in zip(names, pv)], fontsize=9)
    ax.set_xlabel("Coefficient"); ax.set_title(title); ax.invert_yaxis()
    plt.tight_layout()
    return save_fig(fig, output_path) if output_path else ""


def event_study(times: list[int], coefs: list[float], ses: list[float],
                title: str = "Event Study", output_path: str = "") -> str:
    """Event study plot with confidence bands."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ci_l = [c - 1.96 * s for c, s in zip(coefs, ses)]
    ci_u = [c + 1.96 * s for c, s in zip(coefs, ses)]
    colors = ["#E74C3C" if t < 0 else "#3498DB" for t in times]
    for i, t in enumerate(times):
        ax.errorbar(t, coefs[i], yerr=[[coefs[i] - ci_l[i]], [ci_u[i] - coefs[i]]],
                    fmt="o", capsize=3, color=colors[i], markersize=7)
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax.axvline(x=-0.5, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Periods Relative to Treatment"); ax.set_title(title)
    plt.tight_layout()
    return save_fig(fig, output_path) if output_path else ""


def balance_love(smd_before: dict[str, float], smd_after: dict[str, float],
                 output_path: str = "") -> str:
    """Love plot of standardized mean differences before/after matching."""
    common = sorted(set(smd_before) & set(smd_after), key=lambda c: smd_before.get(c, 0), reverse=True)
    if not common:
        return ""
    fig, ax = plt.subplots(figsize=(8, max(4, len(common) * 0.35)))
    before_v = [smd_before[c] for c in common]
    after_v = [smd_after[c] for c in common]
    for i, (b, a) in enumerate(zip(before_v, after_v)):
        ax.plot([b, a], [i, i], color="gray", linewidth=0.8, alpha=0.5)
    ax.scatter(before_v, range(len(common)), marker="o", s=60, label="Before", color="#E74C3C", zorder=3)
    ax.scatter(after_v, range(len(common)), marker="s", s=60, label="After", color="#2ECC71", zorder=3)
    ax.axvline(x=0.1, color="orange", linestyle="--", linewidth=0.8, label="SMD=0.1")
    ax.set_yticks(range(len(common))); ax.set_yticklabels(common, fontsize=9)
    ax.set_xlabel("SMD"); ax.set_title("Balance Diagnostics (Love Plot)")
    ax.legend(fontsize=9); ax.invert_yaxis()
    plt.tight_layout()
    return save_fig(fig, output_path)
