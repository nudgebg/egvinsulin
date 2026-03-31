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

import pandas as pd

from babelbetes.validation import compute, diff, report as report_module, snapshot


def _load_store(data_dir: Path) -> dict[str, dict[str, pd.DataFrame]]:
    """Load all available study/data_type combinations from the output directory.

    Reads each (study_name, data_type) partition individually to keep schemas
    consistent (different data types have different columns).

    Expects structure: <data_dir>/study_name=<X>/data_type=<Y>/patient_id=<Z>/

    Returns:
        Nested dict {study_name: {data_type: DataFrame}}
    """
    store: dict[str, dict[str, pd.DataFrame]] = {}

    for study_dir in sorted(data_dir.glob("study_name=*")):
        study_name = study_dir.name.split("=", 1)[1]
        for type_dir in sorted(study_dir.glob("data_type=*")):
            data_type = type_dir.name.split("=", 1)[1]
            try:
                df = pd.read_parquet(type_dir)
                store.setdefault(study_name, {})[data_type] = df
            except Exception as e:
                print(f"  Warning: could not load {study_name}/{data_type}: {e}")

    return store


def cmd_snapshot(args):
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        return 1

    print(f"Loading data from {data_dir} ...")
    store = _load_store(data_dir)

    total = sum(len(v) for v in store.values())
    print(f"Loaded {len(store)} studies, {total} study/data_type combinations.")

    print("Computing stats ...")
    records = compute.compute_basic_stats(store)

    path = snapshot.save_stats(records)
    print(f"Snapshot saved: {path}")

    # Print a quick summary table
    df = snapshot.load_stats(path)
    pivot = df[df["metric"] == "row_count"].pivot_table(
        index="study", columns="data_type", values="value", aggfunc="sum"
    )
    print("\nRow counts per study/data_type:")
    print(pivot.to_string())
    return 0


def cmd_show(args):
    snapshots = snapshot.list_stats_snapshots()
    if args.path:
        path = Path(args.path)
    elif snapshots:
        path = snapshots[-1]
    else:
        print("Error: no snapshots found. Run 'snapshot' first.")
        return 1

    df = snapshot.load_stats(path)
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
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        return 1

    print(f"Loading data from {data_dir} ...")
    store = _load_store(data_dir)
    total = sum(len(v) for v in store.values())
    print(f"Loaded {len(store)} studies, {total} study/data_type combinations.")

    sid = snapshot._snapshot_id()

    print("Computing basic stats ...")
    basic_records = compute.compute_basic_stats(store)

    print("Computing patient stats (this may take a while) ...")
    patient_records = compute.compute_patient_stats(store)
    patient_stats_df = pd.DataFrame(patient_records)

    print("Computing extended study stats ...")
    extended_records = compute.compute_study_stats_extended(store, patient_stats_df)

    all_stats_records = basic_records + extended_records
    stats_path = snapshot.save_stats(all_stats_records, snapshot_id=sid)
    print(f"Stats snapshot saved:         {stats_path}")

    patient_path = snapshot.save_patient_stats(patient_records, snapshot_id=sid)
    print(f"Patient stats snapshot saved: {patient_path}")

    print("Computing TDD per patient ...")
    tdd_df = compute.compute_tdd_per_patient(store)
    tdd_path = snapshot.save_tdd(tdd_df, snapshot_id=sid)
    print(f"TDD snapshot saved:           {tdd_path}")

    stats_df = snapshot.load_stats(stats_path)
    print("Generating HTML report ...")
    out = report_module.generate_report(stats_df, patient_stats_df, tdd_df, store)
    print(f"\nReport: {out}")
    return 0


def cmd_diff(args):
    snapshots = snapshot.list_stats_snapshots()

    if args.a and args.b:
        path_a, path_b = Path(args.a), Path(args.b)
    elif len(snapshots) >= 2:
        path_a, path_b = snapshots[-2], snapshots[-1]
    else:
        print("Error: need at least 2 snapshots. Run 'snapshot' first, or specify --a and --b.")
        return 1

    snap_a = snapshot.load_stats(path_a)
    snap_b = snapshot.load_stats(path_b)

    print(f"Comparing:\n  A: {path_a}\n  B: {path_b}\n")
    diff_df = diff.diff_stats(snap_a, snap_b)
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

    p_report = sub.add_parser("report", help="Compute all stats, save snapshots, and generate HTML report")
    p_report.add_argument("--data-dir", default=os.path.join(os.getcwd(), "data", "out"),
                          help="Path to the output data directory (default: data/out)")

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
