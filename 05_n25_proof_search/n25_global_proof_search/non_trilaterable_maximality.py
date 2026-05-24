#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maximality and search for non-trilaterable candidates.

The known 70-edge UCCS graph is not handled by finite trilateration. This
script checks whether it is locally maximal inside the current exact necessary
filters while remaining non-trilaterable. It also provides a heuristic search
for denser non-trilaterable graphs passing those filters.
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

from basic_relaxation_search import add_edge, edge_count, has_edge, remove_edge, validate
from triangle_filtered_search import can_add_strong, triangle_consistent
from triangle_lattice_filter import Edge, analyze_edges, normalize_edge
from trilateration_eliminator import adjacency, choose_order

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "non_trilaterable_maximality"
DEFAULT_BASE = ROOT.parent / "03_uccs_exploration" / "uccs_square_stat_runs" / "n25_e70_seed20270530_edges.csv"


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def adj_from_edges(n: int, edges: list[Edge]) -> list[int]:
    adj = [0] * n
    for i, j in edges:
        add_edge(adj, i, j)
    return adj


def adj_to_edges(adj: list[int]) -> list[Edge]:
    n = len(adj)
    return [
        normalize_edge(i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if has_edge(adj, i, j)
    ]


def all_pairs(n: int) -> list[Edge]:
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def has_trilateration_order(adj: list[int]) -> bool:
    edges = adj_to_edges(adj)
    if not edges:
        return False
    set_adj = adjacency(len(adj), edges)
    return any(choose_order(set_adj, edge) is not None for edge in edges)


def local_failure_reason(adj: list[int]) -> str:
    check = validate(adj, require_local_circle=True)
    if check["valid"]:
        return ""
    return "; ".join(check["violations"][:3])


def classify_added_edge(adj: list[int], edge: Edge, max_nodes: int) -> dict:
    i, j = edge
    if has_edge(adj, i, j):
        return {"i": i + 1, "j": j + 1, "status": "already_edge"}

    add_edge(adj, i, j)
    edge_total = edge_count(adj)
    local = validate(adj, require_local_circle=True)
    if not local["valid"]:
        remove_edge(adj, i, j)
        return {
            "i": i + 1,
            "j": j + 1,
            "status": "blocked_local",
            "edge_count_after_add": edge_total,
            "reason": "; ".join(local["violations"][:5]),
        }

    tri = analyze_edges(adj_to_edges(adj), "candidate", edge_total, len(adj), max_nodes)
    if tri["eliminated"]:
        remove_edge(adj, i, j)
        return {
            "i": i + 1,
            "j": j + 1,
            "status": "blocked_triangle_lattice",
            "edge_count_after_add": edge_total,
            "reason": tri["failure_reason"],
            "failure_component": tri["failure_component"],
        }

    trilat = has_trilateration_order(adj)
    remove_edge(adj, i, j)
    return {
        "i": i + 1,
        "j": j + 1,
        "status": "forces_trilateration" if trilat else "survives_non_trilaterable",
        "edge_count_after_add": edge_total,
    }


def maximality_certificate(edges_path: Path, n: int, max_nodes: int) -> dict:
    edges = read_edges(edges_path)
    adj = adj_from_edges(n, edges)
    local = validate(adj, require_local_circle=True)
    tri = analyze_edges(adj_to_edges(adj), edges_path.stem, edge_count(adj), n, max_nodes)
    trilat = has_trilateration_order(adj)
    rows = [
        classify_added_edge(adj, edge, max_nodes)
        for edge in all_pairs(n)
        if not has_edge(adj, *edge)
    ]
    status_counts = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in sorted({row["status"] for row in rows})
    }
    return {
        "source_edges": str(edges_path),
        "n": n,
        "edge_count": edge_count(adj),
        "local_valid": local["valid"],
        "triangle_lattice_valid": not tri["eliminated"],
        "has_trilateration_order": trilat,
        "nonedge_count": len(rows),
        "status_counts": status_counts,
        "maximal_non_trilaterable_under_filters": (
            local["valid"]
            and not tri["eliminated"]
            and not trilat
            and not any(row["status"] == "survives_non_trilaterable" for row in rows)
        ),
        "edge_addition_checks": rows,
    }


def greedy_refill_non_trilaterable(adj: list[int], rng: random.Random, max_nodes: int) -> list[int]:
    pairs = all_pairs(len(adj))
    changed = True
    while changed:
        changed = False
        rng.shuffle(pairs)
        for edge in pairs:
            i, j = edge
            if has_edge(adj, i, j):
                continue
            if not can_add_strong(adj, i, j, max_nodes):
                continue
            add_edge(adj, i, j)
            if has_trilateration_order(adj):
                remove_edge(adj, i, j)
            else:
                changed = True
    return adj


