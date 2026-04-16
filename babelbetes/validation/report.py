"""HTML report generation for the BabelBetes validation system."""
import base64
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless report generation
import matplotlib.pyplot as plt
import pandas as pd

from babelbetes.validation import figures as fig_module

REPORT_DIR = Path("data/out/validation/reports")


def _fig_to_b64(fig: plt.Figure) -> str:
    """Encode a matplotlib figure as a base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


def _section(title: str, b64: str, description: str = "") -> str:
    desc_html = f"<p class='desc'>{description}</p>" if description else ""
    return f"""
    <section>
      <h2>{title}</h2>
      {desc_html}
      <img src="data:image/png;base64,{b64}" style="max-width:100%;">
    </section>
    """


_CSS = """
body {{ font-family: sans-serif; max-width: 1200px; margin: 40px auto; padding: 0 20px; color: #333; }}
h1   {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
h2   {{ margin-top: 40px; color: #555; font-size: 1.1em; text-transform: uppercase; letter-spacing: 1px; }}
p.desc {{ color: #666; font-size: 0.9em; margin-bottom: 8px; }}
section {{ margin-bottom: 32px; }}
.meta {{ color: #999; font-size: 0.85em; margin-bottom: 24px; }}
"""


def generate_report(
    study_stats_df: pd.DataFrame,
    patient_stats_df: pd.DataFrame,
    tdd_df: pd.DataFrame,
    cdf_df: pd.DataFrame | None = None,
    store: dict[str, dict[str, pd.DataFrame]] | None = None,
    output_path: Path | None = None,
) -> Path:
    """Generate a self-contained HTML validation report from pre-computed snapshots.

    Args:
        study_stats_df:   Study-level stats. Columns: [study, data_type, metric, value, snapshot_id].
                          From snapshot.load_study_stats().
        patient_stats_df: Per-patient stats. Columns: [study, patient_id, data_type, metric, value].
                          From snapshot.load_patient_stats(). May be empty.
        tdd_df:           Daily TDD per patient. Columns: [study, patient_id, date, basal, bolus, total].
                          From snapshot.load_tdd(). May be empty.
        cdf_df:           Pre-computed CDF quantiles. Columns: [study, data_type, quantile_level, value].
                          From snapshot.load_cdf_quantiles(). CDF section skipped if None.
        store:            Optional raw data dict {data_type: df} for circadian pattern figures.
                          Circadian section skipped if None.
        output_path:      Optional override for the output HTML path.
                          Default: data/validation/report_<timestamp>.html

    Returns:
        Path to the generated HTML file.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    sections_html = []

    def render(title, fn, description=""):
        print(f"  Rendering: {title} ...")
        try:
            fig = fn()
            sections_html.append(_section(title, _fig_to_b64(fig), description))
        except Exception as e:
            sections_html.append(f"<section><h2>{title}</h2><p style='color:red'>Error: {e}</p></section>")

    render("Subjects per Study",
           lambda: fig_module.plot_subjects_per_study(study_stats_df),
           "Number of unique patients per study.")

    render("Patient-days per Study by Data Type",
           lambda: fig_module.plot_days_per_study(study_stats_df),
           "Total patient-days available per study, broken down by data type.")

    render("Complete Patient-days (Treemap)",
           lambda: fig_module.plot_complete_days_treemap(study_stats_df),
           "Patient-days where CGM, bolus, and basal data are all available.")

    if cdf_df is not None:
        render("CDFs — Raw Values",
               lambda: fig_module.plot_cdfs(cdf_df),
               "Cumulative distribution functions for CGM (mg/dL), bolus (U), and basal rate (U/hr) per study.")

    if not tdd_df.empty:
        render("CDFs — Total Daily Dose",
               lambda: fig_module.plot_tdd_cdfs(tdd_df),
               "CDF of daily basal, bolus, and total insulin dose per study.")

    if not patient_stats_df.empty:
        render("Per-patient Geometric Mean vs Geometric Std",
               lambda: fig_module.plot_gm_vs_gs(patient_stats_df),
               "Each point is one patient. Spread shows inter-patient variability per study.")

        if "tdd" in patient_stats_df["data_type"].values:
            render("Daily TDD Split: Basal vs Bolus",
                   lambda: fig_module.plot_tdd_split(patient_stats_df),
                   "Geometric mean of each patient's daily dose, averaged per study.")

    if store is not None:
        from babelbetes.validation import compute as _compute
        gap_dur_dict = _compute.compute_gap_durations(store)
        if gap_dur_dict:
            render("Gap and Chunk Duration CDFs",
                   lambda: fig_module.plot_gap_chunk_cdfs(gap_dur_dict),
                   "Empirical CDF of continuous data chunk lengths and gap lengths per study.")

    if store is not None:
        render("Circadian Patterns (Moving Averages)",
               lambda: fig_module.plot_moving_averages(store),
               "Rolling average of values by hour of day, revealing daily patterns across studies.")

    # ── assemble HTML ──────────────────────────────────────────────────────────
    snapshot_ids = study_stats_df["snapshot_id"].unique().tolist() if "snapshot_id" in study_stats_df.columns else []
    meta = f"Generated: {ts}"
    if snapshot_ids:
        meta += f" &nbsp;|&nbsp; Snapshot: {', '.join(snapshot_ids)}"
    n_studies = study_stats_df["study"].nunique() if not study_stats_df.empty else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BabelBetes Validation Report — {ts}</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>BabelBetes Validation Report</h1>
  <p class="meta">{meta} &nbsp;|&nbsp; {n_studies} studies</p>
  {''.join(sections_html)}
</body>
</html>"""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = REPORT_DIR / f"report_{ts}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
