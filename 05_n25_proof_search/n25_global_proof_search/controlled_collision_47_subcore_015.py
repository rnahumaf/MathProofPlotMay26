from pathlib import Path
import csv, json, math
import numpy as np
from scipy.optimize import least_squares

root = Path("n25_global_proof_search")
edges_path = root / "collision_forced_subcore_audit" / "target_subcore_015_edges.csv"
coords_path = root / "refine_subcore_015_best_distinct" / "best_refined_coords.csv"
outdir = root / "controlled_collision_47_subcore_015"
outdir.mkdir(parents=True, exist_ok=True)

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def edge_errors(coords, edges):
    vals = []
    for i, j in edges:
        d = coords[i] - coords[j]
        vals.append(float(d @ d - 1.0))
    arr = np.array(vals)
    return float(np.max(np.abs(arr))), float(np.sqrt(np.mean(arr * arr)))

def min_pair_distance(coords):
    best = 1e99
    pair = None
    all_pairs = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = float(np.linalg.norm(coords[i] - coords[j]))
            all_pairs.append((d, i + 1, j + 1))
            if d < best:
                best = d
                pair = (i + 1, j + 1)
    return best, pair, sorted(all_pairs)[:10]

def encode(coords, fixed_edge):
    vals = []
    for i in range(len(coords)):
        if i in fixed_edge:
            continue
        vals.extend([coords[i, 0], coords[i, 1]])
    return np.array(vals, dtype=float)

def decode(vals, n, fixed_edge):
    coords = np.zeros((n, 2), dtype=float)
    a, b = fixed_edge
    coords[a] = [0.0, 0.0]
    coords[b] = [1.0, 0.0]
    k = 0
    for i in range(n):
        if i in fixed_edge:
            continue
        coords[i] = [vals[k], vals[k + 1]]
        k += 2
    return coords

def residuals(vals, n, edges, fixed_edge, target_pair, target_delta, target_weight):
    coords = decode(vals, n, fixed_edge)
    out = []

    for i, j in edges:
        d = coords[i] - coords[j]
        out.append(float(d @ d - 1.0))

    a, b = target_pair
    d = coords[a] - coords[b]
    out.append(target_weight * float(d @ d - target_delta * target_delta))

    return np.array(out, dtype=float)

edges = read_edges(edges_path)
coords = np.loadtxt(coords_path, delimiter=",", skiprows=1)
n = len(coords)

fixed_edge = edges[0]
target_pair = (4 - 1, 7 - 1)

x = encode(coords, fixed_edge)

schedule = [
    0.009,
    0.007,
    0.005,
    0.003,
    0.002,
    0.001,
    0.0005,
    0.0002,
    0.0001,
    0.0,
]

history = []

print("=== CONTROLLED COLLISION 4-7 ===")
for delta in schedule:
    res = least_squares(
        residuals,
        x,
        args=(n, edges, fixed_edge, target_pair, delta, 100.0),
        method="trf",
        loss="linear",
        ftol=1e-14,
        xtol=1e-14,
        gtol=1e-14,
        max_nfev=200000,
    )
    x = res.x
    coords = decode(x, n, fixed_edge)

    max_abs, rms = edge_errors(coords, edges)
    min_dist, min_pair, nearest = min_pair_distance(coords)

    d47 = float(np.linalg.norm(coords[target_pair[0]] - coords[target_pair[1]]))

    item = {
        "target_delta": delta,
        "d47": d47,
        "max_abs": max_abs,
        "rms": rms,
        "min_pair_distance": min_dist,
        "min_pair": list(min_pair),
        "nfev": int(res.nfev),
        "success": bool(res.success),
        "cost": float(res.cost),
        "nearest_pairs": [[i, j, d] for d, i, j in nearest],
    }
    history.append(item)

    print(
        f"delta={delta:<8g} "
        f"d47={d47:.12e} "
        f"max_abs={max_abs:.12e} "
        f"rms={rms:.12e} "
        f"min_dist={min_dist:.12e} "
        f"min_pair={min_pair} "
        f"nfev={res.nfev}",
        flush=True,
    )

np.savetxt(outdir / "controlled_collision_final_coords.csv", coords, delimiter=",", header="x,y", comments="")
(outdir / "controlled_collision_history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")

with (outdir / "controlled_collision_history.csv").open("w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "target_delta",
        "d47",
        "max_abs",
        "rms",
        "min_pair_distance",
        "min_pair",
        "nfev",
        "success",
        "cost",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in history:
        writer.writerow({k: row[k] for k in fieldnames})

print("\nWROTE:")
print(outdir / "controlled_collision_history.csv")
print(outdir / "controlled_collision_history.json")
print(outdir / "controlled_collision_final_coords.csv")
