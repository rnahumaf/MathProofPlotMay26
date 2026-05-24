from pathlib import Path
import json, csv, os, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
details_path = root / "collision_forced_subcore_audit" / "subcore_collision_details.json"
outdir = root / "hard_subcore_exact_probe"
outdir.mkdir(parents=True, exist_ok=True)

target_indices = [21, 18, 20, 3, 15]  # 15 = controle degenerado
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
runs = 300
max_nfev = 80000
scale_values = [2.0, 4.0, 8.0]
seed0 = 202605245

def load_targets():
    details = json.loads(details_path.read_text(encoding="utf-8"))
    targets = []

    for item in details:
        if item["subcore_index"] in target_indices:
            edges = [(int(i) - 1, int(j) - 1) for i, j in item["remapped_edges"]]
            n = max(max(i, j) for i, j in edges) + 1
            targets.append({
                "subcore_index": item["subcore_index"],
                "vertices": item["vertices"],
                "audit_exact_solved_count": item["exact_solved_count"],
                "audit_exact_best_max_abs": item["exact_best_max_abs"],
                "audit_distinct_best_max_abs": item["distinct_best_max_abs"],
                "edges": edges,
                "n": n,
            })

    targets.sort(key=lambda x: target_indices.index(x["subcore_index"]))
    return targets

def run_exact_batch(target, scale):
    tasks = [
        (
            seed0 + target["subcore_index"] * 1000003 + int(scale * 1000) + k * 104729,
            target["edges"],
            target["n"],
            max_nfev,
            scale,
        )
        for k in range(runs)
    ]

    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(exact_worker, t) for t in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows

def main():
    targets = load_targets()
    summary = []
    all_rows = []

    print("=== HARD SUBCORE EXACT PROBE ===", flush=True)

    for target in targets:
        print(
            f"\nsubcore={target['subcore_index']} "
            f"audit_exact_solved={target['audit_exact_solved_count']} "
            f"audit_exact_best={target['audit_exact_best_max_abs']}",
            flush=True,
        )

        for scale in scale_values:
            rows = run_exact_batch(target, scale)
            rows.sort(key=lambda r: r["max_abs_edge_squared_error"])
            best = rows[0]

            vals = [r["max_abs_edge_squared_error"] for r in rows]
            rms_vals = [r["rms_edge_squared_error"] for r in rows]
            solved_1e8 = sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-8)
            solved_1e6 = sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-6)
            solved_1e4 = sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-4)

            item = {
                "subcore_index": target["subcore_index"],
                "scale": scale,
                "runs": runs,
                "max_nfev": max_nfev,
                "best_max_abs": best["max_abs_edge_squared_error"],
                "best_rms": best["rms_edge_squared_error"],
                "best_seed": best["seed"],
                "best_nfev": best["nfev"],
                "median_max_abs": statistics.median(vals),
                "median_rms": statistics.median(rms_vals),
                "solved_1e8": solved_1e8,
                "solved_1e6": solved_1e6,
                "solved_1e4": solved_1e4,
                "audit_exact_best_max_abs": target["audit_exact_best_max_abs"],
                "audit_distinct_best_max_abs": target["audit_distinct_best_max_abs"],
                "vertices": " ".join(map(str, target["vertices"])),
            }
            summary.append(item)

            print(
                f"scale={scale:<3} "
                f"best_abs={item['best_max_abs']:.6e} "
                f"best_rms={item['best_rms']:.6e} "
                f"median_abs={item['median_max_abs']:.6e} "
                f"solved<=1e-8:{solved_1e8} "
                f"<=1e-6:{solved_1e6} "
                f"<=1e-4:{solved_1e4}",
                flush=True,
            )

            for r in rows:
                all_rows.append({
                    "subcore_index": target["subcore_index"],
                    "scale": scale,
                    "seed": r["seed"],
                    "success": r["success"],
                    "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                    "rms_edge_squared_error": r["rms_edge_squared_error"],
                    "nfev": r["nfev"],
                    "runtime_seconds": r["runtime_seconds"],
                })

    with (outdir / "hard_subcore_exact_probe_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with (outdir / "hard_subcore_exact_probe_runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (outdir / "hard_subcore_exact_probe_metadata.json").write_text(json.dumps({
        "target_indices": target_indices,
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": "If a subcore still has best_max_abs bounded away from zero after this exact probe, it becomes a better target for interval/algebraic elimination than collision-only subcore_015."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "hard_subcore_exact_probe_summary.csv")
    print(outdir / "hard_subcore_exact_probe_runs.csv")
    print(outdir / "hard_subcore_exact_probe_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
