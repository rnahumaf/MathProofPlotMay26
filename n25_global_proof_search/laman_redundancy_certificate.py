#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and verify exact Laman certificates for redundant rigidity."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "n25_global_proof_search"
OUTDIR = SEARCH_DIR / "laman_redundancy_certificate"
DEFAULT_EDGES = SEARCH_DIR / "rigid_forced_edge_discovery" / "audit_forced_2_3_witness_edges.csv"

Edge = tuple[int, int]


def normalize_edge(i: int, j: int) -> Edge:
    return (i, j) if i < j else (j, i)


def read_edges(path: Path) -> list[Edge]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_edge(int(row["i"]), int(row["j"])) for row in reader]


def is_laman(vertices: list[int], edges: list[Edge]) -> bool:
    n = len(vertices)
    if len(edges) != 2 * n - 3:
        return False
    vertex_set = set(vertices)
    if any(i not in vertex_set or j not in vertex_set for i, j in edges):
        return False
    for size in range(2, n + 1):
        for subset in itertools.combinations(vertices, size):
            s = set(subset)
            inside = sum(1 for i, j in edges if i in s and j in s)
            if inside > 2 * size - 3:
                return False
    return True


def find_laman_subgraph(vertices: list[int], edges: list[Edge]) -> list[Edge] | None:
    needed = 2 * len(vertices) - 3
    for combo in itertools.combinations(edges, needed):
        candidate = list(combo)
        if is_laman(vertices, candidate):
            return candidate
    return None


def graph_connectivity(vertices: list[int], edges: list[Edge]) -> dict:
    graph = nx.Graph()
    graph.add_nodes_from(vertices)
    graph.add_edges_from(edges)
    return {
        "node_connectivity": nx.node_connectivity(graph),
        "edge_connectivity": nx.edge_connectivity(graph),
        "is_3_connected": nx.node_connectivity(graph) >= 3,
    }


def build_certificate(edges: list[Edge]) -> dict:
    vertices = sorted({v for edge in edges for v in edge})
    base = find_laman_subgraph(vertices, edges)
    if base is None:
        raise RuntimeError("Full graph does not contain a Laman spanning subgraph")

    removals = []
    for edge in edges:
        remaining = [item for item in edges if item != edge]
        laman = find_laman_subgraph(vertices, remaining)
        if laman is None:
            removals.append({"removed_edge": list(edge), "laman_subgraph": None})
        else:
            removals.append({"removed_edge": list(edge), "laman_subgraph": [list(item) for item in laman]})

    return {
        "vertices": vertices,
        "edge_count": len(edges),
        "edges": [list(edge) for edge in edges],
        "connectivity": graph_connectivity(vertices, edges),
        "base_laman_subgraph": [list(edge) for edge in base],
        "edge_removal_certificates": removals,
        "is_redundantly_rigid_by_laman_certificates": all(item["laman_subgraph"] is not None for item in removals),
        "generic_global_rigidity_by_3_connected_redundant_rigidity": (
            graph_connectivity(vertices, edges)["is_3_connected"]
            and all(item["laman_subgraph"] is not None for item in removals)
        ),
        "theorem_used": (
            "In the plane, a graph is generically globally rigid iff it is "
            "3-connected and redundantly rigid (Jackson-Jordan). Laman "
            "subgraphs certify generic rigidity."
        ),
    }


def verify_certificate(certificate: dict) -> dict:
    vertices = [int(v) for v in certificate["vertices"]]
    edges = [normalize_edge(int(i), int(j)) for i, j in certificate["edges"]]
    edge_set = set(edges)
    failures = []

    if not is_laman(vertices, [normalize_edge(*edge) for edge in certificate["base_laman_subgraph"]]):
        failures.append("base_laman_subgraph_invalid")

    for item in certificate["edge_removal_certificates"]:
        removed = normalize_edge(*item["removed_edge"])
        laman_raw = item["laman_subgraph"]
        if laman_raw is None:
            failures.append(f"missing_laman_after_removing_{removed}")
            continue
        laman = [normalize_edge(*edge) for edge in laman_raw]
        if removed in laman:
            failures.append(f"removed_edge_present_{removed}")
        if any(edge not in edge_set for edge in laman):
            failures.append(f"foreign_edge_after_removing_{removed}")
        if not is_laman(vertices, laman):
            failures.append(f"invalid_laman_after_removing_{removed}")

    connectivity = graph_connectivity(vertices, edges)
    return {
        "verified": not failures and connectivity["is_3_connected"],
        "failure_count": len(failures),
        "failures": failures[:20],
        "connectivity": connectivity,
        "edge_removal_certificate_count": len(certificate["edge_removal_certificates"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--verify", type=Path, default=None)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.verify is not None:
        certificate = json.loads(args.verify.read_text(encoding="utf-8"))
        result = verify_certificate(certificate)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if not result["verified"]:
            raise SystemExit(1)
        return

    certificate = build_certificate(read_edges(args.edges))
    out_path = OUTDIR / f"{args.edges.stem}_laman_redundancy_certificate.json"
    out_path.write_text(json.dumps(certificate, indent=2, ensure_ascii=False), encoding="utf-8")
    result = verify_certificate(certificate)
    print(json.dumps({**result, "certificate": str(out_path)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
