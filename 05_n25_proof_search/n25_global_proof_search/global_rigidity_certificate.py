#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global-rigidity evidence/certificate builder for a witness graph.

For a graph in the plane, generic global rigidity is characterized by
3-connectivity and redundant rigidity. This script checks both combinatorially
up to numeric generic rigidity rank. It also computes a numeric equilibrium
stress matrix at a sampled unit-distance realization as stronger audit data.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
OUTDIR = SEARCH_DIR / "global_rigidity_certificate"
DEFAULT_EDGES = SEARCH_DIR / "rigid_forced_edge_discovery" / "audit_forced_2_3_witness_edges.csv"

from geometric_embedder import worker as embed_worker

Edge = tuple[int, int]


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]) - 1, int(row["j"]) - 1) for row in reader]


def remap_edges(edges: list[Edge]) -> tuple[list[Edge], dict[int, int], dict[int, int]]:
    vertices = sorted({v for edge in edges for v in edge})
    mapping = {old: index for index, old in enumerate(vertices)}
    reverse = {index: old for old, index in mapping.items()}
    return [(mapping[i], mapping[j]) for i, j in edges], mapping, reverse


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


def graph_from_edges(n: int, edges: list[Edge], reverse: dict[int, int]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(reverse[i] + 1 for i in range(n))
    graph.add_edges_from((reverse[i] + 1, reverse[j] + 1) for i, j in edges)
    return graph


def generic_rank(edges: list[Edge], n: int, seed: int, tolerance: float) -> int:
    rng = np.random.default_rng(seed)
    coords = rng.normal(size=(n, 2))
    return numeric_rank(rigidity_matrix(coords, edges), tolerance)


def redundant_rigidity(edges: list[Edge], n: int, seed: int, tolerance: float) -> dict:
    max_rank = 2 * n - 3
    full_rank = generic_rank(edges, n, seed, tolerance)
    failures = []
    for index, edge in enumerate(edges):
        reduced = edges[:index] + edges[index + 1 :]
        rank = generic_rank(reduced, n, seed + 1009 * (index + 1), tolerance)
        if rank < max_rank:
            failures.append({"removed_edge": [edge[0], edge[1]], "rank": rank})
    return {
        "max_rank": max_rank,
        "full_rank": full_rank,
        "is_rigid": full_rank == max_rank,
        "is_redundantly_rigid": full_rank == max_rank and not failures,
        "redundancy_failures": failures,
    }


def stress_matrix(coords: np.ndarray, edges: list[Edge], rank_tolerance: float) -> dict:
    rmat = rigidity_matrix(coords, edges)
    # A self-stress is in the left nullspace of the rigidity matrix.
    u, singular, _ = np.linalg.svd(rmat, full_matrices=True)
    rank = int(np.sum(singular > rank_tolerance))
    stress_basis = u[:, rank:]
    n = coords.shape[0]
    stress_rank_target = n - 3
    best = None
    if stress_basis.shape[1] == 0:
        return {
            "stress_space_dimension": 0,
            "psd_stress_found": False,
        }

    # Search small linear combinations for a nearly PSD stress matrix with high rank.
    rng = np.random.default_rng(20260524)
    candidates = []
    for column in range(stress_basis.shape[1]):
        vec = stress_basis[:, column]
        candidates.extend([vec, -vec])
    for _ in range(2000):
        coeffs = rng.normal(size=stress_basis.shape[1])
        candidates.append(stress_basis @ coeffs)

    for stress in candidates:
        omega = np.zeros((n, n), dtype=float)
        for value, (i, j) in zip(stress, edges):
            omega[i, j] -= value
            omega[j, i] -= value
            omega[i, i] += value
            omega[j, j] += value
        eig = np.linalg.eigvalsh((omega + omega.T) / 2)
        min_eig = float(np.min(eig))
        positive_rank = int(np.sum(eig > 1e-7))
        score = (min_eig, positive_rank)
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "min_eigenvalue": min_eig,
                "positive_rank": positive_rank,
                "eigenvalues": eig.tolist(),
            }
    return {
        "stress_space_dimension": int(stress_basis.shape[1]),
        "psd_stress_found": bool(best and best["min_eigenvalue"] >= -1e-8 and best["positive_rank"] >= stress_rank_target),
        "target_stress_rank": stress_rank_target,
        **({k: v for k, v in best.items() if k != "score"} if best else {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--target-pair", nargs=2, type=int, default=[2, 3])
    parser.add_argument("--rank-tolerance", type=float, default=1e-7)
    parser.add_argument("--runs", type=int, default=80)
    parser.add_argument("--max-nfev", type=int, default=30000)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=20260524)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    original_edges = read_edges(args.edges)
    edges, mapping, reverse = remap_edges(original_edges)
    n = len(mapping)
    graph = graph_from_edges(n, edges, reverse)
    redundancy = redundant_rigidity(edges, n, args.seed, args.rank_tolerance)

    rows = [
        embed_worker((args.seed + i * 104729, edges, n, args.max_nfev, args.scale))
        for i in range(args.runs)
    ]
    best = min(rows, key=lambda row: row["max_abs_edge_squared_error"])
    coords = np.array(best["coords"], dtype=float)
    target_original = [value - 1 for value in args.target_pair]
    target = [mapping[value] for value in target_original]
    dx = coords[target[0], 0] - coords[target[1], 0]
    dy = coords[target[0], 1] - coords[target[1], 1]
    target_distance_squared = float(dx * dx + dy * dy)

    result = {
        "source_edges": str(args.edges),
        "original_vertices": [reverse[i] + 1 for i in range(n)],
        "n": n,
        "edge_count": len(edges),
        "node_connectivity": nx.node_connectivity(graph),
        "edge_connectivity": nx.edge_connectivity(graph),
        "is_3_connected": nx.node_connectivity(graph) >= 3,
        "redundant_rigidity": redundancy,
        "generic_global_rigidity_by_hendrickson_jackson_jordan": (
            nx.node_connectivity(graph) >= 3 and redundancy["is_redundantly_rigid"]
        ),
        "unit_realization_best_max_abs": best["max_abs_edge_squared_error"],
        "target_pair": args.target_pair,
        "target_distance_squared_in_sample": target_distance_squared,
        "stress_matrix": stress_matrix(coords, edges, args.rank_tolerance),
        "interpretation": (
            "Generic global rigidity is a combinatorial theorem for generic "
            "frameworks. The sampled unit framework is special, so this is a "
            "strong proof-search certificate but not yet a standalone proof "
            "that every unit realization forces the target pair."
        ),
    }
    (OUTDIR / "forced_2_3_global_rigidity_certificate.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
