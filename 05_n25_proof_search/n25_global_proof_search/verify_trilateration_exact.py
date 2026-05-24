#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Symbolic verifier for finite trilateration certificates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import sympy as sp

Edge = tuple[int, int]
Point = tuple[sp.Expr, sp.Expr]


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


def squared_distance(a: Point, b: Point) -> sp.Expr:
    dx = sp.simplify(a[0] - b[0])
    dy = sp.simplify(a[1] - b[1])
    return sp.simplify(dx * dx + dy * dy)


def is_zero(expr: sp.Expr) -> bool:
    return sp.simplify(expr) == 0


def definitely_positive(expr: sp.Expr) -> bool:
    simplified = sp.simplify(expr)
    if simplified.is_positive is True:
        return True
    if simplified.is_zero is True:
        return False
    return bool(sp.N(simplified, 80) > 0)


def circle_intersections(a: Point, b: Point) -> list[Point]:
    dx = sp.simplify(b[0] - a[0])
    dy = sp.simplify(b[1] - a[1])
    d2 = sp.simplify(dx * dx + dy * dy)
    if is_zero(d2):
        return []
    h2 = sp.simplify(1 - d2 / 4)
    if definitely_positive(-h2):
        return []
    midpoint = (sp.simplify((a[0] + b[0]) / 2), sp.simplify((a[1] + b[1]) / 2))
    if is_zero(h2):
        return [midpoint]
    d = sp.sqrt(d2)
    h = sp.sqrt(h2)
    ux = sp.simplify(-dy / d)
    uy = sp.simplify(dx / d)
    return [
        (sp.simplify(midpoint[0] + h * ux), sp.simplify(midpoint[1] + h * uy)),
        (sp.simplify(midpoint[0] - h * ux), sp.simplify(midpoint[1] - h * uy)),
    ]


def point_key(point: Point) -> tuple[str, str]:
    return (sp.srepr(sp.simplify(point[0])), sp.srepr(sp.simplify(point[1])))


def candidate_valid(coords: dict[int, Point], vertex: int, candidate: Point, adj: list[set[int]]) -> bool:
    for neighbor in adj[vertex]:
        if neighbor not in coords:
            continue
        if not is_zero(squared_distance(candidate, coords[neighbor]) - 1):
            return False
    for other in coords.values():
        if is_zero(squared_distance(candidate, other)):
            return False
    return True


def replay(edges: list[Edge], certificate: dict) -> dict:
    n = infer_n(edges)
    adj = adjacency(n, edges)
    seed = tuple(v - 1 for v in certificate["seed_edge"])
    order = [(row[0] - 1, row[1] - 1, row[2] - 1) for row in certificate.get("order", [])]
    states: list[dict[int, Point]] = [
        {
            seed[0]: (sp.Integer(0), sp.Integer(0)),
            seed[1]: (sp.Integer(1), sp.Integer(0)),
        }
    ]
    max_width = 1

    for step_index, (vertex, a, b) in enumerate(order, 1):
        next_states: dict[tuple[tuple[int, tuple[str, str]], ...], dict[int, Point]] = {}
        for coords in states:
            for candidate in circle_intersections(coords[a], coords[b]):
                if candidate_valid(coords, vertex, candidate, adj):
                    new_coords = dict(coords)
                    new_coords[vertex] = candidate
                    key = tuple(sorted((v, point_key(p)) for v, p in new_coords.items()))
                    next_states[key] = new_coords
        states = list(next_states.values())
        max_width = max(max_width, len(states))
        if not states:
            return {
                "verified": certificate.get("status") == "eliminated"
                and certificate.get("eliminated_at_step") == step_index,
                "status": "eliminated",
                "eliminated_at_step": step_index,
                "max_width": max_width,
            }

    return {
        "verified": certificate.get("status") == "survived",
        "status": "survived",
        "state_count": len(states),
        "max_width": max_width,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    args = parser.parse_args()

    edges = read_edges(args.edges)
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    result = replay(edges, certificate)
    result["edges"] = str(args.edges)
    result["certificate"] = str(args.certificate)
    result["method"] = "sympy_exact_radical_replay"
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
