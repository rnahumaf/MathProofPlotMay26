#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigation harness for the conjecture that 25 planar points have at most
70 unit-distance pairs.

This does three different jobs, with deliberately different proof strength:

1. exact-lower-bound
   Converts the current UCCS n=25/e=70 decimal certificate into Q(sqrt(3))
   coordinates and verifies all 70 unit distances exactly.

2. finite-uccs-upper-bound
   Rebuilds the finite UCCS candidate universe and solves the exact maximum
   25-vertex induced-edge problem inside that finite graph with SciPy/HiGHS.
   This is a rigorous upper bound only for that candidate universe.

3. counterexample-search
   Runs wider UCCS heuristic searches trying to find 71+ edges.

None of these is, by itself, a global proof in the unrestricted Euclidean plane.
The global proof would require eliminating every embeddable unit-distance graph
on 25 vertices with 71 or more edges.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_max70_investigation"
UCCS_DIR = ROOT.parent / "03_uccs_exploration"
SOURCE_POINTS = UCCS_DIR / "uccs_square_stat_runs" / "n25_e70_seed20270530_points.csv"
SOURCE_EDGES = UCCS_DIR / "uccs_square_stat_runs" / "n25_e70_seed20270530_edges.csv"


def default_worker_count() -> int:
    """Use most logical processors while leaving one for the OS/UI."""

    return max(1, (os.cpu_count() or 2) - 1)


@dataclass(frozen=True)
class Qsqrt3:
    """Number a + b*sqrt(3), with exact rational a and b."""

    a: Fraction
    b: Fraction

    def __add__(self, other: "Qsqrt3") -> "Qsqrt3":
        return Qsqrt3(self.a + other.a, self.b + other.b)

    def __sub__(self, other: "Qsqrt3") -> "Qsqrt3":
        return Qsqrt3(self.a - other.a, self.b - other.b)

    def __mul__(self, other: "Qsqrt3") -> "Qsqrt3":
        return Qsqrt3(
            self.a * other.a + 3 * self.b * other.b,
            self.a * other.b + self.b * other.a,
        )

    def square(self) -> "Qsqrt3":
        return self * self

    def as_float(self) -> float:
        return float(self.a) + float(self.b) * math.sqrt(3.0)

    def to_json(self) -> dict[str, str]:
        return {"a": str(self.a), "b": str(self.b), "expr": self.expr()}

    def expr(self) -> str:
        if self.b == 0:
            return str(self.a)
        if self.a == 0:
            return f"{self.b}*sqrt(3)"
        sign = "+" if self.b > 0 else "-"
        return f"{self.a} {sign} {abs(self.b)}*sqrt(3)"


ZERO = Qsqrt3(Fraction(0), Fraction(0))
ONE = Qsqrt3(Fraction(1), Fraction(0))


def candidate_fractions(limit: int = 8, denominator: int = 2) -> list[Fraction]:
    return [Fraction(k, denominator) for k in range(-limit * denominator, limit * denominator + 1)]


def recover_qsqrt3(value: float) -> Qsqrt3:
    """Recover small half-integer coordinates of the form a+b*sqrt(3)."""

    best: tuple[float, Fraction, Fraction] | None = None
    for a in candidate_fractions():
        for b in candidate_fractions():
            error = abs(float(a) + float(b) * math.sqrt(3.0) - value)
            if best is None or error < best[0]:
                best = (error, a, b)
    assert best is not None
    error, a, b = best
    if error > 1e-9:
        raise ValueError(f"Could not recover Q(sqrt(3)) value for {value}; best error={error}")
    return Qsqrt3(a, b)


def load_decimal_points(path: Path = SOURCE_POINTS) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(float(row["x"]), float(row["y"])) for row in reader]


