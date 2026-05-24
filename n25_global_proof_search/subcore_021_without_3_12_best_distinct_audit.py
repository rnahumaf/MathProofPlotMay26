from pathlib import Path
import csv, json, math
import numpy as np

from distinct_geometric_embedder import worker as distinct_worker

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
runs_path = root / "subcore_021_without_3_12_distinct_sweep" / "without_3_12_distinct_sweep_runs.csv"
outdir = root / "subcore_021_without_3_12_best_distinct_audit"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3 - 1, 12 - 1)

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def d2(coords, a, b):
    p = np.array(coords[a], dtype=float)
    q = np.array(coords[b], dtype=float)
    d = p - q
    return float(d @ d)

def pair_table(coords, edges):
    edge_set = {tuple(sorted(e)) for e in edges}
    rows = []
    n = len(coords)
    for i in range(n):
        for j in range(i + 1, n):
            value = d2(coords, i, j)
            rows.append({
                "pair": f"{i+1}-{j+1}",
                "i": i + 1,
                "j": j + 1,
                "is_edge": tuple(sorted((i, j))) in edge_set,
                "d2": value,
                "dist": math.sqrt(max(value, 0.0)),
                "abs_to_0": abs(value),
                "abs_to_1": abs(value - 1.0),
                "abs_to_3": abs(value - 3.0),
            })
    return rows

def edge_residuals(coords, edges):
    rows = []
    for i, j in edges:
        value = d2(coords, i, j)
        rows.append({
            "edge": f"{i+1}-{j+1}",
            "i": i + 1,
            "j": j + 1,
            "d2": value,
            "err": value - 1.0,
            "abs_err": abs(value - 1.0),
        })
    return sorted(rows, key=lambda r: -r["abs_err"])

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

edges = read_edges(edges_path)
n = max(max(i, j) for i, j in edges) + 1

with runs_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Auditar os melhores casos factíveis de sep=0.01 e sep=0.02.
candidates = []
for r in rows:
    sep = float(r["min_separation"])
    weight = float(r["collision_weight"])
    min_dist = float(r["min_pair_distance"])
    err = float(r["max_abs_edge_squared_error"])

    if sep in (0.01, 0.02) and min_dist >= 0.95 * sep:
        r["_sep"] = sep
        r["_weight"] = weight
        r["_err"] = err
        candidates.append(r)

selected = []
for sep in (0.01, 0.02):
    subset = [r for r in candidates if r["_sep"] == sep]
    subset.sort(key=lambda r: r["_err"])
    selected.extend(subset[:5])

print("=== SUBCORE 021 WITHOUT 3-12 BEST DISTINCT AUDIT ===")

summary = []

for idx, r in enumerate(selected, 1):
    sep = float(r["min_separation"])
    weight = float(r["collision_weight"])
    seed = int(r["seed"])

    task = (
        seed,
        edges,
        n,
        160000,
        4.0,
        sep,
        weight,
        0.1,
    )
    rep = distinct_worker(task)
    coords = np.array(rep["coords"], dtype=float)

    pairs = pair_table(coords, edges)
    nearest = sorted(pairs, key=lambda x: x["dist"])[:15]
    residuals = edge_residuals(coords, edges)[:12]

    target = d2(coords, TARGET[0], TARGET[1])

    print(
        f"\ncase={idx} sep={sep} w={weight} seed={seed} "
        f"max_abs={rep['max_abs_edge_squared_error']:.6e} "
        f"rms={rep['rms_edge_squared_error']:.6e} "
        f"min_dist={rep['min_pair_distance']:.6e} "
        f"d2_3_12={target:.12e}"
    )

    print("nearest pairs:")
    for p in nearest[:10]:
        print(
            f"  {p['pair']}: dist={p['dist']:.6e} "
            f"d2={p['d2']:.6e} edge={p['is_edge']}"
        )

    print("top residual edges:")
    for e in residuals[:10]:
        print(f"  {e['edge']}: d2={e['d2']:.9f} err={e['err']:+.6e}")

    case_dir = outdir / f"case_{idx:02d}_sep_{str(sep).replace('.', 'p')}_w_{int(weight)}"
    case_dir.mkdir(exist_ok=True)
    np.savetxt(case_dir / "coords.csv", coords, delimiter=",", header="x,y", comments="")
    write_csv(case_dir / "pair_distances.csv", sorted(pairs, key=lambda x: x["dist"]))
    write_csv(case_dir / "edge_residuals.csv", edge_residuals(coords, edges))

    summary.append({
        "case": idx,
        "sep": sep,
        "weight": weight,
        "seed": seed,
        "max_abs": rep["max_abs_edge_squared_error"],
        "rms": rep["rms_edge_squared_error"],
        "min_pair_distance": rep["min_pair_distance"],
        "d2_3_12": target,
        "nearest_pairs": nearest[:10],
        "top_residual_edges": residuals[:10],
    })

(outdir / "best_distinct_audit_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nWROTE:")
print(outdir / "best_distinct_audit_summary.json")
