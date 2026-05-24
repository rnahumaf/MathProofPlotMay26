#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Numerical unit-distance embedder with an explicit anti-collision penalty."""

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
OUTDIR = ROOT / "n25_global_proof_search" / "distinct_geometric_embedder"

Edge = tuple[int, int]


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def infer_n(edges: list[Edge]) -> int:
    return max(max(i, j) for i, j in edges) + 1


def decode(values: np.ndarray, n: int, fixed_edge: Edge) -> np.ndarray:
    coords = np.zeros((n, 2), dtype=float)
    a, b = fixed_edge
    coords[a] = [0.0, 0.0]
    coords[b] = [1.0, 0.0]
    cursor = 0
    for idx in range(n):
        if idx in fixed_edge:
            continue
        coords[idx] = [values[cursor], values[cursor + 1]]
        cursor += 2
    return coords


def initial_values(n: int, fixed_edge: Edge, rng: random.Random, scale: float) -> np.ndarray:
    values = []
    for idx in range(n):
        if idx in fixed_edge:
            continue
        angle = rng.random() * 2 * math.pi
        radius = scale * math.sqrt(rng.random())
        values.extend([radius * math.cos(angle), radius * math.sin(angle)])
    return np.array(values, dtype=float)


def residuals(
    values: np.ndarray,
    n: int,
    edges: list[Edge],
    fixed_edge: Edge,
    min_separation: float,
    collision_weight: float,
) -> np.ndarray:
    coords = decode(values, n, fixed_edge)
    out = []
    for i, j in edges:
        dx = coords[i, 0] - coords[j, 0]
        dy = coords[i, 1] - coords[j, 1]
        out.append(dx * dx + dy * dy - 1.0)

    sep2 = min_separation * min_separation
    for i in range(n):
        for j in range(i + 1, n):
            dx = coords[i, 0] - coords[j, 0]
            dy = coords[i, 1] - coords[j, 1]
            d2 = dx * dx + dy * dy
            out.append(collision_weight * max(0.0, sep2 - d2))
    return np.array(out, dtype=float)


def distance_diagnostics(coords: np.ndarray) -> dict:
    min_distance = float("inf")
    collision_pairs = 0
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            distance = float(np.linalg.norm(coords[i] - coords[j]))
            min_distance = min(min_distance, distance)
            if distance <= 1e-6:
                collision_pairs += 1
    return {
        "min_pair_distance": min_distance,
        "collision_pairs_at_1e-6": collision_pairs,
        "has_distinct_points_at_1e-6": collision_pairs == 0,
    }


def edge_errors(coords: np.ndarray, edges: list[Edge]) -> tuple[float, float]:
    errors = []
    for i, j in edges:
        delta = coords[i] - coords[j]
        errors.append(float(delta @ delta - 1.0))
    arr = np.array(errors, dtype=float)
    return float(np.max(np.abs(arr))), float(math.sqrt(np.mean(arr * arr)))


def worker(task: tuple[int, list[Edge], int, int, float, float, float, float]) -> dict:
    seed, edges, n, max_nfev, scale, min_separation, collision_weight, loss_f_scale = task
    rng = random.Random(seed)
    fixed_edge = edges[0]
    x0 = initial_values(n, fixed_edge, rng, scale)
    start = time.time()
    result = least_squares(
        residuals,
        x0,
        args=(n, edges, fixed_edge, min_separation, collision_weight),
        method="trf",
        loss="soft_l1",
        f_scale=loss_f_scale,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        max_nfev=max_nfev,
    )
    coords = decode(result.x, n, fixed_edge)
    max_abs, rms = edge_errors(coords, edges)
    diag = distance_diagnostics(coords)
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
        **diag,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=120)
    parser.add_argument("--max-nfev", type=int, default=30000)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--min-separation", type=float, default=0.05)
    parser.add_argument("--collision-weight", type=float, default=20.0)
    parser.add_argument("--loss-f-scale", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    edges = read_edges(args.edges)
    n = infer_n(edges)
    tasks = [
        (
            args.seed + i * 104729,
            edges,
            n,
            args.max_nfev,
            args.scale,
            args.min_separation,
            args.collision_weight,
            args.loss_f_scale,
        )
        for i in range(args.runs)
    ]
    rows = []
    actual_workers = min(args.workers, len(tasks))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            current = min(rows, key=lambda item: (item["max_abs_edge_squared_error"], -item["min_pair_distance"]))
            if row is current:
                print(
                    f"new best/seen {len(rows)}/{len(tasks)}: "
                    f"max_abs={row['max_abs_edge_squared_error']:.3e} "
                    f"min_dist={row['min_pair_distance']:.3e}",
                    flush=True,
                )

    rows.sort(key=lambda item: (item["max_abs_edge_squared_error"], -item["min_pair_distance"]))
    best = rows[0]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", args.edges.stem).strip("_")
    best_out = {key: value for key, value in best.items() if key != "coords"}
    best_out.update(
        {
            "source_edges_csv": str(args.edges),
            "source_edge_count": len(edges),
            "workers": actual_workers,
            "min_separation_requested": args.min_separation,
            "collision_weight": args.collision_weight,
        }
    )
    (OUTDIR / f"{slug}_distinct_best.json").write_text(
        json.dumps(best_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / f"{slug}_distinct_best_coords.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "x", "y"])
        for index, (x, y) in enumerate(best["coords"], 1):
            writer.writerow([index, f"{x:.12f}", f"{y:.12f}"])
    print(json.dumps(best_out, indent=2))


if __name__ == "__main__":
    main()
