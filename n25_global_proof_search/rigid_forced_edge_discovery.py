#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discover numerically forced unit edges from small rigid-looking subcores.

This is a guide for proof search, not a proof by itself. For dense induced
subgraphs, it samples many exact-edge embeddings. If a nonedge has essentially
the same squared distance across all sampled embeddings, it is recorded as a
candidate forced distance. Candidate forced unit edges are then added to the
full graph and checked by the existing exact filters.
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

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
OUTDIR = SEARCH_DIR / "rigid_forced_edge_discovery"
DEFAULT_EDGES = SEARCH_DIR / "non_trilaterable_maximality" / "non_trilaterable_search_best_edges.csv"

from geometric_embedder import worker as embed_worker
from triangle_lattice_filter import analyze_edges, normalize_edge
from trilateration_eliminator import analyze_one as trilateration_analyze

Edge = tuple[int, int]


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def induced_edges(vertices: tuple[int, ...], edge_set: set[Edge]) -> list[Edge]:
    vset = set(vertices)
    return [edge for edge in edge_set if edge[0] in vset and edge[1] in vset]


def remap_edges(vertices: tuple[int, ...], edges: list[Edge]) -> tuple[list[Edge], dict[int, int], dict[int, int]]:
    mapping = {old: new for new, old in enumerate(vertices)}
    reverse = {new: old for old, new in mapping.items()}
    return [(mapping[i], mapping[j]) for i, j in edges], mapping, reverse


def dense_subsets(n: int, edge_set: set[Edge], min_size: int, max_size: int, limit: int) -> list[dict]:
    candidates: list[dict] = []
    for size in range(min_size, max_size + 1):
        for vertices in itertools.combinations(range(n), size):
            edges = induced_edges(vertices, edge_set)
            if len(edges) < 2 * size - 3:
                continue
            candidates.append(
                {
                    "vertices": vertices,
                    "edge_count": len(edges),
                    "size": size,
                    "surplus": len(edges) - (2 * size - 3),
                }
            )
    candidates.sort(key=lambda row: (-row["surplus"], -row["edge_count"], row["size"], row["vertices"]))
    return candidates[:limit]


