from pathlib import Path
import csv, json, os, math, statistics, collections
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import numpy as np

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_final_survivor_greedy_core" / "final_greedy_core_edges.csv"
outdir = root / "subcore_021_final_core_remove_3_11_distance_audit"
outdir.mkdir(parents=True, exist_ok=True)

REMOVED = (3 - 1, 11 - 1)
runs = 700
scale_values = [1.5, 2.0, 4.0, 8.0, 12.0]
max_nfev = 120000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605255

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def distance_squared(coords, pair):
    a, b = pair
    p = np.array(coords[a], dtype=float)
    q = np.array(coords[b], dtype=float)
    d = p - q
    return float(d @ d)

def classify_d2(d2):
    targets = [0.0, 1.0, 3.0, 4.0]
    for t in targets:
        if abs(d2 - t) <= 1e-6:
            return f"d2≈{t:g}"
    return "other"

def cluster_values(vals, tol=1e-6):
    vals = sorted(vals)
    clusters = []
    for v in vals:
        if not clusters or abs(v - clusters[-1]["last"]) > tol:
            clusters.append({"count": 1, "min": v, "max": v, "last": v, "values": [v]})
        else:
            c = clusters[-1]
            c["count"] += 1
            c["max"] = v
            c["last"] = v
            c["values"].append(v)

    out = []
    for c in clusters:
        out.append({
            "count": c["count"],
            "min": c["min"],
            "max": c["max"],
            "mean": statistics.mean(c["values"]),
        })
    return out

def run_batch(edges, n, scale):
    tasks = [
        (
            seed0 + int(scale * 1000) + k * 104729,
            edges,
            n,
            max_nfev,
            scale,
        )
        for k in range(runs)
    ]

    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(exact_worker, t) for t in tasks]
        for fut in as_completed(futs):
            r = fut.result()
            if r["max_abs_edge_squared_error"] <= 1e-8:
                r["removed_pair_d2"] = distance_squared(r["coords"], REMOVED)
                r["removed_pair_dist"] = math.sqrt(max(r["removed_pair_d2"], 0.0))
                r["branch"] = classify_d2(r["removed_pair_d2"])
            else:
                r["removed_pair_d2"] = None
                r["removed_pair_dist"] = None
                r["branch"] = "unsolved"
            rows.append(r)
    return rows

def main():
    full_edges = read_edges(edges_path)
    edges = [e for e in full_edges if tuple(sorted(e)) != tuple(sorted(REMOVED))]
    n = max(max(i, j) for i, j in full_edges) + 1

    print("=== SUBCORE 021 FINAL CORE REMOVE 3-11 DISTANCE AUDIT ===")
    print("full_edge_count:", len(full_edges))
    print("edge_count_without_removed:", len(edges))
    print("removed:", "3-11")

    all_rows = []
    summary = []

    for scale in scale_values:
        rows = run_batch(edges, n, scale)
        solved = [r for r in rows if r["removed_pair_d2"] is not None]
        vals = [r["removed_pair_d2"] for r in solved]
        branch_counts = collections.Counter(r["branch"] for r in solved)

        item = {
            "scale": scale,
            "runs": len(rows),
            "solved_count": len(solved),
            "best_max_abs": min(r["max_abs_edge_squared_error"] for r in rows),
            "median_max_abs": statistics.median(r["max_abs_edge_squared_error"] for r in rows),
            "d2_min": min(vals) if vals else None,
            "d2_max": max(vals) if vals else None,
            "d2_mean": statistics.mean(vals) if vals else None,
            "d2_median": statistics.median(vals) if vals else None,
            "d2_stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "near_1_count": sum(1 for v in vals if abs(v - 1.0) <= 1e-6),
            "near_1e4_count": sum(1 for v in vals if abs(v - 1.0) <= 1e-4),
            "branch_counts": dict(branch_counts),
            "clusters": cluster_values(vals, tol=1e-6) if vals else [],
        }
        summary.append(item)

        print(
            f"scale={scale:<4} solved={len(solved)}/{len(rows)} "
            f"best_abs={item['best_max_abs']:.3e} "
            f"d2_min={item['d2_min']} d2_max={item['d2_max']} "
            f"d2_median={item['d2_median']} "
            f"near1<=1e-6:{item['near_1_count']} "
            f"branches={dict(branch_counts)}",
            flush=True,
        )

        print("  clusters:")
        for c in item["clusters"][:12]:
            print(
                f"    count={c['count']} mean={c['mean']:.12g} "
                f"range=[{c['min']:.12g},{c['max']:.12g}]"
            )

        for r in rows:
            all_rows.append({
                "scale": scale,
                "seed": r["seed"],
                "success": r["success"],
                "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                "rms_edge_squared_error": r["rms_edge_squared_error"],
                "nfev": r["nfev"],
                "runtime_seconds": r["runtime_seconds"],
                "removed_pair_d2": r["removed_pair_d2"],
                "removed_pair_dist": r["removed_pair_dist"],
                "branch": r["branch"],
            })

    with (outdir / "remove_3_11_distance_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with (outdir / "remove_3_11_distance_runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    metadata = {
        "source_edges": str(edges_path),
        "removed_edge": "3-11",
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": (
            "If all exact realizations of the final core without edge 3-11 force "
            "|3-11|^2 away from 1, then reinserting edge 3-11 is the local contradiction."
        ),
    }
    (outdir / "remove_3_11_distance_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nWROTE:")
    print(outdir / "remove_3_11_distance_summary.json")
    print(outdir / "remove_3_11_distance_runs.csv")
    print(outdir / "remove_3_11_distance_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
