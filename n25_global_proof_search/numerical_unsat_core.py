#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Greedy numerical search for small infeasible unit-distance cores."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

from geometric_embedder import worker as embed_worker

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "numerical_unsat_core"
DEFAULT_EDGES = ROOT / "n25_global_proof_search" / "non_trilaterable_maximality" / "non_trilaterable_search_best_edges.csv"

Edge = tuple[int, int]


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def remap_edges(edges: list[Edge]) -> tuple[list[Edge], dict[int, int]]:
    vertices = sorted({v for edge in edges for v in edge})
    mapping = {old: new for new, old in enumerate(vertices)}
    return [(mapping[i], mapping[j]) for i, j in edges], mapping


def score_edges(edges: list[Edge], runs: int, max_nfev: int, seed: int, scale: float) -> dict:
    remapped, mapping = remap_edges(edges)
    n = len(mapping)
    if not remapped:
        return {"max_abs": 0.0, "rms": 0.0, "n": n}
    rows = [
        embed_worker((seed + 104729 * i, remapped, n, max_nfev, scale))
        for i in range(runs)
    ]
    best = min(rows, key=lambda row: row["max_abs_edge_squared_error"])
    return {
        "max_abs": best["max_abs_edge_squared_error"],
        "rms": best["rms_edge_squared_error"],
        "n": n,
        "seed": best["seed"],
    }


def greedy_core(
    edges: list[Edge],
    threshold: float,
    passes: int,
    runs: int,
    max_nfev: int,
    seed: int,
    scale: float,
) -> tuple[list[Edge], list[dict]]:
    rng = random.Random(seed)
    core = edges[:]
    history: list[dict] = []
    baseline = score_edges(core, runs, max_nfev, seed, scale)
    history.append({"action": "baseline", "edge_count": len(core), **baseline})

    for pass_index in range(1, passes + 1):
        order = core[:]
        rng.shuffle(order)
        changed = False
        for edge in order:
            if edge not in core or len(core) <= 2:
                continue
            trial = [item for item in core if item != edge]
            result = score_edges(trial, runs, max_nfev, seed + pass_index * 1000003 + len(history), scale)
            if result["max_abs"] >= threshold:
                core = trial
                changed = True
                history.append(
                    {
                        "action": "remove",
                        "pass": pass_index,
                        "removed_edge": [edge[0] + 1, edge[1] + 1],
                        "edge_count": len(core),
                        **result,
                    }
                )
                print(
                    f"removed {edge[0]+1}-{edge[1]+1}; "
                    f"edges={len(core)} max_abs={result['max_abs']:.3e}",
                    flush=True,
                )
        if not changed:
            history.append({"action": "pass_no_change", "pass": pass_index, "edge_count": len(core)})
            break
    return core, history


def write_core(core: list[Edge], history: list[dict], source: Path, args: argparse.Namespace) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with (OUTDIR / "unsat_core_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j"])
        for i, j in core:
            writer.writerow([i + 1, j + 1])
    (OUTDIR / "unsat_core_history.json").write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata = {
        "source_edges": str(source),
        "initial_edge_count": len(read_edges(source)),
        "core_edge_count": len(core),
        "core_vertex_count": len({v for edge in core for v in edge}),
        "threshold": args.threshold,
        "runs_per_score": args.runs_per_score,
        "max_nfev": args.max_nfev,
        "interpretation": "Numerical heuristic only; a small core needs exact or interval certification.",
    }
    (OUTDIR / "unsat_core_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--threshold", type=float, default=0.20)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--runs-per-score", type=int, default=8)
    parser.add_argument("--max-nfev", type=int, default=10000)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    edges = read_edges(args.edges)
    core, history = greedy_core(
        edges,
        threshold=args.threshold,
        passes=args.passes,
        runs=args.runs_per_score,
        max_nfev=args.max_nfev,
        seed=args.seed,
        scale=args.scale,
    )
    write_core(core, history, args.edges, args)
    print(
        json.dumps(
            {
                "initial_edges": len(edges),
                "core_edges": len(core),
                "core_vertices": len({v for edge in core for v in edge}),
                "last": history[-1],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
