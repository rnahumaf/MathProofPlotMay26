#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Numerical geometric embeddability test for dense abstract candidate graphs.

Given an edge list, try to find planar coordinates p_i such that every listed
edge has Euclidean length exactly 1. Nonedges are unconstrained; therefore a
successful embedding with E edges would be a genuine point set with at least E
unit-distance pairs.

Failure is not a proof. This script is a filter that separates likely
non-embeddable abstract graphs from real geometric counterexamples.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search"
DEFAULT_EDGES = OUTDIR / "local_circle_relaxation_heuristic_best_edges.csv"


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def read_edges(path: Path) -> list[tuple[int, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def infer_n(edges: list[tuple[int, int]]) -> int:
    return max(max(i, j) for i, j in edges) + 1


def decode_variables(values: np.ndarray, n: int, fixed_edge: tuple[int, int]) -> np.ndarray:
    coords = np.zeros((n, 2), dtype=float)
    a, b = fixed_edge
    coords[a] = [0.0, 0.0]
    coords[b] = [1.0, 0.0]
    cursor = 0
    for idx in range(n):
        if idx in fixed_edge:
            continue
        coords[idx, 0] = values[cursor]
        coords[idx, 1] = values[cursor + 1]
        cursor += 2
    return coords


def residuals(values: np.ndarray, n: int, edges: list[tuple[int, int]], fixed_edge: tuple[int, int]) -> np.ndarray:
    coords = decode_variables(values, n, fixed_edge)
    out = np.empty(len(edges), dtype=float)
    for index, (i, j) in enumerate(edges):
        dx = coords[i, 0] - coords[j, 0]
        dy = coords[i, 1] - coords[j, 1]
        out[index] = dx * dx + dy * dy - 1.0
    return out


def initial_values(n: int, fixed_edge: tuple[int, int], rng: random.Random, scale: float) -> np.ndarray:
    values: list[float] = []
    for idx in range(n):
        if idx in fixed_edge:
            continue
        angle = rng.random() * 2.0 * math.pi
        radius = scale * math.sqrt(rng.random())
        values.extend([radius * math.cos(angle), radius * math.sin(angle)])
    return np.array(values, dtype=float)


def worker(task: tuple[int, list[tuple[int, int]], int, int, float]) -> dict:
    seed, edges, n, max_nfev, scale = task
    rng = random.Random(seed)
    fixed_edge = edges[0]
    x0 = initial_values(n, fixed_edge, rng, scale)
    start = time.time()
    result = least_squares(
        residuals,
        x0,
        args=(n, edges, fixed_edge),
        method="trf",
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        max_nfev=max_nfev,
    )
    r = residuals(result.x, n, edges, fixed_edge)
    max_abs = float(np.max(np.abs(r)))
    rms = float(math.sqrt(np.mean(r * r)))
    coords = decode_variables(result.x, n, fixed_edge)
    return {
        "seed": seed,
        "success": bool(result.success),
        "status": int(result.status),
        "cost": float(result.cost),
        "max_abs_edge_squared_error": max_abs,
        "rms_edge_squared_error": rms,
        "nfev": int(result.nfev),
        "runtime_seconds": round(time.time() - start, 3),
        "coords": coords.tolist(),
    }


def count_all_unit_pairs(coords: list[list[float]], tolerance: float = 1e-6) -> int:
    count = 0
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            if abs(dx * dx + dy * dy - 1.0) <= tolerance:
                count += 1
    return count


def distance_diagnostics(coords: list[list[float]], collision_tolerance: float = 1e-6) -> dict:
    min_distance = float("inf")
    collision_pairs = 0
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            distance = math.hypot(dx, dy)
            min_distance = min(min_distance, distance)
            if distance <= collision_tolerance:
                collision_pairs += 1
    return {
        "min_pair_distance": min_distance,
        "collision_pairs_at_1e-6": collision_pairs,
        "has_25_distinct_points_at_1e-6": collision_pairs == 0,
    }


def write_outputs(best: dict, rows: list[dict], edges_path: Path, edge_count: int) -> None:
    OUTDIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", edges_path.stem).strip("_") or "candidate"
    best_out = {
        key: value
        for key, value in best.items()
        if key != "coords"
    }
    best_out["source_edges_csv"] = str(edges_path)
    best_out["source_edge_count"] = edge_count
    best_out["all_unit_pairs_at_1e-6"] = count_all_unit_pairs(best["coords"], tolerance=1e-6)
    best_out.update(distance_diagnostics(best["coords"], collision_tolerance=1e-6))
    best_out["interpretation"] = (
        "A near-zero max_abs_edge_squared_error would be a real geometric counterexample. "
        "It must also have has_25_distinct_points_at_1e-6=true. "
        "A positive residual is only numerical evidence of non-embeddability, not a proof."
    )
    (OUTDIR / f"geometric_embedder_{slug}_best.json").write_text(
        json.dumps(best_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (OUTDIR / f"geometric_embedder_{slug}_best_coords.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "x", "y"])
        for index, (x, y) in enumerate(best["coords"], 1):
            writer.writerow([index, f"{x:.12f}", f"{y:.12f}"])

    with (OUTDIR / f"geometric_embedder_{slug}_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "seed",
                "success",
                "status",
                "cost",
                "max_abs_edge_squared_error",
                "rms_edge_squared_error",
                "nfev",
                "runtime_seconds",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--runs", type=int, default=240)
    parser.add_argument("--max-nfev", type=int, default=30000)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    edges = read_edges(args.edges)
    n = infer_n(edges)
    tasks = [(args.seed + 104729 * i, edges, n, args.max_nfev, args.scale) for i in range(args.runs)]
    actual_workers = min(args.workers, len(tasks))

    rows: list[dict] = []
    start = time.time()
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            best_so_far = min(rows, key=lambda r: r["max_abs_edge_squared_error"])
            if row is best_so_far:
                print(
                    f"new best/seen {len(rows)}/{len(tasks)}: "
                    f"max_abs={row['max_abs_edge_squared_error']:.3e} "
                    f"rms={row['rms_edge_squared_error']:.3e} seed={row['seed']}",
                    flush=True,
                )

    rows.sort(key=lambda row: row["max_abs_edge_squared_error"])
    best = rows[0]
    best["total_wall_seconds"] = round(time.time() - start, 3)
    best["workers"] = actual_workers
    write_outputs(best, rows, args.edges, len(edges))
    print(json.dumps({key: best[key] for key in ["max_abs_edge_squared_error", "rms_edge_squared_error", "seed", "workers", "total_wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
