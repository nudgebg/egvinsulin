"""Validation figures.

Each function returns a matplotlib Figure. Caller is responsible for closing it
(plt.close(fig)) after saving or embedding.
"""
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for report generation

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import squarify

from babelbetes.src import cdf as cdf_module
from babelbetes.src import drawing

# Consistent colour palette keyed by study name (falls back to tab10 for unknown studies)
_STUDY_COLORS: dict[str, str] = {}
_CMAP = plt.cm.get_cmap("tab10")


def _study_color(study: str) -> str:
    if study not in _STUDY_COLORS:
        _STUDY_COLORS[study] = _CMAP(len(_STUDY_COLORS) % 10)
    return _STUDY_COLORS[study]


def _fig(w=10, h=4):
    return plt.subplots(figsize=(w, h))


# ── 1. Subjects per study ──────────────────────────────────────────────────────

def plot_subjects_per_study(stats_df: pd.DataFrame) -> plt.Figure:
    """Bar chart: number of patients per study (from patient_count metric)."""
    data = (stats_df[stats_df["metric"] == "patient_count"]
            .groupby("study")["value"].max()
            .sort_values(ascending=False))
    fig, ax = _fig(10, 4)
    colors = [_study_color(s) for s in data.index]
    ax.bar(data.index, data.values, color=colors)
    ax.set_title("Patients per Study")
    ax.set_ylabel("# Patients")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return fig


# ── 2. Patient-days per study split by data type ───────────────────────────────

def plot_days_per_study(stats_df: pd.DataFrame) -> plt.Figure:
    """Grouped bar chart: patient-days per study, split by data type."""
    data = (stats_df[stats_df["metric"] == "patient_days"]
            .pivot_table(index="study", columns="data_type", values="value", aggfunc="sum")
            .fillna(0))
    if data.empty:
        fig, ax = _fig(); ax.set_title("Patient-days (no data)"); return fig

    n_studies   = len(data)
    n_types     = len(data.columns)
    width       = 0.8 / n_types
    x           = np.arange(n_studies)

    fig, ax = _fig(12, 4)
    for i, col in enumerate(data.columns):
        ax.bar(x + i * width, data[col], width=width, label=col, alpha=0.85)
    ax.set_xticks(x + width * (n_types - 1) / 2)
    ax.set_xticklabels(data.index, rotation=30, ha="right")
    ax.set_title("Patient-days per Study by Data Type")
    ax.set_ylabel("Patient-days")
    ax.legend(title="Data type")
    fig.tight_layout()
    return fig


# ── 3. Complete patient-days treemap ──────────────────────────────────────────

def plot_complete_days_treemap(stats_df: pd.DataFrame) -> plt.Figure:
    """Treemap: total complete patient-days (CGM + bolus + basal) per study."""
    data = (stats_df[
                (stats_df["metric"] == "patient_days_complete") &
                (stats_df["data_type"] == "all")
            ]
            .groupby("study")["value"].sum()
            .sort_values(ascending=False))

    if data.empty or data.sum() == 0:
        fig, ax = _fig(); ax.set_title("Complete patient-days (no data)"); return fig

    fig, ax = _fig(10, 5)
    colors = [_study_color(s) for s in data.index]
    labels = [f"{s}\n{int(v):,} days" for s, v in data.items()]
    squarify.plot(sizes=data.values, label=labels, color=colors, alpha=0.85, ax=ax)
    ax.set_title("Complete Patient-days per Study (CGM + Bolus + Basal)")
    ax.axis("off")
    fig.tight_layout()
    return fig


# ── 4. CDFs: raw values per study ─────────────────────────────────────────────

