#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heuristic search under the strongest current exact necessary filters.

The search keeps only graphs satisfying:

- codegree <= 2, equivalently no K_{2,3};
- no K4;
- local unit-circle neighborhood rule;
- exact triangular-lattice consistency for edge-connected triangle components.

If this search finds a 71+ edge graph, it becomes the next candidate for
continuous geometric elimination. If repeated wide runs stay at 70, that is
evidence that the triangular-lattice layer is close to the obstruction that
explains the n=25 maximum, but it is not yet a universal proof.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from basic_relaxation_search import (
    add_edge,
    can_add_with_local_circle,
    default_worker_count,
    edge_count,
    has_edge,
    remove_edge,
    validate,
)
from triangle_lattice_filter import Edge, analyze_edges, normalize_edge

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "triangle_filtered_search"


def adj_to_edges(adj: list[int]) -> list[Edge]:
    n = len(adj)
    return [
        normalize_edge(i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if has_edge(adj, i, j)
    ]


def triangle_consistent(adj: list[int], max_nodes: int) -> bool:
    edges = adj_to_edges(adj)
    result = analyze_edges(edges, "candidate", len(edges), len(adj), max_nodes)
    return not result["eliminated"]


def can_add_strong(adj: list[int], i: int, j: int, max_nodes: int) -> bool:
    if not can_add_with_local_circle(adj, i, j):
        return False
    add_edge(adj, i, j)
    ok = triangle_consistent(adj, max_nodes)
    remove_edge(adj, i, j)
    return ok


def greedy_fill(n: int, rng: random.Random, max_nodes: int) -> list[int]:
    adj = [0] * n
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    changed = True
    while changed:
        changed = False
        rng.shuffle(edges)
        for i, j in edges:
            if can_add_strong(adj, i, j, max_nodes):
                add_edge(adj, i, j)
                changed = True
    return adj


def improve(adj: list[int], rng: random.Random, steps: int, max_nodes: int) -> list[int]:
    n = len(adj)
    all_edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    best = adj[:]
    best_edges = edge_count(best)

    for _ in range(steps):
        current_edges = [(i, j) for i, j in all_edges if has_edge(adj, i, j)]
        if not current_edges:
            break

        removed = rng.sample(current_edges, min(len(current_edges), rng.choice([1, 1, 2, 2, 3, 4])))
        for i, j in removed:
            remove_edge(adj, i, j)

        candidates = all_edges[:]
        rng.shuffle(candidates)
        for i, j in candidates:
            if can_add_strong(adj, i, j, max_nodes):
                add_edge(adj, i, j)

        e = edge_count(adj)
        if e >= best_edges:
            best = adj[:]
            best_edges = e
        elif rng.random() < 0.06:
            continue
        else:
            adj = best[:]

    return best


def worker(task: tuple[int, int, int, int]) -> dict:
    n, seed, steps, max_nodes = task
    rng = random.Random(seed)
    start = time.time()
    adj = greedy_fill(n, rng, max_nodes)
    adj = improve(adj, rng, steps, max_nodes)
    local_check = validate(adj, require_local_circle=True)
    tri_check = analyze_edges(adj_to_edges(adj), "candidate", edge_count(adj), n, max_nodes)
    edges = [
        [i + 1, j + 1]
        for i in range(n)
        for j in range(i + 1, n)
        if has_edge(adj, i, j)
    ]
    return {
        "seed": seed,
        "edge_count": edge_count(adj),
        "local_valid": local_check["valid"],
        "triangle_lattice_valid": not tri_check["eliminated"],
        "triangle_count": tri_check["triangle_count"],
        "triangle_component_count": tri_check["triangle_component_count"],
        "runtime_seconds": round(time.time() - start, 3),
        "edges": edges,
    }


def write_outputs(best: dict, rows: list[dict], args: argparse.Namespace) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "triangle_filtered_best.json").write_text(
        json.dumps(best, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / "triangle_filtered_best_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j"])
        writer.writerows(best["edges"])

    with (OUTDIR / "triangle_filtered_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "edge_count",
            "local_valid",
            "triangle_lattice_valid",
            "triangle_count",
            "triangle_component_count",
            "runtime_seconds",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})

    metadata = {
        "runs": args.runs,
        "steps": args.steps,
        "workers": best["workers"],
        "logical_processors": os.cpu_count(),
        "max_nodes_per_triangle_component": args.max_nodes,
        "best_edge_count": best["edge_count"],
        "runs_with_71_or_more": sum(1 for row in rows if row["edge_count"] >= 71),
        "interpretation": (
            "Heuristic search under exact necessary filters. A 71+ result would "
            "need continuous geometry checking; absence of 71+ is evidence, not "
            "a universal proof."
        ),
    }
    (OUTDIR / "triangle_filtered_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--runs", type=int, default=120)
    parser.add_argument("--steps", type=int, default=180)
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    tasks = [
        (args.n, args.seed + 7919 * i, args.steps, args.max_nodes)
        for i in range(args.runs)
    ]
    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks))
    start = time.time()
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            if len(rows) == 1 or row["edge_count"] >= max(r["edge_count"] for r in rows):
                print(
                    f"new best/seen {len(rows)}/{len(tasks)}: "
                    f"{row['edge_count']} edges seed={row['seed']}",
                    flush=True,
                )

    rows.sort(key=lambda row: row["edge_count"], reverse=True)
    best = rows[0]
    best["workers"] = actual_workers
    best["total_wall_seconds"] = round(time.time() - start, 3)
    write_outputs(best, rows, args)
    print(
        json.dumps(
            {
                "best_edge_count": best["edge_count"],
                "runs_with_71_or_more": sum(1 for row in rows if row["edge_count"] >= 71),
                "workers": actual_workers,
                "total_wall_seconds": best["total_wall_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
