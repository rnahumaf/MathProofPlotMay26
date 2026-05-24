#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit dense subcores for collision-only unit-distance embeddings.

This is a proof-search tool. It looks for small induced subgraphs where the
edge equations are numerically satisfiable, but every exact-looking sampled
solution collapses at least one pair of vertices. Such a subcore is a strong
target for a later interval or algebraic certificate proving that the graph has
no realization by distinct planar points.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from distinct_geometric_embedder import worker as distinct_worker
from geometric_embedder import worker as exact_worker
from rigid_forced_edge_discovery import dense_subsets, induced_edges, remap_edges, read_edges
from triangle_lattice_filter import normalize_edge

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
OUTDIR = SEARCH_DIR / "collision_forced_subcore_audit"
DEFAULT_EDGES = SEARCH_DIR / "non_trilaterable_maximality" / "non_trilaterable_search_best_edges.csv"

Edge = tuple[int, int]


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def pair_distances(coords: list[list[float]]) -> dict[Edge, float]:
    distances: dict[Edge, float] = {}
    for i, j in itertools.combinations(range(len(coords)), 2):
        dx = coords[i][0] - coords[j][0]
        dy = coords[i][1] - coords[j][1]
        distances[(i, j)] = math.sqrt(dx * dx + dy * dy)
    return distances


