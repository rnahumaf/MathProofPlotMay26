#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combinatorial upper-bound layer for the n=25 / 70 conjecture.

This is not the final Euclidean proof. It answers a narrower question:

    How many edges can a 25-vertex graph have if it satisfies the most basic
    graph-theoretic necessary conditions for being a planar unit-distance graph?

Necessary conditions used here:

1. No K_{2,3}: any two points in the plane have at most two common points at
   unit distance from both of them.
2. No K_4: four pairwise unit-distant points cannot exist in R^2.

If this MILP proves an upper bound <= 70, then these conditions alone would
prove the conjecture. More realistically, it returns denser abstract graphs;
those become the next obstruction candidates for geometric embedding tests.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search"


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def edge_index_map(n: int) -> tuple[list[tuple[int, int]], dict[tuple[int, int], int]]:
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    lookup = {edge: index for index, edge in enumerate(edges)}
    return edges, lookup


def eidx(lookup: dict[tuple[int, int], int], i: int, j: int) -> int:
    if i > j:
        i, j = j, i
    return lookup[(i, j)]


def build_constraints(n: int, lookup: dict[tuple[int, int], int]) -> tuple[LinearConstraint, dict[str, int]]:
    m = n * (n - 1) // 2
    k23_count = math.comb(n, 2) * math.comb(n - 2, 3)
    k4_count = math.comb(n, 4)
    row_count = k23_count + k4_count
    matrix = lil_matrix((row_count, m), dtype=float)
    lower = np.full(row_count, -np.inf)
    upper = np.full(row_count, np.inf)

    row = 0

    # For every pair {u,v} and every triple {a,b,c} outside it, at least one
    # of the six incidence edges must be absent. This enforces codegree <= 2.
    for u, v in itertools.combinations(range(n), 2):
        rest = [x for x in range(n) if x not in (u, v)]
        for a, b, c in itertools.combinations(rest, 3):
            for w in (a, b, c):
                matrix[row, eidx(lookup, u, w)] = 1.0
                matrix[row, eidx(lookup, v, w)] = 1.0
            upper[row] = 5.0
            row += 1

    # For every 4-set, at least one of the six edges must be absent.
    for quad in itertools.combinations(range(n), 4):
        for i, j in itertools.combinations(quad, 2):
            matrix[row, eidx(lookup, i, j)] = 1.0
        upper[row] = 5.0
        row += 1

    assert row == row_count
    return LinearConstraint(matrix.tocsr(), lower, upper), {
        "k23_constraints": k23_count,
        "k4_constraints": k4_count,
        "total_constraints": row_count,
    }


def solve_relaxation(n: int, threads: int, time_limit: float) -> dict:
    edges, lookup = edge_index_map(n)
    constraints, counts = build_constraints(n, lookup)
    c = -np.ones(len(edges), dtype=float)
    options = {"time_limit": time_limit, "mip_rel_gap": 0.0}
    if threads > 0:
        options["threads"] = threads

    start = time.time()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unrecognized options detected: .*threads.*")
        result = milp(
            c=c,
            integrality=np.ones(len(edges)),
            bounds=Bounds(np.zeros(len(edges)), np.ones(len(edges))),
            constraints=constraints,
            options=options,
        )
    elapsed = time.time() - start

    selected = []
    if result.x is not None:
        selected = [
            {"i": i + 1, "j": j + 1}
            for (i, j), value in zip(edges, result.x)
            if value > 0.5
        ]

    edge_count = None if result.fun is None else int(round(-float(result.fun)))
    payload = {
        "claim": "Maximum edge count under basic graph-theoretic necessary conditions.",
        "scope": "abstract_graph_relaxation_not_full_geometry",
        "n": n,
        "conditions": [
            "K_{2,3}-free / every vertex pair has at most two common neighbors",
            "K_4-free",
        ],
        "solver": "scipy.optimize.milp / HiGHS",
        "logical_processors": os.cpu_count(),
        "threads_requested": threads,
        "time_limit_seconds": time_limit,
        "runtime_seconds": round(elapsed, 3),
        "constraint_counts": counts,
        "status": int(result.status),
        "success": bool(result.success),
        "message": result.message,
        "objective_edge_count": edge_count,
        "mip_gap": None if getattr(result, "mip_gap", None) is None else float(result.mip_gap),
        "selected_edges": selected,
        "interpretation": (
            "If objective_edge_count is greater than 70, these necessary graph constraints "
            "are not strong enough by themselves; the selected graph is a target for "
            "geometric non-embeddability tests."
        ),
    }
    return payload


def write_outputs(payload: dict) -> None:
    OUTDIR.mkdir(exist_ok=True)
    n = payload["n"]
    json_path = OUTDIR / f"basic_forbidden_subgraph_relaxation_n{n}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    edge_path = OUTDIR / f"basic_relaxation_candidate_edges_n{n}.csv"
    with edge_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("i,j\n")
        for edge in payload["selected_edges"]:
            handle.write(f"{edge['i']},{edge['j']}\n")

    readme = f"""# n=25 Global Proof Search

This folder is the next step after the UCCS record search. We now treat
`U(25)=70` as a conjecture and start building a layered computer-assisted
upper-bound proof.

## Layer 1: Basic Forbidden Subgraphs

`combinatorial_upper_bound.py` solves an abstract MILP over all graphs on
25 labelled vertices using necessary conditions for unit-distance graphs:

- no `K_{{2,3}}`, because two unit circles intersect in at most two points;
- no `K_4`, because four pairwise unit-distant points cannot exist in the
  Euclidean plane.

Latest result:

```text
status: {payload['status']}
success: {payload['success']}
objective_edge_count: {payload['objective_edge_count']}
mip_gap: {payload['mip_gap']}
runtime_seconds: {payload['runtime_seconds']}
threads_requested: {payload['threads_requested']}
```

Interpretation:

- If the objective is `<= 70`, this layer alone proves the desired upper bound.
- If the objective is `> 70`, the selected edge set in
  `basic_relaxation_candidate_edges.csv` is an abstract graph that passes the
  simplest tests but still needs geometric non-embeddability elimination.

This is expected: the final proof will likely require an enumeration plus a
geometric embedder, similar in spirit to the Alexeev-Mixon-Parshall strategy
for small unit-distance sets.

## Commands

```powershell
python .\\n25_global_proof_search\\combinatorial_upper_bound.py
```
"""
    (OUTDIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--time-limit", type=float, default=600.0)
    args = parser.parse_args()

    payload = solve_relaxation(args.n, args.workers, args.time_limit)
    write_outputs(payload)
    print(json.dumps({k: payload[k] for k in ["status", "success", "objective_edge_count", "mip_gap", "runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