def sample_subcore(
    vertices: tuple[int, ...],
    edges: list[Edge],
    runs: int,
    max_nfev: int,
    seed: int,
    scale: float,
    stable_tolerance: float,
    unit_tolerance: float,
    min_pair_distance: float,
) -> dict:
    remapped, _, reverse = remap_edges(vertices, edges)
    rows = [
        embed_worker((seed + i * 104729, remapped, len(vertices), max_nfev, scale))
        for i in range(runs)
    ]
    solved = []
    rejected_collapsed = 0
    for row in rows:
        if row["max_abs_edge_squared_error"] > 1e-8:
            continue
        coords = row["coords"]
        min_distance = float("inf")
        for i, j in itertools.combinations(range(len(coords)), 2):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            min_distance = min(min_distance, math.sqrt(dx * dx + dy * dy))
        if min_distance < min_pair_distance:
            rejected_collapsed += 1
            continue
        row["min_pair_distance"] = min_distance
        solved.append(row)
    forced: list[dict] = []
    if len(solved) >= max(3, runs // 4):
        remapped_edge_set = {normalize_edge(i, j) for i, j in remapped}
        for a, b in itertools.combinations(range(len(vertices)), 2):
            if normalize_edge(a, b) in remapped_edge_set:
                continue
            values = []
            for row in solved:
                coords = row["coords"]
                dx = coords[a][0] - coords[b][0]
                dy = coords[a][1] - coords[b][1]
                values.append(dx * dx + dy * dy)
            spread = max(values) - min(values)
            mean = sum(values) / len(values)
            if spread <= stable_tolerance and abs(mean - 1.0) <= unit_tolerance:
                forced.append(
                    {
                        "pair": [reverse[a] + 1, reverse[b] + 1],
                        "mean_squared_distance": mean,
                        "spread": spread,
                        "sample_count": len(solved),
                    }
                )
    return {
        "vertices": [v + 1 for v in vertices],
        "edge_count": len(edges),
        "runs": runs,
        "solved_count": len(solved),
        "rejected_collapsed_count": rejected_collapsed,
        "best_max_abs": min(row["max_abs_edge_squared_error"] for row in rows),
        "forced_unit_candidates": forced,
    }


def augmented_check(full_edges: list[Edge], forced_pair: list[int], precision: int, tolerance: str) -> dict:
    pair = normalize_edge(forced_pair[0] - 1, forced_pair[1] - 1)
    augmented = sorted(set(full_edges).union({pair}))
    tri = analyze_edges(augmented, f"augmented_{forced_pair[0]}_{forced_pair[1]}", len(augmented), 25, 100000)
    trilat = trilateration_analyze(
        f"augmented_{forced_pair[0]}_{forced_pair[1]}",
        augmented,
        max_states=200000,
        tolerance_text=tolerance,
        precision=precision,
    )
    return {
        "forced_pair": forced_pair,
        "augmented_edge_count": len(augmented),
        "triangle_lattice_eliminated": tri["eliminated"],
        "triangle_lattice_failure": tri["failure_reason"],
        "trilateration_status": trilat["status"],
        "trilateration_eliminated_at_step": trilat.get("eliminated_at_step", ""),
        "trilateration_max_width": trilat.get("max_width", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--min-size", type=int, default=8)
    parser.add_argument("--max-size", type=int, default=12)
    parser.add_argument("--subset-limit", type=int, default=80)
    parser.add_argument("--runs-per-subcore", type=int, default=60)
    parser.add_argument("--max-nfev", type=int, default=30000)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--stable-tolerance", type=float, default=1e-8)
    parser.add_argument("--unit-tolerance", type=float, default=1e-7)
    parser.add_argument("--min-pair-distance", type=float, default=1e-6)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    full_edges = read_edges(args.edges)
    edge_set = set(full_edges)
    n = max(max(edge) for edge in full_edges) + 1
    subsets = dense_subsets(n, edge_set, args.min_size, args.max_size, args.subset_limit)

    tasks = []
    for index, item in enumerate(subsets):
        vertices = tuple(item["vertices"])
        edges = induced_edges(vertices, edge_set)
        tasks.append(
            (
                vertices,
                edges,
                args.runs_per_subcore,
                args.max_nfev,
                args.seed + index * 1000003,
                args.scale,
                args.stable_tolerance,
                args.unit_tolerance,
                args.min_pair_distance,
            )
        )

    results: list[dict] = []
    actual_workers = min(args.workers, len(tasks)) if tasks else 1
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(sample_subcore, *task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            results.append(row)
            if row["forced_unit_candidates"]:
                print(
                    f"forced candidates in {row['vertices']}: {row['forced_unit_candidates']}",
                    flush=True,
                )

    forced_by_pair: dict[tuple[int, int], dict] = {}
    for row in results:
        for forced in row["forced_unit_candidates"]:
            pair = tuple(forced["pair"])
            current = forced_by_pair.get(pair)
            if current is None or forced["spread"] < current["forced"]["spread"]:
                forced_by_pair[pair] = {"witness": row, "forced": forced}

    augmented = [
        {
            **item,
            "augmented_check": augmented_check(full_edges, list(pair), precision=100, tolerance="1e-40"),
        }
        for pair, item in sorted(forced_by_pair.items())
    ]

    (OUTDIR / "forced_edge_discovery_details.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTDIR / "forced_edge_candidates.json").write_text(
        json.dumps(augmented, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / "forced_edge_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "i",
            "j",
            "mean_squared_distance",
            "spread",
            "witness_vertices",
            "witness_edge_count",
            "triangle_lattice_eliminated",
            "trilateration_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in augmented:
            pair = item["forced"]["pair"]
            writer.writerow(
                {
                    "i": pair[0],
                    "j": pair[1],
                    "mean_squared_distance": item["forced"]["mean_squared_distance"],
                    "spread": item["forced"]["spread"],
                    "witness_vertices": " ".join(map(str, item["witness"]["vertices"])),
                    "witness_edge_count": item["witness"]["edge_count"],
                    "triangle_lattice_eliminated": item["augmented_check"]["triangle_lattice_eliminated"],
                    "trilateration_status": item["augmented_check"]["trilateration_status"],
                }
            )

    metadata = {
        "source_edges": str(args.edges),
        "subsets_tested": len(results),
        "forced_unit_candidate_count": len(augmented),
        "min_pair_distance": args.min_pair_distance,
        "collapsed_embedding_rejections": sum(
            item.get("rejected_collapsed_count", 0) for item in results
        ),
        "workers": actual_workers,
        "interpretation": (
            "Numerical discovery only, using non-collapsed sampled embeddings. "
            "A forced edge becomes rigorous only after the witness subcore is "
            "certified algebraically or by intervals."
        ),
    }
    (OUTDIR / "forced_edge_discovery_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
