from pathlib import Path
import csv, json, os, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
meta_path = root / "subcore_021_final_high_block_survivor_probe" / "final_high_block_survivor_probe_metadata.json"
outdir = root / "subcore_021_final_survivor_edge_ablation"
outdir.mkdir(parents=True, exist_ok=True)

runs = 160
scale_values = [2.0, 4.0, 8.0]
max_nfev = 90000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605253

def parse_edges(s):
    edges = []
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a) - 1, int(b) - 1))))
    return sorted(set(edges))

def edge_label(e):
    return f"{e[0]+1}-{e[1]+1}"

def run_batch(edges, n, tag, scale):
    tasks = [
        (
            seed0 + abs(hash((tag, scale, k))) % 1_000_000_000 + k * 104729,
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
            rows.append(fut.result())
    return rows

def summarize(rows):
    vals = [r["max_abs_edge_squared_error"] for r in rows]
    rms_vals = [r["rms_edge_squared_error"] for r in rows]
    best = min(rows, key=lambda r: r["max_abs_edge_squared_error"])
    return {
        "best_max_abs": best["max_abs_edge_squared_error"],
        "best_rms": best["rms_edge_squared_error"],
        "best_seed": best["seed"],
        "best_nfev": best["nfev"],
        "median_max_abs": statistics.median(vals),
        "median_rms": statistics.median(rms_vals),
        "solved_1e8": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-8),
        "solved_1e6": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-6),
        "solved_1e4": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-4),
    }

def main():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    edges = parse_edges(meta["q_edges_plus_target"])
    n = int(meta["q_vertex_count"])

    print("=== SUBCORE 021 FINAL SURVIVOR EDGE ABLATION ===")
    print("source_index:", meta["source_index"])
    print("qV:", n)
    print("edge_count:", len(edges))
    print("target_q:", meta["target_q"])
    print("representative_blocks:", meta["representative_blocks"])

    summary = []

    # Baseline.
    for scale in scale_values:
        rows = run_batch(edges, n, "baseline", scale)
        s = summarize(rows)
        item = {
            "case": "baseline",
            "removed_edge": "",
            "edge_count": len(edges),
            "scale": scale,
            **s,
        }
        summary.append(item)
        print(
            f"baseline scale={scale:<3} "
            f"best={s['best_max_abs']:.6e} "
            f"median={s['median_max_abs']:.6e} "
            f"solved<=1e-4:{s['solved_1e4']}",
            flush=True,
        )

    # Single-edge ablation.
    for e in edges:
        label = edge_label(e)
        subset = [x for x in edges if x != e]

        best_over_scales = None
        per_scale = []

        for scale in scale_values:
            rows = run_batch(subset, n, f"remove_{label}", scale)
            s = summarize(rows)
            item = {
                "case": "remove_one_edge",
                "removed_edge": label,
                "edge_count": len(subset),
                "scale": scale,
                **s,
            }
            summary.append(item)
            per_scale.append(item)

            if best_over_scales is None or s["best_max_abs"] < best_over_scales["best_max_abs"]:
                best_over_scales = item

        print(
            f"remove={label:<5} "
            f"best_any_scale={best_over_scales['best_max_abs']:.6e} "
            f"best_scale={best_over_scales['scale']} "
            f"solved<=1e-4:{best_over_scales['solved_1e4']}",
            flush=True,
        )

    with (outdir / "final_survivor_edge_ablation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    metadata = {
        "source": str(meta_path),
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": (
            "Single-edge ablation for the final qV=11 quotient survivor. "
            "If removing an edge keeps best_max_abs bounded away from zero, the edge "
            "is not necessary for the numerical obstruction. If removing an edge solves "
            "the graph, it is critical."
        ),
    }
    (outdir / "final_survivor_edge_ablation_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nWROTE:")
    print(outdir / "final_survivor_edge_ablation_summary.csv")
    print(outdir / "final_survivor_edge_ablation_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