def plot_cdfs(store: dict[str, dict[str, pd.DataFrame]]) -> plt.Figure:
    """CDF per study for CGM, bolus, and basal — one subplot per data type."""
    configs = [
        ("cgm",   "cgm",       "CGM (mg/dL)",      False),
        ("bolus", "bolus",     "Bolus (U)",         True),
        ("basal", "basal_rate","Basal rate (U/hr)", False),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, (data_type, col, xlabel, log_x) in zip(axes, configs):
        for study, data_types in store.items():
            if data_type not in data_types:
                continue
            df = data_types[data_type]
            vals = df[col].dropna().values
            if len(vals) == 0:
                continue
            if log_x:
                vals = vals[vals > 0]
            cdf_module.plot_cdf(
                vals, ax=ax, label=study,
                color=_study_color(study), linewidth=1, markersize=0, linestyle="-",
            )
        ax.set_title(f"CDF — {data_type}")
        ax.set_xlabel(xlabel)
        if log_x:
            ax.set_xscale("log")
        ax.legend(fontsize=7)

    fig.tight_layout()
    return fig


# ── 5. TDD CDFs ───────────────────────────────────────────────────────────────

def plot_tdd_cdfs(tdd_df: pd.DataFrame) -> plt.Figure:
    """CDF per study for basal TDD, bolus TDD, and total TDD."""
    configs = [("basal", "Basal TDD (U/day)"), ("bolus", "Bolus TDD (U/day)"), ("total", "Total TDD (U/day)")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, (col, xlabel) in zip(axes, configs):
        for study, group in tdd_df.groupby("study"):
            vals = group[col].dropna().values
            if len(vals) == 0:
                continue
            cdf_module.plot_cdf(
                vals, ax=ax, label=study,
                color=_study_color(study), linewidth=1, markersize=0, linestyle="-",
            )
        ax.set_title(f"CDF — {col} TDD")
        ax.set_xlabel(xlabel)
        ax.legend(fontsize=7)

    fig.tight_layout()
    return fig


# ── 6. Scatter: per-patient geometric mean vs geometric std ───────────────────

def plot_gm_vs_gs(patient_stats_df: pd.DataFrame) -> plt.Figure:
    """Scatter plot of per-patient geometric mean vs geometric std, coloured by study.

    One subplot per data type (cgm, bolus, basal).
    """
    data_types = [dt for dt in ("cgm", "bolus", "basal")
                  if dt in patient_stats_df["data_type"].values]
    if not data_types:
        fig, ax = _fig(); ax.set_title("gm vs gs (no data)"); return fig

    fig, axes = plt.subplots(1, len(data_types), figsize=(5 * len(data_types), 4))
    if len(data_types) == 1:
        axes = [axes]

    gm_df = patient_stats_df[patient_stats_df["metric"] == "gm"].set_index(["study", "patient_id", "data_type"])["value"]
    gs_df = patient_stats_df[patient_stats_df["metric"] == "gs"].set_index(["study", "patient_id", "data_type"])["value"]

    for ax, data_type in zip(axes, data_types):
        for study in patient_stats_df["study"].unique():
            idx = pd.IndexSlice[study, :, data_type]
            try:
                gm_vals = gm_df.loc[idx].values
                gs_vals = gs_df.loc[idx].values
            except KeyError:
                continue
            mask = np.isfinite(gm_vals) & np.isfinite(gs_vals)
            ax.scatter(gm_vals[mask], gs_vals[mask], label=study,
                       color=_study_color(study), s=15, alpha=0.7)

        ax.set_xlabel(f"Geometric mean — {data_type}")
        ax.set_ylabel("Geometric std")
        ax.set_title(f"gm vs gs — {data_type}")
        ax.legend(fontsize=7)

    fig.tight_layout()
    return fig


# ── 7. Moving averages (circadian patterns) ───────────────────────────────────

def plot_moving_averages(store: dict[str, dict[str, pd.DataFrame]]) -> plt.Figure:
    """Moving average of values by hour-of-day per study (one subplot per data type)."""
    configs = [
        ("cgm",   "cgm",        "CGM (mg/dL)"),
        ("bolus", "bolus",      "Bolus (U)"),
        ("basal", "basal_rate", "Basal rate (U/hr)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, (data_type, col, ylabel) in zip(axes, configs):
        for study, data_types in store.items():
            if data_type not in data_types:
                continue
            df = data_types[data_type][["datetime", col]].dropna()
            if len(df) < 48:  # need at least 2 days worth of data
                continue
            try:
                drawing.drawMovingAverage(
                    ax, df, "datetime", col,
                    color=_study_color(study), label=study, s=5,
                )
            except Exception:
                pass
        ax.set_title(f"Circadian pattern — {data_type}")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=7)

    fig.tight_layout()
    return fig
