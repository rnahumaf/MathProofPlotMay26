#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exact triangular-lattice filter for abstract unit-distance candidates.

Every triangle in a planar unit-distance graph is an equilateral triangle. If
two equilateral triangles share an edge, the third vertex of the second
triangle is forced to one of the two triangular-lattice positions over that
edge. Therefore, each edge-connected component of the triangle hypergraph has
an exact embedding problem in the triangular lattice.

This is only a necessary filter. Passing it does not prove that the full graph
is embeddable, because parts not connected by shared triangle edges can rotate
freely in a genuine realization.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
POOL = SEARCH_DIR / "candidate_pool"
OUTDIR = SEARCH_DIR / "triangle_lattice_filter"

Axial = tuple[int, int]
Triangle = tuple[int, int, int]
Edge = tuple[int, int]

UNIT_DIRS: set[Axial] = {
    (1, 0),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (0, -1),
    (1, -1),
}


@dataclass(frozen=True)
class ComponentResult:
    component_index: int
    triangle_count: int
    vertex_count: int
    internal_edge_count: int
    satisfiable: bool
    assigned_vertex_count: int
    search_nodes: int
    reason: str


def default_worker_count() -> int:
    return max(1, (os.cpu_count() or 2) - 1)


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def add(a: Axial, b: Axial) -> Axial:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Axial, b: Axial) -> Axial:
    return (a[0] - b[0], a[1] - b[1])


def rot60(v: Axial) -> Axial:
    q, r = v
    return (-r, q + r)


def rot_minus60(v: Axial) -> Axial:
    q, r = v
    return (q + r, -q)


def is_unit_delta(v: Axial) -> bool:
    return v in UNIT_DIRS