def improve_non_trilaterable(adj: list[int], rng: random.Random, steps: int, max_nodes: int) -> list[int]:
    pairs = all_pairs(len(adj))
    best = adj[:]
    best_edges = edge_count(best)

    for _ in range(steps):
        current_edges = [edge for edge in pairs if has_edge(adj, *edge)]
        if not current_edges:
            break
        removed = rng.sample(current_edges, min(len(current_edges), rng.choice([1, 1, 2, 2, 3])))
        for i, j in removed:
            remove_edge(adj, i, j)
        adj = greedy_refill_non_trilaterable(adj, rng, max_nodes)
        e = edge_count(adj)
        if e >= best_edges:
            best = adj[:]
            best_edges = e
        elif rng.random() < 0.05:
            continue
        else:
            adj = best[:]
    return best


def search_worker(task: tuple[int, list[Edge], int, int, int]) -> dict:
    seed, base_edges, n, steps, max_nodes = task
    rng = random.Random(seed)
    start = time.time()
    adj = adj_from_edges(n, base_edges)
    # Randomly perturb the known non-trilaterable graph, then refill under the
    # non-trilaterable constraint.
    current_edges = adj_to_edges(adj)
    for i, j in rng.sample(current_edges, min(len(current_edges), rng.choice([0, 1, 2, 3, 4]))):
        remove_edge(adj, i, j)
    adj = greedy_refill_non_trilaterable(adj, rng, max_nodes)
    adj = improve_non_trilaterable(adj, rng, steps, max_nodes)
    local = validate(adj, require_local_circle=True)
    tri = analyze_edges(adj_to_edges(adj), "candidate", edge_count(adj), n, max_nodes)
    return {
        "seed": seed,
        "edge_count": edge_count(adj),
        "local_valid": local["valid"],
        "triangle_lattice_valid": not tri["eliminated"],
        "has_trilateration_order": has_trilateration_order(adj),
        "runtime_seconds": round(time.time() - start, 3),
        "edges": [[i + 1, j + 1] for i, j in adj_to_edges(adj)],
    }


def write_search_outputs(best: dict, rows: list[dict], args: argparse.Namespace) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "non_trilaterable_search_best.json").write_text(
        json.dumps(best, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / "non_trilaterable_search_best_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j"])
        writer.writerows(best["edges"])
    with (OUTDIR / "non_trilaterable_search_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "edge_count",
            "local_valid",
            "triangle_lattice_valid",
            "has_trilateration_order",
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
        "best_edge_count": best["edge_count"],
        "runs_over_70": sum(1 for row in rows if row["edge_count"] > 70),
        "interpretation": "Heuristic search for denser graphs that pass exact filters but avoid trilateration.",
    }
    (OUTDIR / "non_trilaterable_search_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_search(args: argparse.Namespace) -> None:
    base_edges = read_edges(args.edges)
    tasks = [
        (args.seed + 7919 * i, base_edges, args.n, args.steps, args.max_nodes)
        for i in range(args.runs)
    ]
    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(search_worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            if len(rows) == 1 or row["edge_count"] >= max(r["edge_count"] for r in rows):
                print(f"new best/seen {len(rows)}/{len(tasks)}: {row['edge_count']} seed={row['seed']}", flush=True)
    rows.sort(key=lambda row: row["edge_count"], reverse=True)
    best = rows[0]
    best["workers"] = actual_workers
    write_search_outputs(best, rows, args)
    print(json.dumps({"best_edge_count": best["edge_count"], "runs_over_70": sum(1 for row in rows if row["edge_count"] > 70)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--runs", type=int, default=500)
    parser.add_argument("--steps", type=int, default=180)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.search:
        run_search(args)
        return

    cert = maximality_certificate(args.edges, args.n, args.max_nodes)
    (OUTDIR / "uccs_e70_non_trilaterable_maximality.json").write_text(
        json.dumps(cert, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / "uccs_e70_edge_addition_checks.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["i", "j", "status", "edge_count_after_add", "reason", "failure_component"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in cert["edge_addition_checks"]:
            writer.writerow(row)
    print(json.dumps({key: cert[key] for key in ["edge_count", "nonedge_count", "status_counts", "maximal_non_trilaterable_under_filters"]}, indent=2))


if __name__ == "__main__":
    main()
