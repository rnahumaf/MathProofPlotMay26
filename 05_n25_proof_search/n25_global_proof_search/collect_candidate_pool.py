#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect and classify dense abstract candidate graphs for the n=25 upper-bound
proof search.

The goal is not to prove embeddability. The goal is to create a deduplicated
pool of 71+ edge graph shapes that pass the local necessary filters, so later
geometric eliminators can work on isomorphism classes instead of labelled
duplicates.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import networkx as nx

from basic_relaxation_search import default_worker_count, worker

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "n25_global_proof_search" / "candidate_pool"


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


def write_outputs(classes: list[dict], raw_rows: list[dict], n: int, min_edges: int, require_local_circle: bool) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for row in classes:
        graph = row["graph"]
        summary = {
            "class_id": row["class_id"],
            "edge_count": row["edge_count"],
            "multiplicity": row["multiplicity"],
            "seed": row["seed"],
            "degree_sequence": " ".join(map(str, sorted((d for _, d in graph.degree()), reverse=True))),
            "triangle_count": sum(nx.triangles(graph).values()) // 3,
            "wl_hash": row["signature"][3],
        }
        summary_rows.append(summary)

        edge_path = OUTDIR / f"class_{row['class_id']:04d}_e{row['edge_count']}_edges.csv"
        with edge_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["i", "j"])
            writer.writerows(row["edges"])

    with (OUTDIR / "candidate_classes.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["class_id", "edge_count", "multiplicity", "seed", "degree_sequence", "triangle_count", "wl_hash"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    metadata = {
        "n": n,
        "min_edges": min_edges,
        "require_local_circle": require_local_circle,
        "raw_candidate_count": len(raw_rows),
        "isomorphism_class_count": len(classes),
        "max_edge_count": max((row["edge_count"] for row in classes), default=None),
        "logical_processors": os.cpu_count(),
        "note": "These are abstract graph candidates, not confirmed geometric embeddings.",
    }
    (OUTDIR / "candidate_pool_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme = f"""# Candidate Pool

Deduplicated abstract graph candidates for the `n=25`, `U(25)=70` proof search.

These graphs pass the current local filters and have at least `{min_edges}`
edges. They are not known to be geometrically embeddable.

```text
raw candidates: {len(raw_rows)}
isomorphism classes: {len(classes)}
max edge count: {metadata['max_edge_count']}
local-circle filter: {require_local_circle}
```

Next step: run geometric/non-embeddability eliminators on each class
representative.
"""
    (OUTDIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--runs", type=int, default=600)
    parser.add_argument("--steps", type=int, default=350)
    parser.add_argument("--min-edges", type=int, default=71)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--no-local-circle", action="store_true")
    args = parser.parse_args()

    require_local_circle = not args.no_local_circle
    tasks = [
        (args.n, args.seed + 7919 * i, args.steps, require_local_circle)
        for i in range(args.runs)
    ]
    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            if row["valid"] and row["edge_count"] >= args.min_edges:
                rows.append(row)
            if rows and len(rows) % 50 == 0:
                print(f"collected {len(rows)} candidates; latest edges={row['edge_count']}", flush=True)

    classes = classify(rows, args.n)
    write_outputs(classes, rows, args.n, args.min_edges, require_local_circle)
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
