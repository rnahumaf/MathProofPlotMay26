#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rigidity-rank analysis for numerically forced edge candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
DEFAULT_CANDIDATES = SEARCH_DIR / "rigid_forced_edge_discovery" / "forced_edge_candidates.json"
OUTDIR = SEARCH_DIR / "rigidity_closure_analyzer"

from geometric_embedder import worker as embed_worker

Edge = tuple[int, int]


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def read_full_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def witness_edges(full_edges: list[Edge], witness_vertices: list[int]) -> tuple[list[Edge], dict[int, int]]:
    vertices = sorted(v - 1 for v in witness_vertices)
    mapping = {old: new for new, old in enumerate(vertices)}
    vset = set(vertices)
    edges = [(mapping[i], mapping[j]) for i, j in full_edges if i in vset and j in vset]
    return edges, mapping


def rigidity_matrix(coords: np.ndarray, edges: list[Edge]) -> np.ndarray:
    n = coords.shape[0]
    matrix = np.zeros((len(edges), 2 * n), dtype=float)
    for row, (i, j) in enumerate(edges):
        dx = coords[i, 0] - coords[j, 0]
        dy = coords[i, 1] - coords[j, 1]
        matrix[row, 2 * i] = dx
        matrix[row, 2 * i + 1] = dy
        matrix[row, 2 * j] = -dx
        matrix[row, 2 * j + 1] = -dy
    return matrix


def numeric_rank(matrix: np.ndarray, tolerance: float) -> int:
    singular = np.linalg.svd(matrix, compute_uv=False)
    return int(np.sum(singular > tolerance))


def analyze_candidate(item: dict, full_edges: list[Edge], args: argparse.Namespace) -> dict:
    witness = item["witness"]
    forced = item["forced"]
    edges, mapping = witness_edges(full_edges, witness["vertices"])
    target_original = [forced["pair"][0] - 1, forced["pair"][1] - 1]
    if target_original[0] not in mapping or target_original[1] not in mapping:
        return {"pair": forced["pair"], "status": "target_not_in_witness"}
    target = normalize_edge(mapping[target_original[0]], mapping[target_original[1]])
    rows = [
        embed_worker((args.seed + i * 104729, edges, len(mapping), args.max_nfev, args.scale))
        for i in range(args.runs)
    ]
    best = min(rows, key=lambda row: row["max_abs_edge_squared_error"])
    coords = np.array(best["coords"], dtype=float)
    base_rank = numeric_rank(rigidity_matrix(coords, edges), args.rank_tolerance)
    augmented_edges = sorted(set(edges).union({target}))
    augmented_rank = numeric_rank(rigidity_matrix(coords, augmented_edges), args.rank_tolerance)
    max_rank = 2 * len(mapping) - 3
    return {
        "pair": forced["pair"],
        "witness_vertices": witness["vertices"],
        "witness_edge_count": len(edges),
        "witness_vertex_count": len(mapping),
        "best_max_abs": best["max_abs_edge_squared_error"],
        "base_rank": base_rank,
        "augmented_rank": augmented_rank,
        "max_planar_rigidity_rank": max_rank,
        "is_infinitesimally_rigid": base_rank == max_rank,
        "target_in_rigidity_closure": augmented_rank == base_rank,
        "forced_mean_squared_distance": forced["mean_squared_distance"],
        "forced_spread": forced["spread"],
        "triangle_lattice_eliminated_after_augment": item["augmented_check"]["triangle_lattice_eliminated"],
        "trilateration_status_after_augment": item["augmented_check"]["trilateration_status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--full-edges", type=Path, default=SEARCH_DIR / "non_trilaterable_maximality" / "non_trilaterable_search_best_edges.csv")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--max-nfev", type=int, default=30000)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--rank-tolerance", type=float, default=1e-7)
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    full_edges = read_full_edges(args.full_edges)
    rows = [analyze_candidate(item, full_edges, args) for item in candidates]
    rows.sort(
        key=lambda row: (
            not row.get("target_in_rigidity_closure", False),
            not row.get("triangle_lattice_eliminated_after_augment", False),
            row.get("forced_spread", 1),
        )
    )

    (OUTDIR / "rigidity_closure_details.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (OUTDIR / "rigidity_closure_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "pair",
            "witness_vertex_count",
            "witness_edge_count",
            "base_rank",
            "augmented_rank",
            "max_planar_rigidity_rank",
            "is_infinitesimally_rigid",
            "target_in_rigidity_closure",
            "forced_spread",
            "triangle_lattice_eliminated_after_augment",
            "trilateration_status_after_augment",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["pair"] = " ".join(map(str, row.get("pair", [])))
            writer.writerow(row)

    metadata = {
        "candidate_count": len(rows),
        "closure_count": sum(1 for row in rows if row.get("target_in_rigidity_closure")),
        "rigid_witness_count": sum(1 for row in rows if row.get("is_infinitesimally_rigid")),
        "closure_and_global_elimination_count": sum(
            1
            for row in rows
            if row.get("target_in_rigidity_closure")
            and (
                row.get("triangle_lattice_eliminated_after_augment")
                or row.get("trilateration_status_after_augment") == "eliminated"
            )
        ),
        "interpretation": "Numerical rigidity closure; targets still need exact/interval certification.",
    }
    (OUTDIR / "rigidity_closure_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