def read_class_summary() -> list[dict]:
    with (POOL / "candidate_classes.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (-int(row["edge_count"]), int(row["class_id"])))
    return rows


def read_edges(class_id: int, edge_count: int) -> list[Edge]:
    path = POOL / f"class_{class_id:04d}_e{edge_count}_edges.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def read_edges_path(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def adjacency_from_edges(n: int, edges: list[Edge]) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def find_triangles(adj: list[set[int]]) -> list[Triangle]:
    triangles: list[Triangle] = []
    n = len(adj)
    for a in range(n):
        for b in sorted(v for v in adj[a] if v > a):
            common = adj[a].intersection(adj[b])
            for c in sorted(v for v in common if v > b):
                triangles.append((a, b, c))
    return triangles


def triangle_edges(triangle: Triangle) -> tuple[Edge, Edge, Edge]:
    a, b, c = triangle
    return normalize_edge(a, b), normalize_edge(a, c), normalize_edge(b, c)


def triangle_components(triangles: list[Triangle]) -> list[list[Triangle]]:
    by_edge: dict[Edge, list[int]] = {}
    for index, triangle in enumerate(triangles):
        for edge in triangle_edges(triangle):
            by_edge.setdefault(edge, []).append(index)

    tri_adj = [set() for _ in triangles]
    for indices in by_edge.values():
        if len(indices) < 2:
            continue
        for i in indices:
            tri_adj[i].update(j for j in indices if j != i)

    components: list[list[Triangle]] = []
    seen: set[int] = set()
    for start in range(len(triangles)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component: list[Triangle] = []
        while stack:
            idx = stack.pop()
            component.append(triangles[idx])
            for nxt in tri_adj[idx]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(component)
    return components


def third_vertex_candidates(a_coord: Axial, b_coord: Axial) -> list[Axial]:
    delta = sub(b_coord, a_coord)
    if not is_unit_delta(delta):
        return []
    return [add(a_coord, rot60(delta)), add(a_coord, rot_minus60(delta))]


def validate_triangle(coords: dict[int, Axial], triangle: Triangle) -> bool:
    a, b, c = triangle
    return (
        is_unit_delta(sub(coords[a], coords[b]))
        and is_unit_delta(sub(coords[a], coords[c]))
        and is_unit_delta(sub(coords[b], coords[c]))
    )


def find_branch(
    triangles: list[Triangle],
    coords: dict[int, Axial],
) -> tuple[Triangle, int, list[Axial]] | None | bool:
    best: tuple[Triangle, int, list[Axial]] | None = None
    occupied = {coord: vertex for vertex, coord in coords.items()}

    for triangle in triangles:
        assigned = [v for v in triangle if v in coords]
        if len(assigned) == 3:
            if not validate_triangle(coords, triangle):
                return False
            continue
        if len(assigned) != 2:
            continue

        missing = next(v for v in triangle if v not in coords)
        a, b = assigned
        candidates = third_vertex_candidates(coords[a], coords[b])
        if not candidates:
            return False
        filtered = [
            candidate
            for candidate in candidates
            if candidate not in occupied or occupied[candidate] == missing
        ]
        if not filtered:
            return False
        if best is None or len(filtered) < len(best[2]):
            best = (triangle, missing, filtered)

    return best


def internal_edges(vertices: set[int], edges: list[Edge]) -> list[Edge]:
    return [(i, j) for i, j in edges if i in vertices and j in vertices]


def solve_component(
    component_index: int,
    triangles: list[Triangle],
    graph_edges: list[Edge],
    max_nodes: int,
) -> ComponentResult:
    vertices = set(v for triangle in triangles for v in triangle)
    edges_inside = internal_edges(vertices, graph_edges)
    seed = triangles[0]
    base_coords: dict[int, Axial] = {
        seed[0]: (0, 0),
        seed[1]: (1, 0),
        seed[2]: (0, 1),
    }
    nodes = 0
    best_assigned = len(base_coords)

    def search(coords: dict[int, Axial]) -> tuple[bool, int, str]:
        nonlocal nodes, best_assigned
        nodes += 1
        best_assigned = max(best_assigned, len(coords))
        if nodes > max_nodes:
            return False, len(coords), "node_limit"

        branch = find_branch(triangles, coords)
        if branch is False:
            return False, len(coords), "triangle_contradiction"

        if branch is None:
            if any(v not in coords for v in vertices):
                return False, len(coords), "unpropagated_triangle_component"
            occupied: dict[Axial, int] = {}
            for vertex, coord in coords.items():
                if coord in occupied and occupied[coord] != vertex:
                    return False, len(coords), "collision"
                occupied[coord] = vertex
            for i, j in edges_inside:
                if not is_unit_delta(sub(coords[i], coords[j])):
                    return False, len(coords), "internal_edge_not_unit"
            return True, len(coords), "satisfied"

        _, missing, candidates = branch
        last_reason = "exhausted"
        for candidate in candidates:
            next_coords = dict(coords)
            next_coords[missing] = candidate
            ok, assigned, reason = search(next_coords)
            best_assigned = max(best_assigned, assigned)
            if ok:
                return True, assigned, reason
            last_reason = reason
        return False, best_assigned, last_reason

    satisfiable, assigned, reason = search(base_coords)
    return ComponentResult(
        component_index=component_index,
        triangle_count=len(triangles),
        vertex_count=len(vertices),
        internal_edge_count=len(edges_inside),
        satisfiable=satisfiable,
        assigned_vertex_count=assigned,
        search_nodes=nodes,
        reason=reason,
    )


def analyze_graph(class_id: int, edge_count: int, n: int, max_nodes: int) -> dict:
    edges = read_edges(class_id, edge_count)
    return analyze_edges(edges, class_id, edge_count, n, max_nodes)


def analyze_edges(edges: list[Edge], class_id: int | str, edge_count: int, n: int, max_nodes: int) -> dict:
    adj = adjacency_from_edges(n, edges)
    triangles = find_triangles(adj)
    components = triangle_components(triangles)

    component_results = [
        solve_component(index + 1, component, edges, max_nodes=max_nodes)
        for index, component in enumerate(components)
    ]
    eliminated = any(not result.satisfiable for result in component_results)
    largest = max((result.vertex_count for result in component_results), default=0)
    total_nodes = sum(result.search_nodes for result in component_results)
    first_failure = next((result for result in component_results if not result.satisfiable), None)

    return {
        "class_id": class_id,
        "edge_count": edge_count,
        "triangle_count": len(triangles),
        "triangle_component_count": len(components),
        "largest_component_vertices": largest,
        "eliminated": eliminated,
        "failure_component": first_failure.component_index if first_failure else "",
        "failure_reason": first_failure.reason if first_failure else "",
        "search_nodes": total_nodes,
        "components": [result.__dict__ for result in component_results],
    }


def worker(task: tuple[int, int, int, int]) -> dict:
    class_id, edge_count, n, max_nodes = task
    return analyze_graph(class_id, edge_count, n, max_nodes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=None)
    parser.add_argument("--classes", type=int, default=100)
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--max-nodes", type=int, default=200000)
    parser.add_argument("--workers", type=int, default=default_worker_count())
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.edges is not None:
        edges = read_edges_path(args.edges)
        result = analyze_edges(edges, args.edges.stem, len(edges), args.n, args.max_nodes)
        slug = args.edges.stem
        (OUTDIR / f"{slug}_triangle_lattice_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    class_rows = read_class_summary()[: args.classes]
    tasks = [
        (int(row["class_id"]), int(row["edge_count"]), args.n, args.max_nodes)
        for row in class_rows
    ]

    rows: list[dict] = []
    actual_workers = min(args.workers, len(tasks)) if tasks else 1
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            status = "eliminated" if row["eliminated"] else "passed"
            print(
                f"class {row['class_id']} e={row['edge_count']}: {status}, "
                f"triangles={row['triangle_count']}, nodes={row['search_nodes']}",
                flush=True,
            )

    rows.sort(key=lambda row: (not row["eliminated"], -row["edge_count"], row["class_id"]))
    with (OUTDIR / "triangle_lattice_filter_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "class_id",
            "edge_count",
            "triangle_count",
            "triangle_component_count",
            "largest_component_vertices",
            "eliminated",
            "failure_component",
            "failure_reason",
            "search_nodes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})

    (OUTDIR / "triangle_lattice_filter_details.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata = {
        "classes_tested": len(rows),
        "eliminated_count": sum(1 for row in rows if row["eliminated"]),
        "passed_count": sum(1 for row in rows if not row["eliminated"]),
        "workers": actual_workers,
        "logical_processors": os.cpu_count(),
        "max_nodes_per_component": args.max_nodes,
        "interpretation": (
            "Exact necessary filter on edge-connected triangle components. "
            "Eliminated classes cannot be unit-distance graphs; passed classes "
            "still need continuous geometric elimination."
        ),
    }
    (OUTDIR / "triangle_lattice_filter_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
