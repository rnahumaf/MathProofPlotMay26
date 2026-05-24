#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interval-arithmetic verifier for trilateration certificates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import mpmath as mp

Edge = tuple[int, int]
Point = tuple[mp.iv.mpf, mp.iv.mpf]


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


def singleton(value: str) -> mp.iv.mpf:
    return mp.iv.mpf([value, value])


def interval_upper(x: mp.iv.mpf) -> mp.mpf:
    return mp.mpf(x.b)


def interval_lower(x: mp.iv.mpf) -> mp.mpf:
    return mp.mpf(x.a)


def contains(x: mp.iv.mpf, value: mp.mpf) -> bool:
    return interval_lower(x) <= value <= interval_upper(x)


def squared_distance(a: Point, b: Point) -> mp.iv.mpf:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def circle_intersections(a: Point, b: Point) -> list[Point]:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    d2 = dx * dx + dy * dy
    if interval_lower(d2) <= 0 <= interval_upper(d2):
        return []
    d = mp.iv.sqrt(d2)
    if interval_lower(d) > 2:
        return []
    h2 = 1 - d2 / 4
    if interval_upper(h2) < 0:
        return []
    if interval_lower(h2) < 0:
        h2 = mp.iv.mpf([0, interval_upper(h2)])
    midpoint = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if contains(h2, mp.mpf("0")) and interval_upper(abs(h2)) == 0:
        return [midpoint]
    h = mp.iv.sqrt(h2)
    ux = -dy / d
    uy = dx / d
    return [
        (midpoint[0] + h * ux, midpoint[1] + h * uy),
        (midpoint[0] - h * ux, midpoint[1] - h * uy),
    ]


def point_key(point: Point, digits: int = 40) -> tuple[str, str, str, str]:
    return (
        mp.nstr(interval_lower(point[0]), digits),
        mp.nstr(interval_upper(point[0]), digits),
        mp.nstr(interval_lower(point[1]), digits),
        mp.nstr(interval_upper(point[1]), digits),
    )


def candidate_may_be_valid(
    coords: dict[int, Point],
    vertex: int,
    candidate: Point,
    adj: list[set[int]],
    collision_tolerance: mp.mpf,
) -> bool:
    one = mp.mpf("1")
    for neighbor in adj[vertex]:
        if neighbor not in coords:
            continue
        d2 = squared_distance(candidate, coords[neighbor])
        if not contains(d2, one):
            return False
    collision_limit = collision_tolerance * collision_tolerance
    for other in coords.values():
        d2 = squared_distance(candidate, other)
        if interval_upper(d2) <= collision_limit:
            return False
    return True


def replay(edges: list[Edge], certificate: dict, precision: int, collision_tolerance_text: str) -> dict:
    mp.mp.dps = precision
    collision_tolerance = mp.mpf(collision_tolerance_text)
    n = infer_n(edges)
    adj = adjacency(n, edges)
    seed = tuple(v - 1 for v in certificate["seed_edge"])
    order = [(row[0] - 1, row[1] - 1, row[2] - 1) for row in certificate.get("order", [])]

    states: list[dict[int, Point]] = [
        {
            seed[0]: (singleton("0"), singleton("0")),
            seed[1]: (singleton("1"), singleton("0")),
        }
    ]
    max_width = 1
    inconclusive_step = None

    for step_index, (vertex, a, b) in enumerate(order, 1):
        next_states: dict[tuple[tuple[int, tuple[str, str, str, str]], ...], dict[int, Point]] = {}
        for coords in states:
            for candidate in circle_intersections(coords[a], coords[b]):
                if candidate_may_be_valid(coords, vertex, candidate, adj, collision_tolerance):
                    new_coords = dict(coords)
                    new_coords[vertex] = candidate
                    key = tuple(sorted((v, point_key(p)) for v, p in new_coords.items()))
                    next_states[key] = new_coords
        states = list(next_states.values())
        max_width = max(max_width, len(states))
        if len(states) > 1000 and inconclusive_step is None:
            inconclusive_step = step_index
        if not states:
            return {
                "verified": certificate.get("status") == "eliminated",
                "status": "eliminated",
                "eliminated_at_step": step_index,
                "certificate_eliminated_at_step": certificate.get("eliminated_at_step"),
                "max_width": max_width,
                "method": "interval_replay",
            }

    return {
        "verified": certificate.get("status") == "survived",
        "status": "survived_or_inconclusive",
        "state_count": len(states),
        "max_width": max_width,
        "inconclusive_step": inconclusive_step,
        "method": "interval_replay",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--precision", type=int, default=120)
    parser.add_argument("--collision-tolerance", default="1e-30")
    args = parser.parse_args()

    edges = read_edges(args.edges)
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    result = replay(edges, certificate, args.precision, args.collision_tolerance)
    result["edges"] = str(args.edges)
    result["certificate"] = str(args.certificate)
    result["precision_digits"] = args.precision
    result["collision_tolerance"] = args.collision_tolerance
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
