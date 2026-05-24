#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finite trilateration eliminator for unit-distance candidate graphs.

If a graph admits an ordering where, after fixing one seed edge, every remaining
vertex has at least two already placed neighbors, all embeddings are obtained by
successive intersections of two unit circles. This script enumerates that finite
search tree with high-precision arithmetic and emits an independently
checkable certificate when every branch is eliminated.

This is not a complete method for all graphs. If no two-neighbor ordering covers
all vertices, the script reports that the graph needs a different eliminator.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import mpmath as mp

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
DEFAULT_POOL = SEARCH_DIR / "triangle_filtered_pool"
OUTDIR = SEARCH_DIR / "trilateration_eliminator"

Edge = tuple[int, int]
Point = tuple[mp.mpf, mp.mpf]


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def read_edges_path(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def read_class_summary(pool: Path) -> list[dict]:
    with (pool / "candidate_classes.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (-int(row["edge_count"]), int(row["class_id"])))
    return rows


def read_pool_edges(pool: Path, class_id: int, edge_count: int) -> list[Edge]:
    return read_edges_path(pool / f"class_{class_id:04d}_e{edge_count}_edges.csv")


def infer_n(edges: list[Edge]) -> int:
    return max(max(i, j) for i, j in edges) + 1


def adjacency(n: int, edges: list[Edge]) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def choose_order(adj: list[set[int]], seed_edge: Edge) -> list[tuple[int, int, int]] | None:
    n = len(adj)
    placed = set(seed_edge)
    order: list[tuple[int, int, int]] = []

    while len(placed) < n:
        candidates: list[tuple[int, int, int, int]] = []
        for vertex in range(n):
            if vertex in placed:
                continue
            anchors = sorted(adj[vertex].intersection(placed))
            if len(anchors) >= 2:
                # Prefer more anchored constraints; the first two are only the
                # construction pair, all anchored neighbors are checked later.
                candidates.append((-len(anchors), vertex, anchors[0], anchors[1]))
        if not candidates:
            return None
        candidates.sort()
        _, vertex, a, b = candidates[0]
        order.append((vertex, a, b))
        placed.add(vertex)
    return order


def squared_distance(a: Point, b: Point) -> mp.mpf:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def circle_intersections(a: Point, b: Point, tolerance: mp.mpf) -> list[Point]:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    d2 = dx * dx + dy * dy
    d = mp.sqrt(d2)
    if d > 2 + tolerance or d < tolerance:
        return []
    midpoint = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    h2 = 1 - d2 / 4
    if h2 < -tolerance:
        return []
    if abs(h2) <= tolerance:
        return [midpoint]
    h = mp.sqrt(max(mp.mpf("0"), h2))
    ux = -dy / d
    uy = dx / d
    return [
        (midpoint[0] + h * ux, midpoint[1] + h * uy),
        (midpoint[0] - h * ux, midpoint[1] - h * uy),
    ]


def point_key(point: Point, digits: int = 80) -> tuple[str, str]:
    return (mp.nstr(point[0], digits), mp.nstr(point[1], digits))


def branch_valid(
    coords: dict[int, Point],
    vertex: int,
    candidate: Point,
    adj: list[set[int]],
    tolerance: mp.mpf,
) -> tuple[bool, str]:
    for neighbor in adj[vertex]:
        if neighbor not in coords:
            continue
        error = abs(squared_distance(candidate, coords[neighbor]) - 1)
        if error > tolerance:
            return False, f"edge_{vertex + 1}_{neighbor + 1}_error_{mp.nstr(error, 12)}"
    for other_vertex, other_point in coords.items():
        if squared_distance(candidate, other_point) <= tolerance * tolerance:
            return False, f"collision_{vertex + 1}_{other_vertex + 1}"
    return True, "ok"


def enumerate_trilateration(
    edges: list[Edge],
    seed_edge: Edge,
    max_states: int,
    tolerance: mp.mpf,
) -> dict:
    n = infer_n(edges)
    adj = adjacency(n, edges)
    order = choose_order(adj, seed_edge)
    if order is None:
        return {
            "status": "no_trilateration_order",
            "seed_edge": [seed_edge[0] + 1, seed_edge[1] + 1],
        }

    states: list[dict[int, Point]] = [
        {
            seed_edge[0]: (mp.mpf("0"), mp.mpf("0")),
            seed_edge[1]: (mp.mpf("1"), mp.mpf("0")),
        }
    ]
    eliminations: list[dict] = []
    max_width = 1

    for step_index, (vertex, a, b) in enumerate(order, 1):
        next_states: dict[tuple[tuple[int, tuple[str, str]], ...], dict[int, Point]] = {}
        step_failures: list[dict] = []
        for state_index, coords in enumerate(states):
            candidates = circle_intersections(coords[a], coords[b], tolerance)
            if not candidates:
                step_failures.append(
                    {
                        "state_index": state_index,
                        "vertex": vertex + 1,
                        "anchors": [a + 1, b + 1],
                        "reason": "anchor_circles_do_not_intersect",
                    }
                )
                continue
            for candidate in candidates:
                ok, reason = branch_valid(coords, vertex, candidate, adj, tolerance)
                if not ok:
                    step_failures.append(
                        {
                            "state_index": state_index,
                            "vertex": vertex + 1,
                            "anchors": [a + 1, b + 1],
                            "candidate": [mp.nstr(candidate[0], 40), mp.nstr(candidate[1], 40)],
                            "reason": reason,
                        }
                    )
                    continue
                new_coords = dict(coords)
                new_coords[vertex] = candidate
                key = tuple(sorted((v, point_key(p, digits=70)) for v, p in new_coords.items()))
                next_states[key] = new_coords

        eliminations.append(
            {
                "step": step_index,
                "vertex": vertex + 1,
                "anchors": [a + 1, b + 1],
                "states_in": len(states),
                "states_out": len(next_states),
                "failures": step_failures[:20],
                "failure_count": len(step_failures),
            }
        )
        states = list(next_states.values())
        max_width = max(max_width, len(states))
        if len(states) > max_states:
            return {
                "status": "state_limit",
                "seed_edge": [seed_edge[0] + 1, seed_edge[1] + 1],
                "order": [[v + 1, a + 1, b + 1] for v, a, b in order],
                "step": step_index,
                "state_count": len(states),
                "max_width": max_width,
            }
        if not states:
            return {
                "status": "eliminated",
                "seed_edge": [seed_edge[0] + 1, seed_edge[1] + 1],
                "order": [[v + 1, a + 1, b + 1] for v, a, b in order],
                "eliminated_at_step": step_index,
                "max_width": max_width,
                "eliminations": eliminations,
            }

    return {
        "status": "survived",
        "seed_edge": [seed_edge[0] + 1, seed_edge[1] + 1],
        "order": [[v + 1, a + 1, b + 1] for v, a, b in order],
        "state_count": len(states),
        "max_width": max_width,
        "note": "Surviving states satisfy all listed edge constraints under the chosen tolerance.",
    }


def try_all_seed_edges(edges: list[Edge], max_states: int, tolerance: mp.mpf) -> dict:
    best_no_order = None
    for seed_edge in edges:
        result = enumerate_trilateration(edges, seed_edge, max_states, tolerance)
        if result["status"] in {"eliminated", "survived", "state_limit"}:
            return result
        best_no_order = result
    return best_no_order or {"status": "empty_edge_set"}


def analyze_one(
    source: str,
    edges: list[Edge],
    max_states: int,
    tolerance_text: str,
    precision: int,
) -> dict:
    mp.mp.dps = precision
    tolerance = mp.mpf(tolerance_text)
    result = try_all_seed_edges(edges, max_states, tolerance)
    result.update(
        {
            "source": source,
            "n": infer_n(edges),
            "edge_count": len(edges),
            "precision_digits": precision,
            "tolerance": tolerance_text,
            "interpretation": (
                "eliminated means all finite trilateration branches from the "
                "reported seed edge failed; survived means a numerically valid "
                "branch remains and needs exact/interval verification."
            ),
        }
    )
    return result


def worker(task: tuple[str, list[Edge], int, str, int]) -> dict:
    return analyze_one(*task)


def write_single(result: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=None)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--classes", type=int, default=20)
    parser.add_argument("--max-states", type=int, default=200000)
    parser.add_argument("--tolerance", default="1e-40")
    parser.add_argument("--precision", type=int, default=100)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.edges is not None:
        edges = read_edges_path(args.edges)
        result = analyze_one(args.edges.stem, edges, args.max_states, args.tolerance, args.precision)
        out_path = OUTDIR / f"{args.edges.stem}_trilateration_certificate.json"
        write_single(result, out_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    class_rows = read_class_summary(args.pool)[: args.classes]
    tasks = []
    for row in class_rows:
        class_id = int(row["class_id"])
        edge_count = int(row["edge_count"])
        edges = read_pool_edges(args.pool, class_id, edge_count)
        source = f"class_{class_id:04d}_e{edge_count}"
        tasks.append((source, edges, args.max_states, args.tolerance, args.precision))

    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks)) if tasks else 1
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            rows.append(result)
            write_single(result, OUTDIR / f"{result['source']}_trilateration_certificate.json")
            print(
                f"{result['source']}: {result['status']} "
                f"max_width={result.get('max_width', '')}",
                flush=True,
            )

    rows.sort(key=lambda row: (row["status"], row["source"]))
    with (OUTDIR / "trilateration_batch_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "source",
            "edge_count",
            "status",
            "seed_edge",
            "eliminated_at_step",
            "state_count",
            "max_width",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    (OUTDIR / "trilateration_batch_details.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata = {
        "classes_tested": len(rows),
        "workers": actual_workers,
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "max_states": args.max_states,
        "precision_digits": args.precision,
        "tolerance": args.tolerance,
    }
    (OUTDIR / "trilateration_batch_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