def load_declared_edges(path: Path = SOURCE_EDGES) -> set[tuple[int, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {tuple(sorted((int(row["i"]) - 1, int(row["j"]) - 1))) for row in reader}


def exact_squared_distance(p: tuple[Qsqrt3, Qsqrt3], q: tuple[Qsqrt3, Qsqrt3]) -> Qsqrt3:
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return dx.square() + dy.square()


def exact_unit_edges(points: list[tuple[Qsqrt3, Qsqrt3]]) -> set[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if exact_squared_distance(points[i], points[j]) == ONE:
                edges.add((i, j))
    return edges


def write_exact_lower_bound_certificate() -> dict:
    decimals = load_decimal_points()
    exact_points = [(recover_qsqrt3(x), recover_qsqrt3(y)) for x, y in decimals]
    declared_edges = load_declared_edges()
    measured_edges = exact_unit_edges(exact_points)

    missing_declared = sorted(declared_edges - measured_edges)
    extra_measured = sorted(measured_edges - declared_edges)
    certificate = {
        "claim": "There exist 25 points in the Euclidean plane with 70 unit-distance pairs.",
        "field": "Q(sqrt(3))",
        "point_count": len(exact_points),
        "unit_edge_count": len(measured_edges),
        "declared_edge_count": len(declared_edges),
        "declared_edges_match_exact_measurement": not missing_declared and not extra_measured,
        "missing_declared_edges": [[i + 1, j + 1] for i, j in missing_declared],
        "extra_measured_edges": [[i + 1, j + 1] for i, j in extra_measured],
        "points": [
            {
                "index": index,
                "x": x.to_json(),
                "y": y.to_json(),
                "x_float": x.as_float(),
                "y_float": y.as_float(),
            }
            for index, (x, y) in enumerate(exact_points, 1)
        ],
        "edges": [[i + 1, j + 1] for i, j in sorted(measured_edges)],
    }

    out = OUTDIR / "n25_e70_exact_certificate.json"
    out.write_text(json.dumps(certificate, indent=2, ensure_ascii=False), encoding="utf-8")
    return certificate


def build_uccs_candidate_graph(top_candidates: int, bounds_padding: float) -> tuple[list[tuple[float, float]], list[tuple[int, int]]]:
    sys.path.insert(0, str(UCCS_DIR))
    import uccs_interactive_runner_v3_resilient as uccs

    seed = uccs.base_seed_for_n(25)
    bounds = uccs.crop_bounds_for_seed(seed, bounds_padding)
    raw = uccs.build_closure_candidates(seed, rounds=1, bounds=bounds)
    candidates = uccs.degree_filter(raw, top_candidates)
    edges = uccs.unit_edges(candidates)
    return candidates, edges


def solve_max_k_edge_induced_subgraph(
    node_count: int,
    edges: list[tuple[int, int]],
    k: int = 25,
    time_limit_seconds: float = 300.0,
    threads: int = 0,
) -> dict:
    """Solve max induced edges on k selected nodes as a binary MILP."""

    edge_count = len(edges)
    variable_count = node_count + edge_count
    objective = np.zeros(variable_count)
    objective[node_count:] = -1.0

    row_count = 1 + 3 * edge_count
    matrix = lil_matrix((row_count, variable_count), dtype=float)
    lower = np.full(row_count, -np.inf)
    upper = np.full(row_count, np.inf)

    matrix[0, :node_count] = 1.0
    lower[0] = k
    upper[0] = k

    row = 1
    for edge_index, (i, j) in enumerate(edges):
        y = node_count + edge_index

        # y_ij <= x_i
        matrix[row, y] = 1.0
        matrix[row, i] = -1.0
        upper[row] = 0.0
        row += 1

        # y_ij <= x_j
        matrix[row, y] = 1.0
        matrix[row, j] = -1.0
        upper[row] = 0.0
        row += 1

        # y_ij >= x_i + x_j - 1
        matrix[row, i] = 1.0
        matrix[row, j] = 1.0
        matrix[row, y] = -1.0
        upper[row] = 1.0
        row += 1

    constraints = LinearConstraint(matrix.tocsr(), lower, upper)
    options = {"time_limit": time_limit_seconds, "mip_rel_gap": 0.0}
    if threads > 0:
        # SciPy forwards unknown options to HiGHS; recent HiGHS builds accept
        # this and use it for MIP branch-and-bound parallelism.
        options["threads"] = threads

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unrecognized options detected: .*threads.*")
        result = milp(
            c=objective,
            integrality=np.ones(variable_count),
            bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
            constraints=constraints,
            options=options,
        )

    selected_vertices: list[int] = []
    if result.x is not None:
        selected_vertices = [i + 1 for i, value in enumerate(result.x[:node_count]) if value > 0.5]

    objective_edges = None if result.fun is None else int(round(-float(result.fun)))
    return {
        "status": int(result.status),
        "success": bool(result.success),
        "message": result.message,
        "node_count": node_count,
        "candidate_edge_count": edge_count,
        "selected_vertex_count": k,
        "optimal_edge_count": objective_edges,
        "mip_gap": None if getattr(result, "mip_gap", None) is None else float(result.mip_gap),
        "threads_requested": threads,
        "selected_vertices_1_based": selected_vertices,
    }


def write_finite_uccs_upper_bound(
    top_candidates: int,
    bounds_padding: float,
    time_limit_seconds: float,
    threads: int,
) -> dict:
    start = time.time()
    candidates, edges = build_uccs_candidate_graph(top_candidates, bounds_padding)
    solver = solve_max_k_edge_induced_subgraph(
        node_count=len(candidates),
        edges=edges,
        k=25,
        time_limit_seconds=time_limit_seconds,
        threads=threads,
    )
    result = {
        "claim": "Maximum 25-point induced subgraph inside this finite UCCS candidate graph.",
        "scope": "finite_uccs_candidate_universe_only",
        "top_candidates": top_candidates,
        "bounds_padding": bounds_padding,
        "runtime_seconds": round(time.time() - start, 3),
        "solver": "scipy.optimize.milp / HiGHS",
        "local_compute": {
            "logical_processors": os.cpu_count(),
            "threads_requested": threads,
            "gpu_note": "RTX GPU is not used by SciPy/HiGHS MILP; this workload is CPU/RAM-bound.",
        },
        "solver_result": solver,
        "interpretation": (
            "If success is true, mip_gap is 0, and optimal_edge_count is 70, "
            "then no 25-point subset of this finite UCCS candidate graph has 71 or more unit-distance pairs."
        ),
    }
    out = OUTDIR / f"finite_uccs_upper_bound_top{top_candidates}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def counterexample_search_one(task: tuple[int, int, int, float, int]) -> dict:
    top_candidates, restarts, steps, bounds_padding, local_seed = task
    sys.path.insert(0, str(UCCS_DIR))
    import uccs_interactive_runner_v3_resilient as uccs

    start = time.time()
    seed_points = uccs.base_seed_for_n(25)
    bounds = uccs.crop_bounds_for_seed(seed_points, bounds_padding)
    raw = uccs.build_closure_candidates(seed_points, rounds=1, bounds=bounds)
    candidates = uccs.degree_filter(raw, top_candidates)
    best_edges, best_points, stats = uccs.search_best_subset(
        candidates,
        n=25,
        restarts=restarts,
        steps=steps,
        seed=local_seed,
    )
    edges = uccs.unit_edges(best_points)
    if best_edges >= 71:
        points_path = OUTDIR / f"counterexample_n25_e{best_edges}_top{top_candidates}_seed{local_seed}_points.csv"
        edges_path = OUTDIR / f"counterexample_n25_e{best_edges}_top{top_candidates}_seed{local_seed}_edges.csv"
        uccs.save_points_csv(points_path, best_points)
        uccs.save_edges_csv(edges_path, edges)

    return {
        "top_candidates": top_candidates,
        "seed": local_seed,
        "raw_candidate_count": len(raw),
        "filtered_candidate_count": len(candidates),
        "best_edges": best_edges,
        "verified_edges": len(edges),
        "found_71_or_more": best_edges >= 71,
        "mean_restart_edges": stats["mean_restart_edges"],
        "std_restart_edges": stats["std_restart_edges"],
        "min_restart_edges": stats["min_restart_edges"],
        "max_restart_edges": stats["max_restart_edges"],
        "runtime_seconds": round(time.time() - start, 3),
    }


def run_counterexample_search(
    top_candidates_values: Iterable[int],
    restarts: int,
    steps: int,
    bounds_padding: float,
    seed: int,
    workers: int,
) -> list[dict]:
    tasks = [
        (top_candidates, restarts, steps, bounds_padding, seed + 1009 * offset)
        for offset, top_candidates in enumerate(top_candidates_values)
    ]
    actual_workers = min(max(1, workers), len(tasks))
    rows: list[dict] = []
    if actual_workers == 1:
        rows = [counterexample_search_one(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=actual_workers) as executor:
            futures = [executor.submit(counterexample_search_one, task) for task in tasks]
            for future in as_completed(futures):
                rows.append(future.result())

    rows.sort(key=lambda row: (row["top_candidates"], row["seed"]))

    csv_path = OUTDIR / "counterexample_search_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_readme() -> None:
    content = """# n=25 / 70 Unit-Distance Investigation

This folder tests the conjecture:

> Among 25 points in the Euclidean plane, the maximum possible number of
> unit-distance pairs is 70.

## Current Status

The repository now has a rigorous **lower-bound certificate**:

- `n25_e70_exact_certificate.json` verifies, in `Q(sqrt(3))`, that the current
  25-point UCCS configuration has exactly 70 unit-distance pairs.

This proves:

```text
U(25) >= 70
```

It does **not** prove the global upper bound `U(25) <= 70`.

According to OEIS A186705 and the Alexeev-Mixon-Parshall small-point-set work,
the public exact table currently reaches `n=21`; `n=25` is therefore outside
the listed exact range. See: https://oeis.org/A186705

## What The Scripts Can Prove

`finite_uccs_upper_bound_top*.json` is a finite-universe certificate. If the
MILP solver reports success with zero MIP gap and optimum 70, it proves:

```text
No 25-point subset of that finite UCCS candidate graph has 71+ edges.
```

That is useful, but narrower than the global Euclidean problem.

## How To Re-run

```powershell
python .\\n25_max70_investigation\\investigate_n25_max70.py --all
```

Faster lower-bound-only check:

```powershell
python .\\n25_max70_investigation\\investigate_n25_max70.py --exact-lower-bound
```

Finite UCCS upper-bound check:

```powershell
python .\\n25_max70_investigation\\investigate_n25_max70.py --finite-uccs-upper-bound --top-candidates 180
```

Counterexample search:

```powershell
python .\\n25_max70_investigation\\investigate_n25_max70.py --counterexample-search --top-candidates-list 180,220,260
```

## Local Compute Policy

The script defaults to `os.cpu_count() - 1` workers. On the current machine that
means `15` workers out of `16` logical processors, leaving one logical processor
for Windows/Codex. Independent counterexample searches run in parallel worker
processes.

For the MILP finite-upper-bound check, the same worker count is forwarded to
HiGHS as a thread request. SciPy/HiGHS is CPU/RAM-bound here; the RTX GPU is not
used unless a future CUDA-capable solver backend is added.

## Global Proof Path

To prove `U(25)=70` globally, the next step is not another plot. It is a
computer-assisted extremal proof:

1. enumerate candidate 25-vertex graphs with at least 71 edges;
2. eliminate graphs that are not unit-distance embeddable;
3. prove that every remaining embeddable case is impossible.

The present folder prepares the lower-bound certificate and finite-family
upper-bound checks needed before attempting that larger enumeration.
"""
    (OUTDIR / "README.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--exact-lower-bound", action="store_true")
    parser.add_argument("--finite-uccs-upper-bound", action="store_true")
    parser.add_argument("--counterexample-search", action="store_true")
    parser.add_argument("--top-candidates", type=int, default=180)
    parser.add_argument("--top-candidates-list", default="180,220,260")
    parser.add_argument("--bounds-padding", type=float, default=0.35)
    parser.add_argument("--milp-time-limit", type=float, default=300.0)
    parser.add_argument("--restarts", type=int, default=800)
    parser.add_argument("--steps", type=int, default=800)
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    args = parser.parse_args()

    OUTDIR.mkdir(exist_ok=True)
    write_readme()

    if args.all or args.exact_lower_bound:
        cert = write_exact_lower_bound_certificate()
        print(
            "Exact lower-bound certificate:",
            cert["point_count"],
            "points,",
            cert["unit_edge_count"],
            "unit edges, match=",
            cert["declared_edges_match_exact_measurement"],
        )

    if args.all or args.finite_uccs_upper_bound:
        result = write_finite_uccs_upper_bound(
            args.top_candidates,
            args.bounds_padding,
            args.milp_time_limit,
            threads=args.workers,
        )
        print("Finite UCCS upper-bound result:", result["solver_result"])

    if args.all or args.counterexample_search:
        values = [int(part.strip()) for part in args.top_candidates_list.split(",") if part.strip()]
        rows = run_counterexample_search(values, args.restarts, args.steps, args.bounds_padding, args.seed, args.workers)
        print("Counterexample search rows:")
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
