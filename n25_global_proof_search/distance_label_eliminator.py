#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exact distance-label eliminator.

If vertices a,b have exactly two common unit-neighbors c,d, then the two unit
circles centered at c,d intersect in a,b and the squared distances satisfy

    |ab|^2 + |cd|^2 = 4.

Starting from graph edges labelled |uv|^2 = 1, this propagates forced
|uv|^2 = 3 labels. Fully labelled quadruples must satisfy the planar
Cayley-Menger determinant. A nonzero determinant is an exact algebraic
certificate of non-embeddability.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import sympy as sp

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = ROOT / "n25_global_proof_search" / "triangle_filtered_pool"
OUTDIR = ROOT / "n25_global_proof_search" / "distance_label_eliminator"

Edge = tuple[int, int]


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def infer_n(edges: list[Edge]) -> int:
    return max(max(i, j) for i, j in edges) + 1


def adjacency(n: int, edges: list[Edge]) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def propagate_labels(n: int, edges: list[Edge]) -> tuple[dict[Edge, int], dict | None, list[dict]]:
    adj = adjacency(n, edges)
    labels = {edge: 1 for edge in edges}
    derivations: list[dict] = []
    changed = True
    while changed:
        changed = False
        for a, b in itertools.combinations(range(n), 2):
            common = sorted(adj[a].intersection(adj[b]))
            if len(common) != 2:
                continue
            c, d = common
            p = normalize_edge(a, b)
            q = normalize_edge(c, d)
            for source, target in [(p, q), (q, p)]:
                if source not in labels:
                    continue
                value = 4 - labels[source]
                if target in labels and labels[target] != value:
                    return labels, {
                        "type": "label_conflict",
                        "source_pair": [source[0] + 1, source[1] + 1],
                        "source_value": labels[source],
                        "target_pair": [target[0] + 1, target[1] + 1],
                        "target_existing_value": labels[target],
                        "target_forced_value": value,
                        "common_neighbor_relation": [a + 1, b + 1, c + 1, d + 1],
                    }, derivations
                if target not in labels:
                    labels[target] = value
                    changed = True
                    derivations.append(
                        {
                            "source_pair": [source[0] + 1, source[1] + 1],
                            "source_value": labels[source],
                            "target_pair": [target[0] + 1, target[1] + 1],
                            "target_value": value,
                            "relation": [a + 1, b + 1, c + 1, d + 1],
                        }
                    )
    return labels, None, derivations


def solve_linear_distance_labels(n: int, edges: list[Edge]) -> tuple[dict[Edge, sp.Rational], list[dict]]:
    adj = adjacency(n, edges)
    pairs: set[Edge] = set(edges)
    relations: list[tuple[Edge, Edge]] = []
    for a, b in itertools.combinations(range(n), 2):
        common = sorted(adj[a].intersection(adj[b]))
        if len(common) != 2:
            continue
        p = normalize_edge(a, b)
        q = normalize_edge(common[0], common[1])
        pairs.add(p)
        pairs.add(q)
        relations.append((p, q))

    pair_list = sorted(pairs)
    index = {pair: pos for pos, pair in enumerate(pair_list)}
    equations: list[list[sp.Rational]] = []
    rhs: list[sp.Rational] = []

    for edge in edges:
        row = [sp.Rational(0)] * len(pair_list)
        row[index[edge]] = sp.Rational(1)
        equations.append(row)
        rhs.append(sp.Rational(1))

    for p, q in relations:
        row = [sp.Rational(0)] * len(pair_list)
        row[index[p]] += sp.Rational(1)
        row[index[q]] += sp.Rational(1)
        equations.append(row)
        rhs.append(sp.Rational(4))

    matrix = sp.Matrix(equations)
    vector = sp.Matrix(rhs)
    solution_set = sp.linsolve((matrix, vector))
    if not solution_set:
        return {}, [
            {
                "type": "linear_system_inconsistent",
                "equation_count": len(equations),
                "variable_count": len(pair_list),
            }
        ]

    solution = next(iter(solution_set))
    labels: dict[Edge, sp.Rational] = {}
    derivations: list[dict] = []
    for pair, value in zip(pair_list, solution):
        if value.free_symbols:
            continue
        rational_value = sp.Rational(value)
        labels[pair] = rational_value
        if pair not in edges:
            derivations.append(
                {
                    "pair": [pair[0] + 1, pair[1] + 1],
                    "squared_distance": str(rational_value),
                    "method": "linear_opposite_distance_system",
                }
            )
    return labels, derivations


