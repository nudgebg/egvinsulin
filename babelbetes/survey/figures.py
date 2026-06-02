"""Validation figures for the BabelBetes output validation report."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import squarify
from typing import NamedTuple

from babelbetes import drawing

# Consistent colour palette keyed by study name (falls back to tab10 for unknown studies)
_STUDY_COLORS: dict[str, str] = {}
_CMAP = plt.cm.get_cmap("tab10")


class _CDFConfig(NamedTuple):
    data_type: str
    col: str
    xlabel: str
    log_x: bool = False


class _TDDConfig(NamedTuple):
    col: str
    xlabel: str
    log_x: bool = False


_CDF_CONFIGS = [
    _CDFConfig(data_type="cgm",   col="cgm",       xlabel="CGM (mg/dL)"),
    _CDFConfig(data_type="bolus", col="bolus",      xlabel="Bolus (U)",         log_x=True),
    _CDFConfig(data_type="basal", col="basal_rate", xlabel="Basal rate (U/hr)", log_x=True),
]

_TDD_CONFIGS = [
    _TDDConfig(col="basal", xlabel="Basal TDD (U/day)", log_x=True),
    _TDDConfig(col="bolus", xlabel="Bolus TDD (U/day)", log_x=True),
    _TDDConfig(col="total", xlabel="Total TDD (U/day)", log_x=True),
]

_CDF_QUANTILES = np.linspace(0, 1, 401)  # 0.25% resolution


def _plot_cdf_lines(ax: plt.Axes, df: pd.DataFrame, value_col: str, study_col: str) -> None:
    """Plot per-study CDF lines from pre-computed quantiles.

    Uses 401 fixed quantile points (0.25% resolution) per study regardless of
    data size — deterministic, exact, and fast for any dataset.
    """
    for study, group in df.groupby(study_col, observed=True):
        quantiles = np.quantile(group[value_col].to_numpy(), _CDF_QUANTILES)
        ax.plot(quantiles, _CDF_QUANTILES, color=_study_color(study), linewidth=1, label=study)
    ax.legend(fontsize=7)


def _study_color(study: str) -> str:
    if study not in _STUDY_COLORS:
        _STUDY_COLORS[study] = _CMAP(len(_STUDY_COLORS) % 10)
    return _STUDY_COLORS[study]


def _fig(w=10, h=4):
    return plt.subplots(figsize=(w, h))


def plot_subjects_per_study(stats_df: pd.DataFrame) -> plt.Figure:
    """Bar chart: number of patients per study.

    Args:
        stats_df: Columns [study, data_type, metric, value].
                  Uses rows where metric="patient_count", data_type="all".
    """
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


def plot_days_per_study(stats_df: pd.DataFrame) -> plt.Figure:
    """Grouped bar chart: patient-days per study, split by data type.

    Args:
        stats_df: Columns [study, data_type, metric, value].
                  Uses rows where metric="patient_days" (cgm/bolus/basal) and
                  metric="complete_days" (data_type="complete").
    """
    data = (pd.concat([
                stats_df[stats_df["metric"] == "patient_days"][["study", "data_type", "value"]],
                stats_df[stats_df["metric"] == "complete_days"][["study", "data_type", "value"]],
            ])
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


def plot_complete_days_treemap(stats_df: pd.DataFrame) -> plt.Figure:
    """Treemap: total complete patient-days (CGM + bolus + basal) per study.

    Args:
        stats_df: Columns [study, data_type, metric, value].
                  Uses rows where metric="complete_days", data_type="complete".
    """
    data = (stats_df[
                (stats_df["metric"] == "complete_days") &
                (stats_df["data_type"] == "complete")
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


def plot_cdfs(cdf_df: pd.DataFrame) -> plt.Figure:
    """CDF per study for CGM, bolus, and basal — one subplot per data type.

    Args:
        cdf_df: Pre-computed quantile DataFrame from compute.compute_cdf_quantiles().
                Columns: [study, data_type, quantile_level, value].
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, cfg in zip(axes, _CDF_CONFIGS):
        df = cdf_df[cdf_df["data_type"] == cfg.data_type]
        if not df.empty:
            for study, group in df.groupby("study", observed=True):
                ax.plot(group["value"], group["quantile_level"],
                        color=_study_color(study), linewidth=1, label=study)
            ax.legend(fontsize=7)
        ax.set_title(f"CDF — {cfg.data_type}")
        ax.set_xlabel(cfg.xlabel)
        if cfg.log_x:
            ax.set_xscale("log")

    fig.tight_layout()
    return fig


def plot_tdd_cdfs(tdd_df: pd.DataFrame) -> plt.Figure:
    """CDF per study for basal TDD, bolus TDD, and total TDD.

    Args:
        tdd_df: Columns [study, patient_id, date, basal, bolus, total].
                basal/bolus/total are daily insulin doses in U/day.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, cfg in zip(axes, _TDD_CONFIGS):
        df = tdd_df[["study", cfg.col]].dropna()
        if not df.empty:
            _plot_cdf_lines(ax, df, cfg.col, "study")
        ax.set_title(f"CDF — {cfg.col} TDD")
        ax.set_xlabel(cfg.xlabel)
        if cfg.log_x:
            ax.set_xscale("log")

    fig.tight_layout()
    return fig


def plot_gm_vs_gs(patient_stats_df: pd.DataFrame) -> plt.Figure:
    """Scatter plot of per-patient geometric mean vs geometric std, coloured by study.

    One subplot per data type (cgm, bolus, basal).

    Args:
        patient_stats_df: Columns [study, patient_id, data_type, metric, value].
                          Uses metric="gm" (geometric mean) and metric="gs" (geometric std).
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


