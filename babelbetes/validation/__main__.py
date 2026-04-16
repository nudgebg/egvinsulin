"""CLI for BabelBetes validation.

Usage:
    python -m babelbetes.validation snapshot [--data-dir PATH]
    python -m babelbetes.validation show [--path PATH] [--metric METRIC]
    python -m babelbetes.validation diff [--a PATH] [--b PATH]
    python -m babelbetes.validation report [--data-dir PATH]
"""
import argparse
import logging
import os
from pathlib import Path
import pandas as pd
from babelbetes.src import data_store
from babelbetes.src.logger import Logger
from babelbetes.validation import compute, diff, report as report_module, snapshot

log = Logger.get_logger(__name__, level=logging.INFO)


def cmd_snapshot(args):
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

    ts = snapshot._snapshot_id()

    log.info("Computing TDD ...")
    tdd_df = compute.compute_tdd_per_patient(store, verbose=True)
    tdd_path = snapshot.save_tdd(tdd_df, snapshot_id=ts)
    log.info("  → %s", tdd_path)

    log.info("Computing patient stats ...")
    patient_records = (
        (compute.compute_cgm_stats(store["cgm"])   if "cgm"   in store else [])
        + (compute.compute_basal_stats(store["basal"]) if "basal" in store else [])
        + (compute.compute_bolus_stats(store["bolus"]) if "bolus" in store else [])
        + compute.compute_complete_days(store)
        + compute.compute_tdd_stats(tdd_df)
    )
    patient_path = snapshot.save_patient_stats(patient_records, snapshot_id=ts)
    log.info("  → %s", patient_path)

    log.info("Computing study stats ...")
    patient_stats_df = pd.DataFrame(patient_records)
    records = (
        compute.aggregate_study_stats(patient_stats_df)
        + compute.compute_age_stats(store)
    )
    study_stats_path = snapshot.save_study_stats(records, snapshot_id=ts)
    log.info("  → %s", study_stats_path)

    log.info("Computing CDF quantiles ...")
    cdf_df = compute.compute_cdf_quantiles(store, verbose=True)
    cdf_path = snapshot.save_cdf_quantiles(cdf_df, snapshot_id=ts)
    log.info("  → %s", cdf_path)

    df = snapshot.load_study_stats(study_stats_path)
    pivot = df[df["metric"] == "row_count"].pivot_table(
        index="study", columns="data_type", values="value", aggfunc="sum"
    )
    log.info("Row counts per study/data_type:\n%s", pivot.to_string())
    return 0


def cmd_show(args):
    snapshots = snapshot.list_study_stats_snapshots()
    if args.path:
        path = Path(args.path)
    elif snapshots:
        path = snapshots[-1]
    else:
        log.error("No snapshots found. Run 'snapshot' first.")
        return 1

    df = snapshot.load_study_stats(path)
    log.info("Snapshot: %s", path)

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
        study_stats_df   = snapshot.load_study_stats(stats_path)
        patient_stats_df = snapshot.load_patient_stats(patient_path)
        tdd_df           = snapshot.load_tdd(tdd_path)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    # cdf is optional — report renders without it
    try:
        cdf_df = snapshot.load_cdf_quantiles(cdf_path)
    except FileNotFoundError:
        cdf_df = None

    log.info("Stats snapshot:   %s", study_stats_df["snapshot_id"].iloc[0])
    log.info("Patient snapshot: %s", patient_stats_df["snapshot_id"].iloc[0])
    log.info("TDD snapshot:     %s", tdd_df["snapshot_id"].iloc[0])
    log.info("CDF snapshot:     %s", cdf_df["snapshot_id"].iloc[0] if cdf_df is not None else "(none — CDF section skipped)")

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
    snapshots = snapshot.list_study_stats_snapshots()

    if args.a and args.b:
        path_a, path_b = Path(args.a), Path(args.b)
    elif len(snapshots) >= 2:
        path_a, path_b = snapshots[-2], snapshots[-1]
    else:
        print("Error: need at least 2 snapshots. Run 'snapshot' first, or specify --a and --b.")
        return 1

    snap_a = snapshot.load_study_stats(path_a)
    snap_b = snapshot.load_study_stats(path_b)

    log.info("Comparing:\n  A: %s\n  B: %s", path_a, path_b)
    diff_df = diff.diff_study_stats(snap_a, snap_b)
    print(diff.format_diff_report(diff_df))
    return 0


def main():
    parser = argparse.ArgumentParser(description="BabelBetes data validation CLI")
    sub = parser.add_subparsers(dest="command")

    p_snap = sub.add_parser("snapshot", help="Compute stats and save a snapshot")
    p_snap.add_argument("--data-dir", default=os.path.join(os.getcwd(), "data", "out"),
                        help="Path to the output data directory (default: data/out)")

    p_show = sub.add_parser("show", help="Print the latest (or a specific) snapshot")
    p_show.add_argument("--path", default=None, help="Path to a specific snapshot Parquet file")
    p_show.add_argument("--metric", default=None, help="Show only a single metric (e.g. row_count)")

    p_report = sub.add_parser("report", help="Generate HTML report from the latest (or specified) snapshots")
    p_report.add_argument("--stats",    default=None, help="Path to a stats snapshot Parquet file (default: latest)")
    p_report.add_argument("--patient",  default=None, help="Path to a patient-stats snapshot Parquet file (default: latest)")
    p_report.add_argument("--tdd",      default=None, help="Path to a TDD snapshot Parquet file (default: latest)")
    p_report.add_argument("--cdf",      default=None, help="Path to a CDF quantiles snapshot Parquet file (default: latest)")
    p_report.add_argument("--data-dir", default=None, help="Path to the output data directory to load raw store for circadian patterns (optional)")

    p_diff = sub.add_parser("diff", help="Diff the two most recent snapshots")
    p_diff.add_argument("--a", default=None, help="Path to the earlier snapshot Parquet file")
    p_diff.add_argument("--b", default=None, help="Path to the later snapshot Parquet file")

    args = parser.parse_args()
    if args.command == "snapshot":
        return cmd_snapshot(args)
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