def audit_subcore(task: tuple[int, dict, list[Edge], argparse.Namespace]) -> dict:
    subcore_index, subset, full_edges, args = task
    vertices = tuple(subset["vertices"])
    edge_set = set(full_edges)
    original_edges = induced_edges(vertices, edge_set)
    remapped_edges, _, reverse = remap_edges(vertices, original_edges)
    remapped_edges = [normalize_edge(i, j) for i, j in remapped_edges]

    exact_rows = [
        exact_worker(
            (
                args.seed + subcore_index * 1000003 + run * 104729,
                remapped_edges,
                len(vertices),
                args.max_nfev,
                args.scale,
            )
        )
        for run in range(args.exact_runs)
    ]
    exact_solved = [
        row for row in exact_rows if row["max_abs_edge_squared_error"] <= args.exact_tolerance
    ]

    collision_counts: dict[Edge, int] = {}
    min_distances = []
    for row in exact_solved:
        distances = pair_distances(row["coords"])
        min_distances.append(min(distances.values()))
        for pair, distance in distances.items():
            if distance <= args.collision_tolerance:
                collision_counts[pair] = collision_counts.get(pair, 0) + 1

    stable_collision_pairs = [
        {
            "pair": [reverse[i] + 1, reverse[j] + 1],
            "support": count,
            "support_fraction": count / len(exact_solved) if exact_solved else 0.0,
        }
        for (i, j), count in sorted(collision_counts.items(), key=lambda item: (-item[1], item[0]))
        if exact_solved and count / len(exact_solved) >= args.stable_fraction
    ]

    distinct_rows = [
        distinct_worker(
            (
                args.seed + subcore_index * 1000003 + 500000 + run * 104729,
                remapped_edges,
                len(vertices),
                args.max_nfev,
                args.scale,
                args.min_separation,
                args.collision_weight,
                args.loss_f_scale,
            )
        )
        for run in range(args.distinct_runs)
    ]
    distinct_best = min(
        distinct_rows,
        key=lambda row: (row["max_abs_edge_squared_error"], -row["min_pair_distance"]),
    )

    return {
        "subcore_index": subcore_index,
        "vertices": [vertex + 1 for vertex in vertices],
        "size": len(vertices),
        "edge_count": len(original_edges),
        "surplus": len(original_edges) - (2 * len(vertices) - 3),
        "exact_runs": args.exact_runs,
        "exact_solved_count": len(exact_solved),
        "exact_best_max_abs": min(row["max_abs_edge_squared_error"] for row in exact_rows),
        "exact_min_pair_distance_best": min(min_distances) if min_distances else None,
        "exact_median_min_pair_distance": sorted(min_distances)[len(min_distances) // 2]
        if min_distances
        else None,
        "stable_collision_pair_count": len(stable_collision_pairs),
        "stable_collision_pairs": stable_collision_pairs[:20],
        "distinct_runs": args.distinct_runs,
        "distinct_best_max_abs": distinct_best["max_abs_edge_squared_error"],
        "distinct_best_rms": distinct_best["rms_edge_squared_error"],
        "distinct_best_min_pair_distance": distinct_best["min_pair_distance"],
        "remapped_edges": [[i + 1, j + 1] for i, j in sorted(remapped_edges)],
        "original_edges": [[i + 1, j + 1] for i, j in sorted(original_edges)],
        "mapping": {str(new + 1): old + 1 for new, old in reverse.items()},
    }


def write_target_edges(result: dict) -> None:
    path = OUTDIR / f"target_subcore_{result['subcore_index']:03d}_edges.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j"])
        writer.writerows(result["remapped_edges"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--min-size", type=int, default=10)
    parser.add_argument("--max-size", type=int, default=12)
    parser.add_argument("--subset-limit", type=int, default=24)
    parser.add_argument("--exact-runs", type=int, default=40)
    parser.add_argument("--distinct-runs", type=int, default=40)
    parser.add_argument("--max-nfev", type=int, default=25000)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--exact-tolerance", type=float, default=1e-8)
    parser.add_argument("--collision-tolerance", type=float, default=1e-6)
    parser.add_argument("--stable-fraction", type=float, default=0.95)
    parser.add_argument("--min-separation", type=float, default=0.05)
    parser.add_argument("--collision-weight", type=float, default=20.0)
    parser.add_argument("--loss-f-scale", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    full_edges = read_edges(args.edges)
    n = max(max(i, j) for i, j in full_edges) + 1
    subsets = dense_subsets(n, set(full_edges), args.min_size, args.max_size, args.subset_limit)
    tasks = [(index + 1, subset, full_edges, args) for index, subset in enumerate(subsets)]

    results: list[dict] = []
    actual_workers = min(args.workers, len(tasks))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(audit_subcore, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                "subcore "
                f"{result['subcore_index']}: "
                f"exact_solved={result['exact_solved_count']} "
                f"stable_collisions={result['stable_collision_pair_count']} "
                f"distinct_best={result['distinct_best_max_abs']:.3e}",
                flush=True,
            )

    results.sort(
        key=lambda row: (
            -row["stable_collision_pair_count"],
            row["distinct_best_max_abs"],
            -row["edge_count"],
        )
    )
    for result in results[:5]:
        write_target_edges(result)

    (OUTDIR / "subcore_collision_details.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (OUTDIR / "subcore_collision_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "rank",
            "subcore_index",
            "size",
            "edge_count",
            "surplus",
            "exact_solved_count",
            "exact_best_max_abs",
            "exact_median_min_pair_distance",
            "stable_collision_pair_count",
            "distinct_best_max_abs",
            "distinct_best_min_pair_distance",
            "vertices",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, result in enumerate(results, 1):
            writer.writerow(
                {
                    "rank": rank,
                    "subcore_index": result["subcore_index"],
                    "size": result["size"],
                    "edge_count": result["edge_count"],
                    "surplus": result["surplus"],
                    "exact_solved_count": result["exact_solved_count"],
                    "exact_best_max_abs": result["exact_best_max_abs"],
                    "exact_median_min_pair_distance": result["exact_median_min_pair_distance"],
                    "stable_collision_pair_count": result["stable_collision_pair_count"],
                    "distinct_best_max_abs": result["distinct_best_max_abs"],
                    "distinct_best_min_pair_distance": result["distinct_best_min_pair_distance"],
                    "vertices": " ".join(map(str, result["vertices"])),
                }
            )

    metadata = {
        "source_edges": str(args.edges),
        "subsets_tested": len(results),
        "workers": actual_workers,
        "top_target_edge_files": [
            str(OUTDIR / f"target_subcore_{result['subcore_index']:03d}_edges.csv")
            for result in results[:5]
        ],
        "interpretation": (
            "Numerical proof-search output. Stable collision pairs are not a proof; "
            "they identify small subcores that should be attacked next by interval "
            "or algebraic distinctness certificates."
        ),
    }
    (OUTDIR / "collision_forced_subcore_audit_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
