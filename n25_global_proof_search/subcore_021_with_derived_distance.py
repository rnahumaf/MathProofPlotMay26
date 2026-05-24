from pathlib import Path
import csv, json, math, os, random, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import numpy as np
from scipy.optimize import least_squares

root = Path("n25_global_proof_search")
edges_path = root / "hard_subcore_exact_filter_checks" / "subcore_021_edges.csv"
outdir = root / "subcore_021_with_derived_distance"
outdir.mkdir(parents=True, exist_ok=True)

DERIVED = [
    (1 - 1, 9 - 1, 3.0),  # |1-9|^2 = 3
]

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def initial_values(n, fixed_edge, seed, scale):
    rng = random.Random(seed)
    vals = []
    for i in range(n):
        if i in fixed_edge:
            continue
        angle = rng.random() * 2 * math.pi
        radius = scale * math.sqrt(rng.random())
        vals.extend([radius * math.cos(angle), radius * math.sin(angle)])
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

def residuals(vals, n, edges, fixed_edge, derived_weight):
    coords = decode(vals, n, fixed_edge)
    out = []

    for i, j in edges:
        d = coords[i] - coords[j]
        out.append(float(d @ d - 1.0))

    for i, j, target in DERIVED:
        d = coords[i] - coords[j]
        out.append(derived_weight * float(d @ d - target))

    return np.array(out, dtype=float)

def diagnostics(coords, edges):
    edge_errs = []
    for i, j in edges:
        d = coords[i] - coords[j]
        edge_errs.append(float(d @ d - 1.0))

    derived_errs = []
    for i, j, target in DERIVED:
        d = coords[i] - coords[j]
        derived_errs.append(float(d @ d - target))

    min_dist = 1e99
    min_pair = None
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dist = float(np.linalg.norm(coords[i] - coords[j]))
            if dist < min_dist:
                min_dist = dist
                min_pair = (i + 1, j + 1)

    return {
        "max_edge_abs": float(np.max(np.abs(edge_errs))),
        "rms_edge": float(np.sqrt(np.mean(np.array(edge_errs) ** 2))),
        "max_derived_abs": float(np.max(np.abs(derived_errs))),
        "rms_derived": float(np.sqrt(np.mean(np.array(derived_errs) ** 2))),
        "min_pair_distance": min_dist,
        "min_pair": min_pair,
    }

def worker(task):
    seed, edges, n, fixed_edge, scale, derived_weight, max_nfev = task
    x0 = initial_values(n, fixed_edge, seed, scale)
    res = least_squares(
        residuals,
        x0,
        args=(n, edges, fixed_edge, derived_weight),
        method="trf",
        loss="soft_l1",
        f_scale=1.0,
        ftol=1e-13,
        xtol=1e-13,
        gtol=1e-13,
        max_nfev=max_nfev,
    )
    coords = decode(res.x, n, fixed_edge)
    diag = diagnostics(coords, edges)
    return {
        "seed": seed,
        "scale": scale,
        "derived_weight": derived_weight,
        "success": bool(res.success),
        "nfev": int(res.nfev),
        "cost": float(res.cost),
        **diag,
    }

def run_batch(tasks, workers_count):
    rows = []
    with ProcessPoolExecutor(max_workers=workers_count) as ex:
        futs = [ex.submit(worker, t) for t in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows

def main():
    edges = read_edges(edges_path)
    n = max(max(i, j) for i, j in edges) + 1
    fixed_edge = edges[0]

    runs = 240
    max_nfev = 100000
    scales = [2.0, 4.0, 8.0]
    weights = [1.0, 10.0, 100.0]
    workers_count = max(1, min(12, (os.cpu_count() or 2) - 1))
    seed0 = 202605246

    summary = []
    all_rows = []

    print("=== SUBCORE 021 WITH DERIVED DISTANCE ===")

    for scale in scales:
        for weight in weights:
            tasks = [
                (
                    seed0 + int(scale * 1000) + int(weight * 10000) + k * 104729,
                    edges,
                    n,
                    fixed_edge,
                    scale,
                    weight,
                    max_nfev,
                )
                for k in range(runs)
            ]

            rows = run_batch(tasks, workers_count)
            rows.sort(key=lambda r: (r["max_edge_abs"] + r["max_derived_abs"], r["max_edge_abs"]))

            best = rows[0]
            item = {
                "scale": scale,
                "derived_weight": weight,
                "runs": runs,
                "best_max_edge_abs": best["max_edge_abs"],
                "best_rms_edge": best["rms_edge"],
                "best_max_derived_abs": best["max_derived_abs"],
                "best_min_pair_distance": best["min_pair_distance"],
                "best_min_pair": best["min_pair"],
                "best_seed": best["seed"],
                "best_nfev": best["nfev"],
                "median_max_edge_abs": statistics.median(r["max_edge_abs"] for r in rows),
                "median_max_derived_abs": statistics.median(r["max_derived_abs"] for r in rows),
                "solved_edge_1e4": sum(1 for r in rows if r["max_edge_abs"] <= 1e-4),
                "solved_both_1e4": sum(1 for r in rows if r["max_edge_abs"] <= 1e-4 and r["max_derived_abs"] <= 1e-4),
            }
            summary.append(item)
            all_rows.extend(rows)

            print(
                f"scale={scale:<3} w={weight:<5} "
                f"best_edge={item['best_max_edge_abs']:.6e} "
                f"best_derived={item['best_max_derived_abs']:.6e} "
                f"min_dist={item['best_min_pair_distance']:.6e} "
                f"min_pair={item['best_min_pair']} "
                f"median_edge={item['median_max_edge_abs']:.6e} "
                f"solved_both<=1e-4:{item['solved_both_1e4']}",
                flush=True,
            )

    with (outdir / "subcore_021_with_derived_distance_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "subcore_021_with_derived_distance_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "subcore_021_with_derived_distance_metadata.json").write_text(json.dumps({
        "edges": str(edges_path),
        "derived_constraints": [{"i": 1, "j": 9, "squared_distance": 3}],
        "runs_per_cell": runs,
        "scales": scales,
        "weights": weights,
        "max_nfev": max_nfev,
        "workers": workers_count,
        "interpretation": "If the residual remains bounded away from zero after adding the derived |1-9|^2=3 equation, subcore_021 is a stronger target for an interval/algebraic certificate."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "subcore_021_with_derived_distance_summary.csv")
    print(outdir / "subcore_021_with_derived_distance_runs.csv")
    print(outdir / "subcore_021_with_derived_distance_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
