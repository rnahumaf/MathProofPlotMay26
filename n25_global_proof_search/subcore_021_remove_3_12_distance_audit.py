from pathlib import Path
import csv, json, os, math, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import numpy as np

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "hard_subcore_exact_filter_checks" / "subcore_021_edges.csv"
outdir = root / "subcore_021_remove_3_12_distance_audit"
outdir.mkdir(parents=True, exist_ok=True)

REMOVED = (3 - 1, 12 - 1)
runs = 500
scale_values = [2.0, 4.0, 8.0]
max_nfev = 100000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605248

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def distance_squared(coords, pair):
    a, b = pair
    p = np.array(coords[a])
    q = np.array(coords[b])
    d = p - q
    return float(d @ d)

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
            row = fut.result()
            if row["max_abs_edge_squared_error"] <= 1e-8:
                row["removed_pair_d2"] = distance_squared(row["coords"], REMOVED)
                row["removed_pair_dist"] = math.sqrt(max(row["removed_pair_d2"], 0.0))
            else:
                row["removed_pair_d2"] = None
                row["removed_pair_dist"] = None
            rows.append(row)

    return rows

def main():
    full_edges = read_edges(edges_path)
    edges = [e for e in full_edges if tuple(sorted(e)) != tuple(sorted(REMOVED))]
    n = max(max(i, j) for i, j in full_edges) + 1

    all_rows = []
    summary = []

    print("=== SUBCORE 021 REMOVE 3-12 DISTANCE AUDIT ===")
    print(f"edge_count_without_removed={len(edges)} removed=3-12")

    for scale in scale_values:
        rows = run_batch(edges, n, scale)
        solved = [r for r in rows if r["removed_pair_d2"] is not None]
        vals = [r["removed_pair_d2"] for r in solved]

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
            "d2_near_1_count": sum(1 for v in vals if abs(v - 1.0) <= 1e-6),
            "d2_near_1e4_count": sum(1 for v in vals if abs(v - 1.0) <= 1e-4),
        }
        summary.append(item)

        print(
            f"scale={scale:<3} solved={len(solved)}/{len(rows)} "
            f"best_abs={item['best_max_abs']:.3e} "
            f"d2_min={item['d2_min']} d2_max={item['d2_max']} "
            f"d2_mean={item['d2_mean']} d2_stdev={item['d2_stdev']} "
            f"near1<=1e-6:{item['d2_near_1_count']} "
            f"near1<=1e-4:{item['d2_near_1e4_count']}",
            flush=True,
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
            })

    with (outdir / "remove_3_12_distance_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "remove_3_12_distance_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "remove_3_12_distance_metadata.json").write_text(json.dumps({
        "source_edges": str(edges_path),
        "removed_edge": "3-12",
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": "If all exact realizations of subcore_021 without edge 3-12 force |3-12|^2 away from 1, then adding edge 3-12 is the local contradiction target."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "remove_3_12_distance_summary.csv")
    print(outdir / "remove_3_12_distance_runs.csv")
    print(outdir / "remove_3_12_distance_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
