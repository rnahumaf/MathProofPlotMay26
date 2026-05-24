from pathlib import Path
import csv, json, os, math, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import numpy as np

from distinct_geometric_embedder import worker as distinct_worker

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
outdir = root / "subcore_021_without_3_12_distinct_sweep"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3 - 1, 12 - 1)

min_seps = [0.20, 0.10, 0.05, 0.02, 0.01]
weights = [100.0, 500.0, 2000.0]
runs_per_cell = 60
max_nfev = 100000
scale = 4.0
loss_f_scale = 0.1
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605250

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def target_d2(coords):
    p = np.array(coords[TARGET[0]], dtype=float)
    q = np.array(coords[TARGET[1]], dtype=float)
    d = p - q
    return float(d @ d)

def run_batch(edges, n, min_sep, weight):
    tasks = [
        (
            seed0
            + int(min_sep * 1_000_000)
            + int(weight * 1000)
            + k * 104729,
            edges,
            n,
            max_nfev,
            scale,
            min_sep,
            weight,
            loss_f_scale,
        )
        for k in range(runs_per_cell)
    ]

    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(distinct_worker, t) for t in tasks]
        for fut in as_completed(futs):
            r = fut.result()
            r["target_3_12_d2"] = target_d2(r["coords"])
            rows.append(r)
    return rows

def main():
    edges = read_edges(edges_path)
    n = max(max(i, j) for i, j in edges) + 1

    summary = []
    all_rows = []

    print("=== SUBCORE 021 WITHOUT 3-12 DISTINCT SWEEP ===")
    print(f"edges={len(edges)} target_pair=3-12")

    for min_sep in min_seps:
        for weight in weights:
            rows = run_batch(edges, n, min_sep, weight)

            feasible = [
                r for r in rows
                if r["min_pair_distance"] >= 0.95 * min_sep
            ]

            best_edge = min(
                rows,
                key=lambda r: (r["max_abs_edge_squared_error"], -r["min_pair_distance"]),
            )

            best_feasible = min(
                feasible,
                key=lambda r: r["max_abs_edge_squared_error"],
                default=None,
            )

            d2_vals_feasible = [r["target_3_12_d2"] for r in feasible]
            item = {
                "min_separation": min_sep,
                "collision_weight": weight,
                "runs": len(rows),
                "feasible_count": len(feasible),
                "best_edge_max_abs": best_edge["max_abs_edge_squared_error"],
                "best_edge_min_pair_distance": best_edge["min_pair_distance"],
                "best_edge_target_3_12_d2": best_edge["target_3_12_d2"],
                "best_feasible_max_abs": None if best_feasible is None else best_feasible["max_abs_edge_squared_error"],
                "best_feasible_rms": None if best_feasible is None else best_feasible["rms_edge_squared_error"],
                "best_feasible_min_pair_distance": None if best_feasible is None else best_feasible["min_pair_distance"],
                "best_feasible_target_3_12_d2": None if best_feasible is None else best_feasible["target_3_12_d2"],
                "feasible_d2_min": None if not d2_vals_feasible else min(d2_vals_feasible),
                "feasible_d2_max": None if not d2_vals_feasible else max(d2_vals_feasible),
                "feasible_d2_median": None if not d2_vals_feasible else statistics.median(d2_vals_feasible),
                "median_max_abs": statistics.median(r["max_abs_edge_squared_error"] for r in rows),
                "median_min_pair_distance": statistics.median(r["min_pair_distance"] for r in rows),
            }
            summary.append(item)

            print(
                f"sep={min_sep:<5} w={weight:<7} "
                f"feas={len(feasible):>2}/{len(rows)} "
                f"best_feas_abs={item['best_feasible_max_abs']} "
                f"best_feas_dist={item['best_feasible_min_pair_distance']} "
                f"best_feas_d2_3_12={item['best_feasible_target_3_12_d2']} "
                f"d2_range=[{item['feasible_d2_min']},{item['feasible_d2_max']}] "
                f"best_edge_abs={item['best_edge_max_abs']:.3e} "
                f"best_edge_dist={item['best_edge_min_pair_distance']:.3e} "
                f"best_edge_d2={item['best_edge_target_3_12_d2']:.6g}",
                flush=True,
            )

            for r in rows:
                all_rows.append({
                    "min_separation": min_sep,
                    "collision_weight": weight,
                    "seed": r["seed"],
                    "success": r["success"],
                    "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                    "rms_edge_squared_error": r["rms_edge_squared_error"],
                    "min_pair_distance": r["min_pair_distance"],
                    "collision_pairs_at_1e-6": r["collision_pairs_at_1e-6"],
                    "target_3_12_d2": r["target_3_12_d2"],
                    "nfev": r["nfev"],
                })

    with (outdir / "without_3_12_distinct_sweep_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "without_3_12_distinct_sweep_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "without_3_12_distinct_sweep_metadata.json").write_text(json.dumps({
        "source_edges": str(edges_path),
        "target_pair": "3-12",
        "min_seps": min_seps,
        "weights": weights,
        "runs_per_cell": runs_per_cell,
        "max_nfev": max_nfev,
        "scale": scale,
        "loss_f_scale": loss_f_scale,
        "workers": workers,
        "interpretation": "If exact solutions are always collapsed and separated approximations keep positive residual, the obstruction is distinctness, not the removed edge alone."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "without_3_12_distinct_sweep_summary.csv")
    print(outdir / "without_3_12_distinct_sweep_runs.csv")
    print(outdir / "without_3_12_distinct_sweep_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
