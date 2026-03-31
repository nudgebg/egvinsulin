import numpy as np
import pandas as pd

_CHANGE_THRESHOLD_PCT = 5.0


def diff_stats(snap_a: pd.DataFrame, snap_b: pd.DataFrame) -> pd.DataFrame:
    """Diff two stats snapshots.

    Uses an outer merge on (study, data_type, metric) so that:
    - New metrics in snap_b appear with value_before=NaN (status='added')
    - Metrics only in snap_a appear with value_after=NaN (status='removed')
    - Metrics in both get delta and pct_change computed

    Args:
        snap_a: Earlier snapshot DataFrame from snapshot.load_stats()
        snap_b: Later snapshot DataFrame from snapshot.load_stats()

    Returns:
        DataFrame with columns: study, data_type, metric, value_before, value_after,
        delta, pct_change, status, flagged
    """
    keys = ["study", "data_type", "metric"]
    a = snap_a[keys + ["value"]].rename(columns={"value": "value_before"})
    b = snap_b[keys + ["value"]].rename(columns={"value": "value_after"})

    merged = a.merge(b, on=keys, how="outer")
    merged["delta"] = merged["value_after"] - merged["value_before"]
    merged["pct_change"] = merged["delta"] / merged["value_before"].abs() * 100

    merged["status"] = np.where(
        merged["value_before"].isna(), "added",
        np.where(merged["value_after"].isna(), "removed", "changed")
    )
    merged.loc[merged["delta"] == 0, "status"] = "unchanged"

    merged["flagged"] = (
        (merged["status"] == "changed") &
        (merged["pct_change"].abs() > _CHANGE_THRESHOLD_PCT)
    )

    return merged.sort_values(keys).reset_index(drop=True)


def format_diff_report(diff_df: pd.DataFrame) -> str:
    """Format a diff DataFrame as a human-readable text table."""
    lines = []
    for _, row in diff_df.iterrows():
        if row["status"] == "unchanged":
            continue

        flag = " ⚠️" if row["flagged"] else ""
        before = f"{row['value_before']:.1f}" if pd.notna(row["value_before"]) else "—"
        after = f"{row['value_after']:.1f}" if pd.notna(row["value_after"]) else "—"

        if row["status"] in ("added", "removed"):
            pct_str = f"  [{row['status'].upper()}]"
        else:
            pct_str = f"  {row['pct_change']:+.1f}%{flag}"

        lines.append(
            f"{row['study']:<12} {row['data_type']:<8} {row['metric']:<15}"
            f"  {before:>10} → {after:<10}{pct_str}"
        )

    if not lines:
        return "No changes detected."

    header = f"{'study':<12} {'data_type':<8} {'metric':<15}  {'before':>10}   {'after':<10}"
    separator = "-" * len(header)
    return "\n".join([header, separator] + lines)
