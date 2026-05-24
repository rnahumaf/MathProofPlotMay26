#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heuristic search for dense abstract graphs satisfying the basic necessary
conditions for planar unit-distance graphs:

- every pair of vertices has at most two common neighbors (K_{2,3}-free);
- no K4.

Finding a graph with >70 edges here does not disprove the conjecture. It proves
that these basic combinatorial conditions are insufficient, and it produces a
target graph for the next geometric non-embeddability layer.
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

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search"


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def edge_count(adj: list[int]) -> int:
    return sum(mask.bit_count() for mask in adj) // 2


def has_edge(adj: list[int], i: int, j: int) -> bool:
    return bool(adj[i] & (1 << j))


def common_count(adj: list[int], i: int, j: int) -> int:
    return (adj[i] & adj[j]).bit_count()


def can_add(adj: list[int], i: int, j: int) -> bool:
    if i == j or has_edge(adj, i, j):
        return False

    # Adding i-j increases codegree(j,k) for k in N(i), and codegree(i,k) for
    # k in N(j). All codegrees must remain <= 2.
    ni = adj[i]
    while ni:
        bit = ni & -ni
        k = bit.bit_length() - 1
        if k != j and common_count(adj, j, k) >= 2:
            return False
        ni ^= bit

    nj = adj[j]
    while nj:
        bit = nj & -nj
        k = bit.bit_length() - 1
        if k != i and common_count(adj, i, k) >= 2:
            return False
        nj ^= bit

    # Adding i-j creates a K4 exactly when two common neighbors of i and j are
    # already adjacent.
    common = adj[i] & adj[j]
    scan = common
    while scan:
        bit = scan & -scan
        a = bit.bit_length() - 1
        if adj[a] & (common ^ (1 << a)):
            return False
        scan ^= bit

    return True


def local_circle_valid_at(adj: list[int], v: int) -> bool:
    """Check the unit-circle restriction inside the neighborhood of v."""

    neighbors = [u for u in range(len(adj)) if has_edge(adj, v, u)]
    neighbor_mask = 0
    for u in neighbors:
        neighbor_mask |= 1 << u

    local_degree: dict[int, int] = {}
    for u in neighbors:
        local_degree[u] = (adj[u] & neighbor_mask).bit_count()
        if local_degree[u] > 2:
            return False

    seen = 0
    for start in neighbors:
        if seen & (1 << start):
            continue
        stack = [start]
        seen |= 1 << start
        component: list[int] = []
        while stack:
            u = stack.pop()
            component.append(u)
            linked = adj[u] & neighbor_mask
            while linked:
                bit = linked & -linked
                w = bit.bit_length() - 1
                if not (seen & bit):
                    seen |= bit
                    stack.append(w)
                linked ^= bit

        if component and all(local_degree[u] == 2 for u in component) and len(component) != 6:
            return False
    return True


def local_circle_valid(adj: list[int]) -> bool:
    return all(local_circle_valid_at(adj, v) for v in range(len(adj)))


def can_add_with_local_circle(adj: list[int], i: int, j: int) -> bool:
    if not can_add(adj, i, j):
        return False
    add_edge(adj, i, j)
    ok = local_circle_valid(adj)
    remove_edge(adj, i, j)
    return ok


def add_edge(adj: list[int], i: int, j: int) -> None:
    adj[i] |= 1 << j
    adj[j] |= 1 << i


def remove_edge(adj: list[int], i: int, j: int) -> None:
    adj[i] &= ~(1 << j)
    adj[j] &= ~(1 << i)


def validate(adj: list[int], require_local_circle: bool = False) -> dict:
    n = len(adj)
    violations: list[str] = []
    for i in range(n):
        for j in range(i + 1, n):
            c = common_count(adj, i, j)
            if c > 2:
                violations.append(f"codegree({i + 1},{j + 1})={c}")

    for a in range(n):
        for b in range(a + 1, n):
            if not has_edge(adj, a, b):
                continue
            for c in range(b + 1, n):
                if not has_edge(adj, a, c) or not has_edge(adj, b, c):
                    continue
                for d in range(c + 1, n):
                    if (
                        has_edge(adj, a, d)
                        and has_edge(adj, b, d)
                        and has_edge(adj, c, d)
                    ):
                        violations.append(f"K4({a + 1},{b + 1},{c + 1},{d + 1})")

    if require_local_circle:
        for v in range(n):
            if not local_circle_valid_at(adj, v):
                violations.append(f"local_circle({v + 1})")

    return {
        "edge_count": edge_count(adj),
        "valid": not violations,
        "violations": violations[:20],
    }


