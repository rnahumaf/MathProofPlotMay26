#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent verifier for finite trilateration certificates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import mpmath as mp

Edge = tuple[int, int]
Point = tuple[mp.mpf, mp.mpf]


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


def point_key(point: Point, digits: int = 90) -> tuple[str, str]:
    return (mp.nstr(point[0], digits), mp.nstr(point[1], digits))


def candidate_valid(
    coords: dict[int, Point],
    vertex: int,
    candidate: Point,
    adj: list[set[int]],
    tolerance: mp.mpf,
) -> bool:
    for neighbor in adj[vertex]:
        if neighbor not in coords:
            continue
        if abs(squared_distance(candidate, coords[neighbor]) - 1) > tolerance:
            return False
    for other_point in coords.values():
        if squared_distance(candidate, other_point) <= tolerance * tolerance:
            return False
    return True


def replay(edges: list[Edge], certificate: dict, precision: int, tolerance_text: str) -> dict:
    mp.mp.dps = precision
    tolerance = mp.mpf(tolerance_text)
    n = infer_n(edges)
    adj = adjacency(n, edges)
    seed = tuple(v - 1 for v in certificate["seed_edge"])
    order = [(row[0] - 1, row[1] - 1, row[2] - 1) for row in certificate.get("order", [])]

    states: list[dict[int, Point]] = [
        {
            seed[0]: (mp.mpf("0"), mp.mpf("0")),
            seed[1]: (mp.mpf("1"), mp.mpf("0")),
        }
    ]
    max_width = 1

    for step_index, (vertex, a, b) in enumerate(order, 1):
        if a not in states[0] and any(a not in state for state in states):
            return {"verified": False, "reason": f"anchor {a + 1} absent at step {step_index}"}
        if b not in states[0] and any(b not in state for state in states):
            return {"verified": False, "reason": f"anchor {b + 1} absent at step {step_index}"}

        next_states: dict[tuple[tuple[int, tuple[str, str]], ...], dict[int, Point]] = {}
        for coords in states:
            for candidate in circle_intersections(coords[a], coords[b], tolerance):
                if candidate_valid(coords, vertex, candidate, adj, tolerance):
                    new_coords = dict(coords)
                    new_coords[vertex] = candidate
                    key = tuple(sorted((v, point_key(p)) for v, p in new_coords.items()))
                    next_states[key] = new_coords

        states = list(next_states.values())
        max_width = max(max_width, len(states))
        if not states:
            expected = certificate.get("status") == "eliminated"
            expected_step = certificate.get("eliminated_at_step") == step_index
            return {
                "verified": bool(expected and expected_step),
                "status": "eliminated",
                "eliminated_at_step": step_index,
                "max_width": max_width,
                "expected_status": certificate.get("status"),
                "expected_step": certificate.get("eliminated_at_step"),
            }

    return {
        "verified": certificate.get("status") == "survived",
        "status": "survived",
        "state_count": len(states),
        "max_width": max_width,
        "expected_status": certificate.get("status"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--precision", type=int, default=120)
    parser.add_argument("--tolerance", default=None)
    args = parser.parse_args()

    edges = read_edges(args.edges)
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    tolerance = args.tolerance or certificate.get("tolerance", "1e-40")
    result = replay(edges, certificate, args.precision, tolerance)
    result["edges"] = str(args.edges)
    result["certificate"] = str(args.certificate)
    result["precision_digits"] = args.precision
    result["tolerance"] = tolerance
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
