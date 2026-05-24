from pathlib import Path
import csv, json, math
import numpy as np
import collections

root = Path("n25_global_proof_search")
branch_dir = root / "subcore_021_branch_representatives"
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
outdir = root / "subcore_021_collision_quotients"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3, 12)

def read_edges_1based(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [tuple(sorted((int(r["i"]), int(r["j"])))) for r in csv.DictReader(f)]

def read_coords(path):
    return np.loadtxt(path, delimiter=",", skiprows=1)

def d2(coords, a, b):
    p = coords[a - 1]
    q = coords[b - 1]
    d = p - q
    return float(d @ d)

def collision_components(coords, threshold=1e-8):
    n = len(coords)
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            if d2(coords, i, j) <= threshold:
                union(i, j)

    groups = collections.defaultdict(list)
    for i in range(1, n + 1):
        groups[find(i)].append(i)

    comps = sorted([tuple(v) for v in groups.values()], key=lambda c: (c[0], len(c)))
    return comps

def quotient(edges, comps):
    mapping = {}
    for idx, comp in enumerate(comps, 1):
        for v in comp:
            mapping[v] = idx

    q_edges = set()
    loops = []
    edge_lifts = collections.defaultdict(list)

    for a, b in edges:
        qa, qb = mapping[a], mapping[b]
        if qa == qb:
            loops.append((a, b))
        else:
            qe = tuple(sorted((qa, qb)))
            q_edges.add(qe)
            edge_lifts[qe].append((a, b))

    target_q = tuple(sorted((mapping[TARGET[0]], mapping[TARGET[1]])))
    target_is_loop = target_q[0] == target_q[1]

    return {
        "mapping": mapping,
        "components": comps,
        "quotient_vertex_count": len(comps),
        "quotient_edge_count": len(q_edges),
        "quotient_edges": sorted(q_edges),
        "loops_from_original_edges": loops,
        "target_quotient_pair": target_q,
        "target_is_loop": target_is_loop,
        "edge_lifts": {f"{a}-{b}": lifts for (a, b), lifts in sorted(edge_lifts.items())},
    }

def write_edges(path, edges):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j"])
        w.writerows(edges)

edges = read_edges_1based(edges_path)

print("=== SUBCORE 021 COLLISION QUOTIENTS ===")
print("source edge count:", len(edges))
print("target pair:", TARGET)

summary = {}

for branch in ["d2_0", "d2_3"]:
    coords = read_coords(branch_dir / f"{branch}_coords.csv")
    comps = collision_components(coords, threshold=1e-8)
    q = quotient(edges, comps)

    target_d2 = d2(coords, *TARGET)

    print(f"\nbranch={branch}")
    print("target_d2:", target_d2)
    print("components:")
    for idx, comp in enumerate(comps, 1):
        print(f"  Q{idx}: {comp}")

    print("quotient V/E:", q["quotient_vertex_count"], q["quotient_edge_count"])
    print("original-edge loops:", q["loops_from_original_edges"] or "none")
    print("target quotient pair:", q["target_quotient_pair"], "loop:", q["target_is_loop"])
    print("quotient edges:", q["quotient_edges"])

    q_edges_path = outdir / f"{branch}_quotient_edges.csv"
    write_edges(q_edges_path, q["quotient_edges"])

    summary[branch] = {
        "target_d2": target_d2,
        **q,
        "quotient_edges_file": str(q_edges_path),
    }

(outdir / "collision_quotients_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nWROTE:")
print(outdir / "collision_quotients_summary.json")
print(outdir / "d2_0_quotient_edges.csv")
print(outdir / "d2_3_quotient_edges.csv")
