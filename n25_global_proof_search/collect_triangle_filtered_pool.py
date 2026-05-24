#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect isomorphism classes from the triangle-filtered search frontier."""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import networkx as nx

from basic_relaxation_search import default_worker_count
from triangle_filtered_search import worker

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "triangle_filtered_pool"


def graph_from_edges(n: int, edges: list[list[int]]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(1, n + 1))
    graph.add_edges_from((i, j) for i, j in edges)
    return graph


def graph_signature(graph: nx.Graph) -> tuple:
    degrees = tuple(sorted((degree for _, degree in graph.degree()), reverse=True))
    triangles = sum(nx.triangles(graph).values()) // 3
    wl_hash = nx.weisfeiler_lehman_graph_hash(graph, iterations=4)
    return graph.number_of_edges(), degrees, triangles, wl_hash


def classify(rows: list[dict], n: int) -> list[dict]:
    classes: list[dict] = []
    buckets: dict[tuple, list[dict]] = {}
    for row in rows:
        graph = graph_from_edges(n, row["edges"])
        row["signature"] = graph_signature(graph)
        row["graph"] = graph
        buckets.setdefault(row["signature"], []).append(row)

    class_id = 1
    for signature, bucket in sorted(buckets.items(), key=lambda item: (-item[0][0], item[0])):
        representatives: list[dict] = []
        for row in bucket:
            matched = False
            for rep in representatives:
                if nx.is_isomorphic(row["graph"], rep["graph"]):
                    rep["multiplicity"] += 1
                    rep["seeds"].append(row["seed"])
                    matched = True
                    break
            if not matched:
                item = dict(row)
                item["class_id"] = class_id
                item["multiplicity"] = 1
                item["seeds"] = [row["seed"]]
                representatives.append(item)
                class_id += 1
        classes.extend(representatives)

    classes.sort(key=lambda row: (-row["edge_count"], -row["multiplicity"], row["class_id"]))
    return classes


def write_outputs(classes: list[dict], raw_rows: list[dict], args: argparse.Namespace) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for row in classes:
        graph = row["graph"]
        summary = {
            "class_id": row["class_id"],
            "edge_count": row["edge_count"],
            "multiplicity": row["multiplicity"],
            "seed": row["seed"],
            "degree_sequence": " ".join(map(str, sorted((d for _, d in graph.degree()), reverse=True))),
            "triangle_count": sum(nx.triangles(graph).values()) // 3,
            "triangle_component_count": row["triangle_component_count"],
            "wl_hash": row["signature"][3],
        }
        summaries.append(summary)
        edge_path = OUTDIR / f"class_{row['class_id']:04d}_e{row['edge_count']}_edges.csv"
        with edge_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["i", "j"])
            writer.writerows(row["edges"])

    with (OUTDIR / "candidate_classes.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "class_id",
            "edge_count",
            "multiplicity",
            "seed",
            "degree_sequence",
            "triangle_count",
            "triangle_component_count",
            "wl_hash",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    metadata = {
        "n": args.n,
        "runs": args.runs,
        "steps": args.steps,
        "min_edges": args.min_edges,
        "max_nodes_per_triangle_component": args.max_nodes,
        "raw_candidate_count": len(raw_rows),
        "isomorphism_class_count": len(classes),
        "max_edge_count": max((row["edge_count"] for row in classes), default=None),
        "workers": args.actual_workers,
        "logical_processors": os.cpu_count(),
        "note": "Candidates pass local graph filters and exact triangular-lattice consistency; they are not confirmed geometric embeddings.",
    }
    (OUTDIR / "candidate_pool_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTDIR / "README.md").write_text(
        f"""# Triangle-Filtered Candidate Pool

This pool is generated after enforcing the exact triangular-lattice consistency
filter during the search itself.

```text
runs: {args.runs}
steps: {args.steps}
minimum edges kept: {args.min_edges}
raw candidates: {len(raw_rows)}
isomorphism classes: {len(classes)}
max edge count: {metadata['max_edge_count']}
```

These are abstract candidates only. The next stage is continuous geometric
elimination.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--runs", type=int, default=600)
    parser.add_argument("--steps", type=int, default=260)
    parser.add_argument("--min-edges", type=int, default=71)
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    tasks = [
        (args.n, args.seed + 7919 * i, args.steps, args.max_nodes)
        for i in range(args.runs)
    ]
    actual_workers = min(args.workers, len(tasks))
    args.actual_workers = actual_workers
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            if (
                row["local_valid"]
                and row["triangle_lattice_valid"]
                and row["edge_count"] >= args.min_edges
            ):
                rows.append(row)
            if rows and len(rows) % 50 == 0:
                print(f"collected {len(rows)} candidates; latest={row['edge_count']} edges", flush=True)

    classes = classify(rows, args.n)
    write_outputs(classes, rows, args)
    print(
        json.dumps(
            {
                "raw_candidate_count": len(rows),
                "isomorphism_class_count": len(classes),
                "max_edge_count": max((row["edge_count"] for row in classes), default=None),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
