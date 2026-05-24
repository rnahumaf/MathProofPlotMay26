#!/usr/bin/env python3
"""Extract exact square-size subgraphs from a local Stage 16/OpenAI dataset."""

from __future__ import annotations

import csv
import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path


OUTDIR = Path("openai_square_exact_runs")
DATASET_SLUG = "09_regular12_balanced"
DATASET_DIR = Path("final_blueprint_symmetric_variations")
SQUARE_SIDES = range(4, 21)


@dataclass
class ExactRun:
    n: int
    side: int
    best_edges: int
    mean_edges: float
    std_edges: float
    min_edges: int
    max_edges: int
    sample_count: int
    source_dataset: str
    source_points: int
    source_edges: int
    restarts: int
    steps: int
    base_seed: int
    runtime_seconds: float
    points_csv: str
    edges_csv: str
    metadata_json: str


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_graph(edge_rows: list[dict]) -> tuple[list[set[int]], list[tuple[int, int]]]:
    max_id = 0
    edges = []
    for row in edge_rows:
        i = int(row["from_id"])
        j = int(row["to_id"])
        max_id = max(max_id, i, j)
        edges.append((i, j))
    adj = [set() for _ in range(max_id + 1)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj, edges


def count_edges(adj: list[set[int]], selected: set[int]) -> int:
    return sum(len(adj[i] & selected) for i in selected) // 2


def local_search_exact_n(adj: list[set[int]], n: int, restarts: int, steps: int, seed: int) -> tuple[int, set[int]]:
    rng = random.Random(seed)
    nodes = list(range(len(adj)))
    all_nodes = set(nodes)
    degree_order = sorted(nodes, key=lambda i: len(adj[i]), reverse=True)
    best = set(degree_order[:n])
    best_edges = count_edges(adj, best)

    hot_pool_size = min(len(nodes), max(5 * n, 600))
    hot_pool = degree_order[:hot_pool_size]

    for restart in range(restarts):
        if restart % 4 == 0:
            selected = set(degree_order[:n])
            swaps = min(n // 2 + 1, max(4, n))
            for _ in range(swaps):
                out = rng.choice(tuple(selected))
                inn = rng.choice(hot_pool)
                if inn not in selected:
                    selected.remove(out)
                    selected.add(inn)
        elif restart % 4 == 1:
            selected = set(rng.sample(hot_pool, n))
        elif restart % 4 == 2:
            pool = degree_order[: min(len(nodes), max(2 * n, 80))]
            selected = set(rng.sample(pool, n))
        else:
            selected = set(rng.sample(nodes, n))

        current_edges = count_edges(adj, selected)
        temperature = 1.15

        for _ in range(steps):
            out = rng.choice(tuple(selected))
            remaining = selected - {out}
            available_pool = hot_pool if rng.random() < 0.9 else nodes
            sample = [x for x in rng.sample(available_pool, min(len(available_pool), 36)) if x not in selected]
            if not sample:
                continue
            if rng.random() < 0.86:
                inn = max(sample, key=lambda x: len(adj[x] & remaining))
            else:
                inn = rng.choice(sample)

            delta = len(adj[inn] & remaining) - len(adj[out] & remaining)
            if delta >= 0 or rng.random() < math.exp(delta / max(temperature, 1e-9)):
                selected.remove(out)
                selected.add(inn)
                current_edges += delta

            temperature *= 0.997

            if current_edges > best_edges:
                best = set(selected)
                best_edges = current_edges

    return best_edges, best


def induced_edges(edges: list[tuple[int, int]], selected: set[int]) -> list[tuple[int, int]]:
    return [(i, j) for i, j in edges if i in selected and j in selected]


def write_points(path: Path, point_rows: list[dict], selected: set[int]) -> dict[int, int]:
    ordered = sorted(selected)
    remap = {old_id: index + 1 for index, old_id in enumerate(ordered)}
    by_id = {int(row["id"]): row for row in point_rows}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "source_id", "x", "y", "max_embedding_abs"])
        for old_id in ordered:
            row = by_id[old_id]
            writer.writerow([remap[old_id], old_id, row["x"], row["y"], row["max_embedding_abs"]])
    return remap


def write_edges(path: Path, edges: list[tuple[int, int]], remap: dict[int, int]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j", "source_i", "source_j"])
        for i, j in edges:
            writer.writerow([remap[i], remap[j], i, j])


def write_summary(path: Path, rows: list[ExactRun]) -> None:
    fields = list(asdict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    point_rows = read_csv(DATASET_DIR / f"{DATASET_SLUG}_points.csv")
    edge_rows = read_csv(DATASET_DIR / f"{DATASET_SLUG}_edges.csv")
    adj, all_edges = build_graph(edge_rows)

    runs = []
    for side in SQUARE_SIDES:
        n = side * side
        start = time.time()
        restarts = 260 if n <= 144 else 380
        steps = 620 if n <= 144 else 840
        sample_count = 10
        base_seed = 20260523 + n * 31
        samples = []
        best_edges = -1
        selected: set[int] = set()
        for sample_index in range(sample_count):
            seed = base_seed + sample_index * 1009
            sample_edges, sample_selected = local_search_exact_n(adj, n, restarts=restarts, steps=steps, seed=seed)
            samples.append({"sample_index": sample_index, "seed": seed, "edges": sample_edges})
            if sample_edges > best_edges:
                best_edges = sample_edges
                selected = sample_selected
        values = [sample["edges"] for sample in samples]
        mean_edges = sum(values) / len(values)
        variance = sum((value - mean_edges) ** 2 for value in values) / len(values)
        std_edges = math.sqrt(variance)
        selected_edges = induced_edges(all_edges, selected)
        assert len(selected_edges) == best_edges

        stem = f"openai_stage16_exact_n{n}_e{best_edges}"
        points_csv = OUTDIR / f"{stem}_points.csv"
        edges_csv = OUTDIR / f"{stem}_edges.csv"
        metadata_json = OUTDIR / f"{stem}_metadata.json"
        remap = write_points(points_csv, point_rows, selected)
        write_edges(edges_csv, selected_edges, remap)

        run = ExactRun(
            n=n,
            side=side,
            best_edges=best_edges,
            mean_edges=round(mean_edges, 3),
            std_edges=round(std_edges, 3),
            min_edges=min(values),
            max_edges=max(values),
            sample_count=sample_count,
            source_dataset=DATASET_SLUG,
            source_points=len(point_rows),
            source_edges=len(all_edges),
            restarts=restarts,
            steps=steps,
            base_seed=base_seed,
            runtime_seconds=round(time.time() - start, 3),
            points_csv=str(points_csv),
            edges_csv=str(edges_csv),
            metadata_json=str(metadata_json),
        )
        metadata_json.write_text(
            json.dumps(
                {
                    "run": asdict(run),
                    "description": "Exact-n induced subgraph extracted from the local Stage 16/OpenAI Blueprint dataset.",
                    "samples": samples,
                    "selected_source_ids": sorted(selected),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        runs.append(run)
        print(
            f"n={n}: OpenAI exact-n best={best_edges}, "
            f"mean={mean_edges:.1f}, std={std_edges:.1f} in {run.runtime_seconds:.1f}s"
        )

    write_summary(OUTDIR / "summary_results.csv", runs)
    print(f"Wrote {OUTDIR / 'summary_results.csv'}")


if __name__ == "__main__":
    main()