def greedy_fill(n: int, rng: random.Random, require_local_circle: bool = False) -> list[int]:
    adj = [0] * n
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    add_ok = can_add_with_local_circle if require_local_circle else can_add
    changed = True
    while changed:
        changed = False
        rng.shuffle(edges)
        for i, j in edges:
            if add_ok(adj, i, j):
                add_edge(adj, i, j)
                changed = True
    return adj


def improve(adj: list[int], rng: random.Random, steps: int, require_local_circle: bool = False) -> list[int]:
    n = len(adj)
    all_edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    best = adj[:]
    best_edges = edge_count(best)
    add_ok = can_add_with_local_circle if require_local_circle else can_add

    for _ in range(steps):
        current_edges = [(i, j) for i, j in all_edges if has_edge(adj, i, j)]
        if not current_edges:
            break

        removed = rng.sample(current_edges, min(len(current_edges), rng.choice([1, 1, 2, 2, 3])))
        for i, j in removed:
            remove_edge(adj, i, j)

        candidates = all_edges[:]
        rng.shuffle(candidates)
        for i, j in candidates:
            if add_ok(adj, i, j):
                add_edge(adj, i, j)

        e = edge_count(adj)
        if e >= best_edges:
            best = adj[:]
            best_edges = e
        else:
            # Keep occasional worse states to escape local optima.
            if rng.random() < 0.08:
                continue
            adj = best[:]

    return best


def worker(task: tuple[int, int, int, bool]) -> dict:
    n, seed, steps, require_local_circle = task
    rng = random.Random(seed)
    start = time.time()
    adj = greedy_fill(n, rng, require_local_circle)
    adj = improve(adj, rng, steps, require_local_circle)
    check = validate(adj, require_local_circle)
    edges = [
        [i + 1, j + 1]
        for i in range(n)
        for j in range(i + 1, n)
        if has_edge(adj, i, j)
    ]
    return {
        "seed": seed,
        "edge_count": check["edge_count"],
        "valid": check["valid"],
        "violations": check["violations"],
        "runtime_seconds": round(time.time() - start, 3),
        "require_local_circle": require_local_circle,
        "edges": edges,
    }


def write_best(best: dict, rows: list[dict]) -> None:
    OUTDIR.mkdir(exist_ok=True)
    suffix = "local_circle" if best.get("require_local_circle") else "basic"
    (OUTDIR / f"{suffix}_relaxation_heuristic_best.json").write_text(
        json.dumps(best, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (OUTDIR / f"{suffix}_relaxation_heuristic_best_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j"])
        writer.writerows(best["edges"])

    with (OUTDIR / f"{suffix}_relaxation_heuristic_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["seed", "edge_count", "valid", "runtime_seconds", "require_local_circle"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--runs", type=int, default=240)
    parser.add_argument("--steps", type=int, default=250)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--require-local-circle", action="store_true")
    args = parser.parse_args()

    tasks = [(args.n, args.seed + 7919 * i, args.steps, args.require_local_circle) for i in range(args.runs)]
    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks))
    start = time.time()
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            if len(rows) == 1 or row["edge_count"] >= max(r["edge_count"] for r in rows):
                print(f"new best/seen {len(rows)}/{len(tasks)}: {row['edge_count']} edges seed={row['seed']}", flush=True)

    rows.sort(key=lambda row: row["edge_count"], reverse=True)
    best = rows[0]
    best["total_wall_seconds"] = round(time.time() - start, 3)
    best["workers"] = actual_workers
    write_best(best, rows)
    print(json.dumps({key: best[key] for key in ["edge_count", "valid", "seed", "workers", "total_wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
