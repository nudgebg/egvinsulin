"""CLI for BabelBetes validation.

Usage:
    python -m babelbetes.validation snapshot [--data-dir PATH]
    python -m babelbetes.validation show [--path PATH] [--metric METRIC]
    python -m babelbetes.validation diff [--a PATH] [--b PATH]
    python -m babelbetes.validation report [--data-dir PATH]
"""
import argparse
import os
from pathlib import Path

from babelbetes.src import data_store
from babelbetes.validation import compute, diff, report as report_module, snapshot


def cmd_snapshot(args):
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        return 1

    print(f"Loading data from {data_dir} ...")
    store = data_store.load(str(data_dir))

    total = sum(len(df) for df in store.values())
    print(f"Loaded {len(store)} data types, {total} total rows.")

    ts = snapshot._snapshot_id()

    print("Computing study stats ...")
    records = (compute.compute_basic_stats(store, verbose=True)
               + compute.compute_study_stats_extended(store, verbose=True))
    study_stats_path = snapshot.save_study_stats(records, snapshot_id=ts)
    print(f"  → {study_stats_path}")

    print("Computing patient stats ...")
    patient_records = compute.compute_patient_stats(store, verbose=True)
    patient_path = snapshot.save_patient_stats(patient_records, snapshot_id=ts)
    print(f"  → {patient_path}")

    print("Computing TDD ...")
    tdd_df = compute.compute_tdd_per_patient(store, verbose=True)
    tdd_path = snapshot.save_tdd(tdd_df, snapshot_id=ts)
    print(f"  → {tdd_path}")

    print("Computing CDF quantiles ...")
    cdf_df = compute.compute_cdf_quantiles(store, verbose=True)
    cdf_path = snapshot.save_cdf_quantiles(cdf_df, snapshot_id=ts)
    print(f"  → {cdf_path}")

    # Print a quick summary table
    df = snapshot.load_study_stats(study_stats_path)
    pivot = df[df["metric"] == "row_count"].pivot_table(
        index="study", columns="data_type", values="value", aggfunc="sum"
    )
    print("\nRow counts per study/data_type:")
    print(pivot.to_string())
    return 0


def cmd_show(args):
    snapshots = snapshot.list_study_stats_snapshots()
    if args.path:
        path = Path(args.path)
    elif snapshots:
        path = snapshots[-1]
    else:
        print("Error: no snapshots found. Run 'snapshot' first.")
        return 1

    df = snapshot.load_study_stats(path)
    print(f"Snapshot: {path}\n")

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
    stats_path    = Path(args.stats)    if args.stats    else snapshot.list_study_stats_snapshots()[-1]  if snapshot.list_study_stats_snapshots()  else None
    patient_path  = Path(args.patient)  if args.patient  else snapshot.list_patient_stats_snapshots()[-1] if snapshot.list_patient_stats_snapshots() else None
    tdd_path      = Path(args.tdd)      if args.tdd      else snapshot.list_tdd_snapshots()[-1]           if snapshot.list_tdd_snapshots()           else None
    cdf_path      = Path(args.cdf)      if args.cdf      else snapshot.list_cdf_quantile_snapshots()[-1]  if snapshot.list_cdf_quantile_snapshots()  else None

    missing = [name for name, p in [("stats", stats_path), ("patient", patient_path), ("tdd", tdd_path)] if p is None]
    if missing:
        print(f"Error: no {', '.join(missing)} snapshot(s) found. Run 'snapshot' first.")
        return 1

    print(f"Stats snapshot:   {stats_path}")
    print(f"Patient snapshot: {patient_path}")
    print(f"TDD snapshot:     {tdd_path}")
    print(f"CDF snapshot:     {cdf_path or '(none — CDF section skipped)'}")

    study_stats_df   = snapshot.load_study_stats(stats_path)
    patient_stats_df = snapshot.load_stats(patient_path)
    tdd_df           = snapshot.load_tdd(tdd_path)
    cdf_df           = snapshot.load_cdf_quantiles(cdf_path) if cdf_path else None

    store = None
    if args.data_dir:
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            print(f"Error: data directory not found: {data_dir}")
            return 1
        print(f"Loading store from {data_dir} ...")
        store = data_store.load(str(data_dir))

    print("Generating HTML report ...")
    out = report_module.generate_report(study_stats_df, patient_stats_df, tdd_df, cdf_df=cdf_df, store=store)
    print(f"\nReport: {out}")
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

    print(f"Comparing:\n  A: {path_a}\n  B: {path_b}\n")
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
