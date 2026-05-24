#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the numerical geometric embedder over candidate-pool representatives."""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from basic_relaxation_search import default_worker_count
from geometric_embedder import worker as embed_worker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = ROOT / "n25_global_proof_search" / "candidate_pool"
DEFAULT_OUTDIR = ROOT / "n25_global_proof_search" / "geometric_batch"


def read_class_summary(pool: Path) -> list[dict]:
    with (pool / "candidate_classes.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (-int(row["edge_count"]), int(row["class_id"])))
    return rows


def read_edges(pool: Path, class_id: int, edge_count: int) -> list[tuple[int, int]]:
    path = pool / f"class_{class_id:04d}_e{edge_count}_edges.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--classes", type=int, default=20)
    parser.add_argument("--runs-per-class", type=int, default=30)
    parser.add_argument("--max-nfev", type=int, default=16000)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    class_rows = read_class_summary(args.pool)[: args.classes]
    tasks = []
    task_meta = []
    for class_row in class_rows:
        class_id = int(class_row["class_id"])
        edge_count = int(class_row["edge_count"])
        edges = read_edges(args.pool, class_id, edge_count)
        n = 25
        for run in range(args.runs_per_class):
            seed = args.seed + class_id * 1000003 + run * 104729
            tasks.append((seed, edges, n, args.max_nfev, args.scale))
            task_meta.append((class_id, edge_count, seed))

    best_by_class: dict[int, dict] = {}
    actual_workers = min(args.workers, len(tasks))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        future_meta = {
            executor.submit(embed_worker, task): meta
            for task, meta in zip(tasks, task_meta)
        }
        for index, future in enumerate(as_completed(future_meta), 1):
            class_id, edge_count, seed = future_meta[future]
            row = future.result()
            row["class_id"] = class_id
            row["edge_count"] = edge_count
            current = best_by_class.get(class_id)
            if current is None or row["max_abs_edge_squared_error"] < current["max_abs_edge_squared_error"]:
                best_by_class[class_id] = row
                print(
                    f"class {class_id} e={edge_count}: "
                    f"best max_abs={row['max_abs_edge_squared_error']:.3e} "
                    f"rms={row['rms_edge_squared_error']:.3e} ({index}/{len(tasks)})",
                    flush=True,
                )

    rows = sorted(best_by_class.values(), key=lambda row: (row["max_abs_edge_squared_error"], -row["edge_count"]))
    with (args.outdir / "batch_geometric_probe_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "class_id",
            "edge_count",
            "seed",
            "max_abs_edge_squared_error",
            "rms_edge_squared_error",
            "cost",
            "nfev",
            "runtime_seconds",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})

    metadata = {
        "classes_tested": len(class_rows),
        "runs_per_class": args.runs_per_class,
        "workers": actual_workers,
        "logical_processors": os.cpu_count(),
        "pool": str(args.pool),
        "best_overall": {
            key: rows[0][key]
            for key in ["class_id", "edge_count", "max_abs_edge_squared_error", "rms_edge_squared_error", "seed"]
        }
        if rows
        else None,
        "interpretation": "Numerical filter only; positive residual is not a proof of non-embeddability.",
    }
    (args.outdir / "batch_geometric_probe_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