def cayley_menger_det(values: list[sp.Expr]) -> sp.Expr:
    matrix = sp.Matrix(
        [
            [0, 1, 1, 1, 1],
            [1, 0, values[0], values[1], values[2]],
            [1, values[0], 0, values[3], values[4]],
            [1, values[1], values[3], 0, values[5]],
            [1, values[2], values[4], values[5], 0],
        ]
    )
    return sp.factor(matrix.det())


def find_bad_quad(n: int, labels: dict[Edge, sp.Expr]) -> dict | None:
    for quad in itertools.combinations(range(n), 4):
        pairs = [
            normalize_edge(quad[0], quad[1]),
            normalize_edge(quad[0], quad[2]),
            normalize_edge(quad[0], quad[3]),
            normalize_edge(quad[1], quad[2]),
            normalize_edge(quad[1], quad[3]),
            normalize_edge(quad[2], quad[3]),
        ]
        if not all(pair in labels for pair in pairs):
            continue
        values = [labels[pair] for pair in pairs]
        determinant = cayley_menger_det(values)
        if determinant != 0:
            return {
                "type": "cayley_menger_nonzero",
                "quad": [v + 1 for v in quad],
                "pair_order": [[p[0] + 1, p[1] + 1] for p in pairs],
                "squared_distances": [str(value) for value in values],
                "determinant": str(determinant),
            }
    return None


def analyze_edges(source: str, edges: list[Edge]) -> dict:
    n = infer_n(edges)
    labels, conflict, derivations = propagate_labels(n, edges)
    linear_labels, linear_derivations = solve_linear_distance_labels(n, edges)
    merged_labels: dict[Edge, sp.Expr] = {pair: sp.Rational(value) for pair, value in labels.items()}
    merged_labels.update(linear_labels)
    certificate = conflict or find_bad_quad(n, merged_labels)
    return {
        "source": source,
        "n": n,
        "edge_count": len(edges),
        "label_count": len(labels),
        "derived_label_count": len(derivations),
        "linear_label_count": len(linear_labels),
        "linear_derived_label_count": len(linear_derivations),
        "eliminated": certificate is not None,
        "certificate": certificate,
        "derivations": derivations if certificate is not None else derivations[:50],
        "linear_derivations": linear_derivations if certificate is not None else linear_derivations[:50],
    }


def read_class_summary(pool: Path) -> list[dict]:
    with (pool / "candidate_classes.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (-int(row["edge_count"]), int(row["class_id"])))
    return rows


def read_pool_edges(pool: Path, class_id: int, edge_count: int) -> list[Edge]:
    return read_edges(pool / f"class_{class_id:04d}_e{edge_count}_edges.csv")


def worker(task: tuple[str, list[Edge]]) -> dict:
    return analyze_edges(*task)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=None)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--classes", type=int, default=100)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.edges is not None:
        result = analyze_edges(args.edges.stem, read_edges(args.edges))
        (OUTDIR / f"{args.edges.stem}_distance_label_certificate.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    tasks = []
    for row in read_class_summary(args.pool)[: args.classes]:
        class_id = int(row["class_id"])
        edge_count = int(row["edge_count"])
        source = f"class_{class_id:04d}_e{edge_count}"
        tasks.append((source, read_pool_edges(args.pool, class_id, edge_count)))

    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks)) if tasks else 1
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{row['source']}: {'eliminated' if row['eliminated'] else 'passed'} "
                f"labels={row['label_count']}",
                flush=True,
            )

    rows.sort(key=lambda row: (not row["eliminated"], -row["edge_count"], row["source"]))
    with (OUTDIR / "distance_label_batch_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["source", "edge_count", "label_count", "derived_label_count", "eliminated"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})
    (OUTDIR / "distance_label_batch_details.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata = {
        "classes_tested": len(rows),
        "workers": actual_workers,
        "eliminated_count": sum(1 for row in rows if row["eliminated"]),
        "passed_count": sum(1 for row in rows if not row["eliminated"]),
        "interpretation": "Exact squared-distance propagation plus planar Cayley-Menger checks.",
    }
    (OUTDIR / "distance_label_batch_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