def plot_tdd_split(patient_stats_df: pd.DataFrame, relative: bool = False) -> plt.Figure:
    """Stacked bar chart of mean daily basal vs bolus TDD per study.

    Args:
        patient_stats_df: Columns [study, patient_id, data_type, metric, value].
                          Uses data_type='tdd', metrics 'basal_gm' and 'bolus_gm'.
        relative: When True, show percentage split instead of absolute U/day using a
                  seaborn grouped bar chart. A dashed line at 50% is drawn for reference.
    """
    tdd = patient_stats_df[patient_stats_df["data_type"] == "tdd"]
    basal = tdd[tdd["metric"] == "basal_gm"].groupby("study")["value"].mean()
    bolus = tdd[tdd["metric"] == "bolus_gm"].groupby("study")["value"].mean()

    studies = sorted(set(basal.index) | set(bolus.index))
    basal_vals = np.array([basal.get(s, 0.0) for s in studies])
    bolus_vals = np.array([bolus.get(s, 0.0) for s in studies])

    fig, ax = _fig(10, 4)

    if relative:
        total = np.where(basal_vals + bolus_vals > 0, basal_vals + bolus_vals, 1.0)
        long = pd.DataFrame({
            "study":     studies * 2,
            "component": ["Basal"] * len(studies) + ["Bolus"] * len(studies),
            "pct":       np.concatenate([basal_vals / total * 100, bolus_vals / total * 100]),
        })
        sns.barplot(data=long, x="study", y="pct", hue="component",
                    palette={"Basal": "steelblue", "Bolus": "salmon"}, ax=ax)
        ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.set_ylabel("TDD fraction (%)")
        ax.set_title("Daily TDD: Basal vs Bolus Split (%)")
        ax.set_xlabel("")
    else:
        x = np.arange(len(studies))
        ax.bar(x, basal_vals, label="Basal", color="steelblue", alpha=0.85)
        ax.bar(x, bolus_vals, bottom=basal_vals, label="Bolus", color="salmon", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(studies, rotation=30, ha="right")
        ax.set_ylabel("Insulin (U/day)")
        ax.set_title("Mean Daily TDD: Basal vs Bolus Split")

    ax.tick_params(axis="x", rotation=30)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_gap_chunk_cdfs(gap_dur_dict: dict[str, pd.DataFrame]) -> plt.Figure:
    """CDF of gap and chunk durations per data type, coloured by study.

    Args:
        gap_dur_dict: Output of compute.compute_gap_durations().
                      Dict keyed by data_type; each DataFrame has columns
                      [study, patient_id, kind, dur_hrs].
    """
    data_types = [dt for dt in ("cgm", "basal", "bolus") if dt in gap_dur_dict]
    if not data_types:
        fig, ax = _fig()
        ax.set_title("Gap/Chunk CDFs (no data)")
        return fig

    data = pd.concat(
        [df.assign(data_type=dt) for dt, df in gap_dur_dict.items()],
        ignore_index=True,
    )

    fig, axes = plt.subplots(2, len(data_types), figsize=(5 * len(data_types), 8))
    if len(data_types) == 1:
        axes = axes.reshape(2, 1)

    for col_i, data_type in enumerate(data_types):
        for row_i, kind in enumerate(("chunk", "gap")):
            ax = axes[row_i, col_i]
            subset = data[(data["data_type"] == data_type) & (data["kind"] == kind)]
            if not subset.empty:
                sns.ecdfplot(data=subset, x="dur_hrs", hue="study", ax=ax)
            ax.set_title(f"{kind.capitalize()} duration CDF — {data_type}")
            ax.set_xlabel("Duration (hrs)")
            ax.set_ylabel("CDF")

    fig.tight_layout()
    return fig


def plot_moving_averages(store: dict[str, pd.DataFrame]) -> plt.Figure:
    """Moving average of values by hour-of-day per study — one subplot per data type.

    Args:
        store: {data_type: df} where df contains a study_name column.
               cgm df columns:   patient_id, study_name, datetime, cgm (float, mg/dL)
               bolus df columns: patient_id, study_name, datetime, bolus (float, U)
               basal df columns: patient_id, study_name, datetime, basal_rate (float, U/hr)
    """
    configs = [
        ("cgm",   "cgm",        "CGM (mg/dL)"),
        ("bolus", "bolus",      "Bolus (U)"),
        ("basal", "basal_rate", "Basal rate (U/hr)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for ax, (data_type, col, ylabel) in zip(axes, configs):
        if data_type not in store:
            continue
        for study, df in store[data_type].groupby("study_name", observed=True):
            df = df[["datetime", col]].dropna()
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
