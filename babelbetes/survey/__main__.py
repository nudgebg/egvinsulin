"""CLI for BabelBetes survey.

Usage:
    python -m babelbetes.survey survey [--data-dir PATH]
    python -m babelbetes.survey show [--path PATH] [--metric METRIC]
    python -m babelbetes.survey diff [--a PATH] [--b PATH]
    python -m babelbetes.survey report [--data-dir PATH]
"""
import argparse
import logging
import os
from pathlib import Path
import pandas as pd
from babelbetes import data_store
from babelbetes.logger import Logger
from babelbetes.survey import compute, diff, report as report_module, survey

log = Logger.get_logger(__name__, level=logging.INFO)


def cmd_survey(args):
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        log.error("Data directory not found: %s", data_dir)
        return 1

    log.info("Loading data from %s ...", data_dir)
    store = data_store.load(str(data_dir))

    total = sum(len(df) for df in store.values())
    log.info("Loaded %d data types, %d total rows.", len(store), total)
    rows = [
        {"data_type": dt, "study": row["study_name"], "rows": row["count"]}
        for dt, df in store.items()
        for _, row in df.groupby("study_name", observed=True).size().rename("count").reset_index().iterrows()
    ]
    breakdown = pd.DataFrame(rows).pivot_table(index="study", columns="data_type", values="rows", aggfunc="sum", fill_value=0)
    log.info("Row counts per study/data_type:\n%s", breakdown.to_string())

    ts = survey._survey_id()

    log.info("Computing TDD ...")
    tdd_df = compute.compute_tdd_per_patient(store, verbose=True)
    tdd_path = survey.save_tdd(tdd_df, survey_id=ts)
    log.info("  → %s", tdd_path)

    log.info("Computing patient stats ...")
    patient_records = (
        (compute.compute_cgm_stats(store["cgm"])   if "cgm"   in store else [])
        + (compute.compute_basal_stats(store["basal"]) if "basal" in store else [])
        + (compute.compute_bolus_stats(store["bolus"]) if "bolus" in store else [])
        + (compute.compute_carb_stats(store["carbs"]) if "carbs" in store else [])
        + compute.compute_complete_days(store)
        + compute.compute_tdd_stats(tdd_df)
    )
    patient_path = survey.save_patient_stats(patient_records, survey_id=ts)
    log.info("  → %s", patient_path)

    log.info("Computing study stats ...")
    patient_stats_df = pd.DataFrame(patient_records)
    records = (
        compute.aggregate_study_stats(patient_stats_df)
        + compute.compute_age_stats(store)
    )
    study_stats_path = survey.save_study_stats(records, survey_id=ts)
    log.info("  → %s", study_stats_path)

    log.info("Computing CDF quantiles ...")
    cdf_df = compute.compute_cdf_quantiles(store, verbose=True)
    cdf_path = survey.save_cdf_quantiles(cdf_df, survey_id=ts)
    log.info("  → %s", cdf_path)

    df = survey.load_study_stats(study_stats_path)
    pivot = df[df["metric"] == "row_count"].pivot_table(
        index="study", columns="data_type", values="value", aggfunc="sum"
    )
    log.info("Row counts per study/data_type:\n%s", pivot.to_string())
    return 0


def cmd_show(args):
    surveys = survey.list_study_stats_surveys()
    if args.path:
        path = Path(args.path)
    elif surveys:
        path = surveys[-1]
    else:
        log.error("No surveys found. Run 'survey' first.")
        return 1

    df = survey.load_study_stats(path)
    log.info("Survey: %s", path)

    if args.metric:
        df = df[df["metric"] == args.metric]
        pivot = df.pivot_table(index="study", columns="data_type", values="value", aggfunc="sum")
        print(pivot.to_string())
    else:
        for metric, group in df.groupby("metric"):
            pivot = group.pivot_table(index="study", columns="data_type", values="value", aggfunc="sum")
            print(f"── {metric} ──")
            print(pivot.to_string())
            print()
    return 0


