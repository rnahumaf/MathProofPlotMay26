#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search for triangle-filtered candidates that survive trilateration."""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from triangle_filtered_search import worker as triangle_worker
from trilateration_eliminator import analyze_one

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "post_trilateration_search"


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def zero_based_edges(edges: list[list[int]]) -> list[tuple[int, int]]:
    return [(i - 1, j - 1) if i < j else (j - 1, i - 1) for i, j in edges]


def worker(task: tuple[int, int, int, int, int, str, int]) -> dict:
    n, seed, steps, max_nodes, max_states, tolerance, precision = task
    candidate = triangle_worker((n, seed, steps, max_nodes))
    result = analyze_one(
        f"seed_{seed}",
        zero_based_edges(candidate["edges"]),
        max_states=max_states,
        tolerance_text=tolerance,
        precision=precision,
    )
    return {
        "seed": seed,
        "edge_count": candidate["edge_count"],
        "triangle_count": candidate["triangle_count"],
        "triangle_component_count": candidate["triangle_component_count"],
        "trilateration_status": result["status"],
        "trilateration_max_width": result.get("max_width", ""),
        "trilateration_eliminated_at_step": result.get("eliminated_at_step", ""),
        "edges": candidate["edges"],
        "certificate": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=260)
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--max-states", type=int, default=200000)
    parser.add_argument("--precision", type=int, default=100)
    parser.add_argument("--tolerance", default="1e-40")
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    tasks = [
        (
            args.n,
            args.seed + 7919 * i,
            args.steps,
            args.max_nodes,
            args.max_states,
            args.tolerance,
            args.precision,
        )
        for i in range(args.runs)
    ]
    actual_workers = min(args.workers, len(tasks))
    rows: list[dict] = []
    survivors: list[dict] = []
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            if row["edge_count"] >= 71 and row["trilateration_status"] != "eliminated":
                survivors.append(row)
                print(
                    f"survivor {len(survivors)} at {index}/{len(tasks)}: "
                    f"e={row['edge_count']} seed={row['seed']} status={row['trilateration_status']}",
                    flush=True,
                )
            elif index % 100 == 0:
                best = max(r["edge_count"] for r in rows)
                print(f"checked {index}/{len(tasks)}; best_edges={best}; survivors={len(survivors)}", flush=True)

    with (OUTDIR / "post_trilateration_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "edge_count",
            "triangle_count",
            "triangle_component_count",
            "trilateration_status",
            "trilateration_max_width",
            "trilateration_eliminated_at_step",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})

    for index, row in enumerate(survivors, 1):
        with (OUTDIR / f"survivor_{index:04d}_e{row['edge_count']}_edges.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["i", "j"])
            writer.writerows(row["edges"])
        (OUTDIR / f"survivor_{index:04d}_certificate.json").write_text(
            json.dumps(row["certificate"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    metadata = {
        "runs": args.runs,
        "steps": args.steps,
        "workers": actual_workers,
        "logical_processors": os.cpu_count(),
        "best_edge_count": max((row["edge_count"] for row in rows), default=None),
        "survivor_count": len(survivors),
        "status_counts": {
            status: sum(1 for row in rows if row["trilateration_status"] == status)
            for status in sorted({row["trilateration_status"] for row in rows})
        },
        "interpretation": (
            "A survivor is a 71+ candidate passing the current exact filters "
            "that was not eliminated by finite trilateration."
        ),
    }
    (OUTDIR / "post_trilateration_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
