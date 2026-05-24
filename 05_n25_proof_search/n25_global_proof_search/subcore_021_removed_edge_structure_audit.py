from pathlib import Path
import csv, json, itertools, math, statistics, subprocess, sys
import collections

root = Path("n25_global_proof_search")
full_edges_path = root / "hard_subcore_exact_filter_checks" / "subcore_021_edges.csv"
runs_path = root / "subcore_021_remove_3_12_distance_audit" / "remove_3_12_distance_runs.csv"
outdir = root / "subcore_021_removed_edge_structure_audit"
outdir.mkdir(parents=True, exist_ok=True)

REMOVED = tuple(sorted((3, 12)))

def read_edges_1based(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [tuple(sorted((int(r["i"]), int(r["j"])))) for r in csv.DictReader(f)]

def neighbors(edges):
    nb = collections.defaultdict(set)
    for a, b in edges:
        nb[a].add(b)
        nb[b].add(a)
    return nb

def edge_exists(edges, a, b):
    return tuple(sorted((a, b))) in set(edges)

def run_tool(name, args):
    print(f"\n--- {name} ---")
    proc = subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    print(proc.stdout[-4000:] if len(proc.stdout) > 4000 else proc.stdout)
    return proc.stdout

full_edges = read_edges_1based(full_edges_path)
removed_edges = [e for e in full_edges if e != REMOVED]
edge_set = set(removed_edges)
nb = neighbors(removed_edges)

print("=== SUBCORE 021 REMOVED EDGE STRUCTURE AUDIT ===")
print("full edge count:", len(full_edges))
print("without 3-12 edge count:", len(removed_edges))

print("\nDegrees without 3-12:")
for v in range(1, 13):
    print(f"{v}: deg={len(nb[v])} neighbors={sorted(nb[v])}")

cn = sorted(nb[3] & nb[12])
print("\nCommon neighbors of 3 and 12:", cn)

print("\nEdges among common neighbors of 3 and 12:")
for a, b in itertools.combinations(cn, 2):
    print(f"{a}-{b}: edge={edge_exists(removed_edges, a, b)}")

print("\nPotential opposite-distance relations involving pair 3-12:")
relations = []
for a, b in itertools.combinations(cn, 2):
    ab_edge = edge_exists(removed_edges, a, b)
    relations.append({
        "opposite_pair": f"{a}-{b}",
        "ab_is_edge": ab_edge,
        "would_imply_if_ab_d2_known": "|3-12|^2 + |a-b|^2 = 4",
        "if_ab_unit_then_3_12_d2": 3 if ab_edge else None,
    })
    print(
        f"3 and 12 share {a},{b}; "
        f"{a}-{b} edge={ab_edge}; "
        f"relation: |3-12|² + |{a}-{b}|² = 4"
    )

# Salva o grafo sem 3-12.
without_path = outdir / "subcore_021_without_3_12_edges.csv"
with without_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["i", "j"])
    w.writerows(removed_edges)

# Roda filtros exatos no grafo sem 3-12.
triangle_out = run_tool(
    "triangle without 3-12",
    [
        sys.executable,
        str(root / "triangle_lattice_filter.py"),
        "--edges",
        str(without_path),
        "--max-nodes",
        "200000",
    ],
)

distance_out = run_tool(
    "distance labels without 3-12",
    [
        sys.executable,
        str(root / "distance_label_eliminator.py"),
        "--edges",
        str(without_path),
    ],
)

trilat_out = run_tool(
    "trilateration without 3-12",
    [
        sys.executable,
        str(root / "trilateration_eliminator.py"),
        "--edges",
        str(without_path),
        "--max-states",
        "200000",
        "--precision",
        "100",
        "--tolerance",
        "1e-40",
    ],
)

# Classifica os runs salvos.
with runs_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

solved = [
    r for r in rows
    if r["removed_pair_d2"] not in ("", "None", None)
    and float(r["max_abs_edge_squared_error"]) <= 1e-8
]

branches = collections.Counter()
vals = []

for r in solved:
    d2 = float(r["removed_pair_d2"])
    vals.append(d2)
    if abs(d2) <= 1e-6:
        branch = "d2≈0"
    elif abs(d2 - 3.0) <= 1e-6:
        branch = "d2≈3"
    elif abs(d2 - 1.0) <= 1e-6:
        branch = "d2≈1"
    else:
        branch = "other"
    branches[branch] += 1

print("\nRemoved-edge distance branch counts:")
for k, v in branches.most_common():
    print(f"{k}: {v}/{len(solved)} = {v/len(solved):.3f}")

print("\nD2 numeric summary:")
print("count:", len(vals))
print("min:", min(vals))
print("max:", max(vals))
print("mean:", statistics.mean(vals))
print("median:", statistics.median(vals))
print("stdev:", statistics.pstdev(vals))

metadata = {
    "full_edges": full_edges,
    "removed_edges": removed_edges,
    "removed_pair": [3, 12],
    "common_neighbors_3_12": cn,
    "relations": relations,
    "branch_counts": dict(branches),
    "d2_summary": {
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "stdev": statistics.pstdev(vals),
    },
    "interpretation": (
        "If 3 and 12 share two unit neighbors a,b and a-b is unit, then "
        "|3-12|^2 = 3 by the rhombus/opposite-chord relation. The d2≈0 branch "
        "indicates a collapsed alternative. Since no d2≈1 branch appears, edge 3-12 "
        "is a strong local contradiction candidate."
    ),
}

(outdir / "removed_edge_structure_audit.json").write_text(
    json.dumps(metadata, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nWROTE:")
print(without_path)
print(outdir / "removed_edge_structure_audit.json")