def cmd_report(args):
    stats_path   = Path(args.stats)   if args.stats   else None
    patient_path = Path(args.patient) if args.patient else None
    tdd_path     = Path(args.tdd)     if args.tdd     else None
    cdf_path     = Path(args.cdf)     if args.cdf     else None

    try:
        study_stats_df   = survey.load_study_stats(stats_path)
        patient_stats_df = survey.load_patient_stats(patient_path)
        tdd_df           = survey.load_tdd(tdd_path)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    # cdf is optional — report renders without it
    try:
        cdf_df = survey.load_cdf_quantiles(cdf_path)
    except FileNotFoundError:
        cdf_df = None

    log.info("Stats survey:   %s", study_stats_df["survey_id"].iloc[0])
    log.info("Patient survey: %s", patient_stats_df["survey_id"].iloc[0])
    log.info("TDD survey:     %s", tdd_df["survey_id"].iloc[0])
    log.info("CDF survey:     %s", cdf_df["survey_id"].iloc[0] if cdf_df is not None else "(none — CDF section skipped)")

    store = None
    if args.data_dir:
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            log.error("Data directory not found: %s", data_dir)
            return 1
        log.info("Loading store from %s ...", data_dir)
        store = data_store.load(str(data_dir))

    log.info("Generating HTML report ...")
    out = report_module.generate_report(study_stats_df, patient_stats_df, tdd_df, cdf_df=cdf_df, store=store)
    log.info("Report: %s", out)
    return 0


def cmd_diff(args):
    surveys = survey.list_study_stats_surveys()

    if args.a and args.b:
        path_a, path_b = Path(args.a), Path(args.b)
    elif len(surveys) >= 2:
        path_a, path_b = surveys[-2], surveys[-1]
    else:
        print("Error: need at least 2 surveys. Run 'survey' first, or specify --a and --b.")
        return 1

    snap_a = survey.load_study_stats(path_a)
    snap_b = survey.load_study_stats(path_b)

    log.info("Comparing:\n  A: %s\n  B: %s", path_a, path_b)
    diff_df = diff.diff_study_stats(snap_a, snap_b)
    print(diff.format_diff_report(diff_df))
    return 0


def main():
    parser = argparse.ArgumentParser(description="BabelBetes data survey CLI")
    sub = parser.add_subparsers(dest="command")

    p_snap = sub.add_parser("survey", help="Compute stats and save a survey")
    p_snap.add_argument("--data-dir", default=os.path.join(os.getcwd(), "data", "out"),
                        help="Path to the output data directory (default: data/out)")

    p_show = sub.add_parser("show", help="Print the latest (or a specific) survey")
    p_show.add_argument("--path", default=None, help="Path to a specific survey Parquet file")
    p_show.add_argument("--metric", default=None, help="Show only a single metric (e.g. row_count)")

    p_report = sub.add_parser("report", help="Generate HTML report from the latest (or specified) surveys")
    p_report.add_argument("--stats",    default=None, help="Path to a stats survey Parquet file (default: latest)")
    p_report.add_argument("--patient",  default=None, help="Path to a patient-stats survey Parquet file (default: latest)")
    p_report.add_argument("--tdd",      default=None, help="Path to a TDD survey Parquet file (default: latest)")
    p_report.add_argument("--cdf",      default=None, help="Path to a CDF quantiles survey Parquet file (default: latest)")
    p_report.add_argument("--data-dir", default=None, help="Path to the output data directory to load raw store for circadian patterns (optional)")

    p_diff = sub.add_parser("diff", help="Diff the two most recent surveys")
    p_diff.add_argument("--a", default=None, help="Path to the earlier survey Parquet file")
    p_diff.add_argument("--b", default=None, help="Path to the later survey Parquet file")

    args = parser.parse_args()
    if args.command == "survey":
        return cmd_survey(args)
    elif args.command == "show":
        return cmd_show(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "diff":
        return cmd_diff(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
