from pathlib import Path
import csv, json, statistics, os
from concurrent.futures import ProcessPoolExecutor, as_completed

from distinct_geometric_embedder import worker as distinct_worker

root = Path("n25_global_proof_search")
edges_path = root / "collision_forced_subcore_audit" / "target_subcore_015_edges.csv"
outdir = root / "hard_separation_sweep_subcore_015"
outdir.mkdir(parents=True, exist_ok=True)

def load_edges():
    with edges_path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def run_batch(tasks, workers):
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(distinct_worker, t) for t in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows

def main():
    edges = load_edges()
    n = max(max(i, j) for i, j in edges) + 1

    min_seps = [0.20, 0.10, 0.05, 0.02, 0.01]
    weights = [20.0, 100.0, 500.0, 2000.0]
    runs_per_cell = 30
    max_nfev = 50000
    scale = 4.0
    loss_f_scale = 0.1
    workers = max(1, min(12, (os.cpu_count() or 2) - 1))
    seed0 = 202605243

    summary = []
    all_rows = []

    for min_sep in min_seps:
        for weight in weights:
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

            rows = run_batch(tasks, workers)

            feasible = [
                r for r in rows
                if r["min_pair_distance"] >= 0.95 * min_sep
            ]

            rows_by_edge = sorted(
                rows,
                key=lambda r: (r["max_abs_edge_squared_error"], -r["min_pair_distance"]),
            )
            rows_by_sep = sorted(
                rows,
                key=lambda r: (
                    max(0.0, 0.95 * min_sep - r["min_pair_distance"]),
                    r["max_abs_edge_squared_error"],
                ),
            )

            best_edge = rows_by_edge[0]
            best_sep = rows_by_sep[0]
            best_feasible = min(
                feasible,
                key=lambda r: r["max_abs_edge_squared_error"],
                default=None,
            )

            item = {
                "min_separation": min_sep,
                "collision_weight": weight,
                "runs": len(rows),
                "feasible_count": len(feasible),
                "best_edge_max_abs": best_edge["max_abs_edge_squared_error"],
                "best_edge_min_pair_distance": best_edge["min_pair_distance"],
                "best_sep_max_abs": best_sep["max_abs_edge_squared_error"],
                "best_sep_min_pair_distance": best_sep["min_pair_distance"],
                "best_feasible_max_abs": None if best_feasible is None else best_feasible["max_abs_edge_squared_error"],
                "best_feasible_rms": None if best_feasible is None else best_feasible["rms_edge_squared_error"],
                "best_feasible_min_pair_distance": None if best_feasible is None else best_feasible["min_pair_distance"],
                "median_max_abs": statistics.median(r["max_abs_edge_squared_error"] for r in rows),
                "median_min_pair_distance": statistics.median(r["min_pair_distance"] for r in rows),
            }
            summary.append(item)

            print(
                f"sep={min_sep:<5} w={weight:<7} "
                f"feas={len(feasible):>2}/{len(rows)} "
                f"best_feas_abs={item['best_feasible_max_abs']} "
                f"best_sep_abs={item['best_sep_max_abs']:.3e} "
                f"best_sep_dist={item['best_sep_min_pair_distance']:.3e} "
                f"best_edge_abs={item['best_edge_max_abs']:.3e} "
                f"best_edge_dist={item['best_edge_min_pair_distance']:.3e}",
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
                    "nfev": r["nfev"],
                })

    with (outdir / "hard_separation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "hard_separation_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "hard_separation_metadata.json").write_text(json.dumps({
        "edges": str(edges_path),
        "n": n,
        "edge_count": len(edges),
        "min_seps": min_seps,
        "weights": weights,
        "runs_per_cell": runs_per_cell,
        "max_nfev": max_nfev,
        "loss_f_scale": loss_f_scale,
        "interpretation": "Rows with feasible_count > 0 show approximate distinct realizations at that separation. If feasible_count is zero or best_feasible_max_abs stays bounded away from zero, this suggests a distinctness obstruction at that separation."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "hard_separation_summary.csv")
    print(outdir / "hard_separation_runs.csv")
    print(outdir / "hard_separation_metadata.json")

if __name__ == "__main__":
    main()
