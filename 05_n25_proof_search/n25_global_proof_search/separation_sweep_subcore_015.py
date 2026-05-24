from pathlib import Path
import csv, json, statistics, os
from concurrent.futures import ProcessPoolExecutor, as_completed

from distinct_geometric_embedder import worker as distinct_worker

root = Path("n25_global_proof_search")
edges_path = root / "collision_forced_subcore_audit" / "target_subcore_015_edges.csv"
outdir = root / "separation_sweep_subcore_015"
outdir.mkdir(parents=True, exist_ok=True)

def load_edges():
    with edges_path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def run_tasks(tasks, workers):
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(distinct_worker, t) for t in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows

def main():
    edges = load_edges()
    n = max(max(i, j) for i, j in edges) + 1

    workers = max(1, min(12, (os.cpu_count() or 2) - 1))
    min_seps = [0.20, 0.10, 0.05, 0.02, 0.01, 0.005, 0.002]

    runs_per_sep = 40
    max_nfev = 40000
    scale = 4.0
    collision_weight = 20.0
    loss_f_scale = 1.0
    seed0 = 202605241

    summary = []
    all_rows = []

    for min_sep in min_seps:
        tasks = [
            (
                seed0 + int(min_sep * 1_000_000) + k * 104729,
                edges,
                n,
                max_nfev,
                scale,
                min_sep,
                collision_weight,
                loss_f_scale,
            )
            for k in range(runs_per_sep)
        ]

        rows = run_tasks(tasks, workers)
        rows.sort(key=lambda r: (r["max_abs_edge_squared_error"], -r["min_pair_distance"]))

        best = rows[0]
        vals = [r["max_abs_edge_squared_error"] for r in rows]
        dists = [r["min_pair_distance"] for r in rows]

        item = {
            "min_separation": min_sep,
            "runs": len(rows),
            "best_max_abs": best["max_abs_edge_squared_error"],
            "best_rms": best["rms_edge_squared_error"],
            "best_min_pair_distance": best["min_pair_distance"],
            "median_max_abs": statistics.median(vals),
            "median_min_pair_distance": statistics.median(dists),
            "best_seed": best["seed"],
            "best_nfev": best["nfev"],
            "best_success": best["success"],
        }
        summary.append(item)

        print(
            f"sep={item['min_separation']:<7} "
            f"best_abs={item['best_max_abs']:.6e} "
            f"best_min_dist={item['best_min_pair_distance']:.6e} "
            f"median_abs={item['median_max_abs']:.6e}",
            flush=True,
        )

        for r in rows:
            all_rows.append({
                "min_separation": min_sep,
                "seed": r["seed"],
                "success": r["success"],
                "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                "rms_edge_squared_error": r["rms_edge_squared_error"],
                "min_pair_distance": r["min_pair_distance"],
                "collision_pairs_at_1e-6": r["collision_pairs_at_1e-6"],
                "nfev": r["nfev"],
            })

    with (outdir / "separation_sweep_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "separation_sweep_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "separation_sweep_metadata.json").write_text(json.dumps({
        "edges": str(edges_path),
        "n": n,
        "edge_count": len(edges),
        "min_seps": min_seps,
        "runs_per_sep": runs_per_sep,
        "max_nfev": max_nfev,
        "scale": scale,
        "collision_weight": collision_weight,
        "loss_f_scale": loss_f_scale,
        "workers": workers,
        "interpretation": "If best_max_abs tends toward 0 as min_separation tends toward 0, the obstruction is likely a collision-limit phenomenon rather than a fixed positive residual certificate."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "separation_sweep_summary.csv")
    print(outdir / "separation_sweep_runs.csv")
    print(outdir / "separation_sweep_metadata.json")

if __name__ == "__main__":
    main()
