from pathlib import Path
import csv, json, os, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
src = root / "subcore_021_high_block_survivor_exact_filters" / "high_block_survivor_exact_filter_summary.csv"
outdir = root / "subcore_021_final_high_block_survivor_probe"
outdir.mkdir(parents=True, exist_ok=True)

SOURCE_INDEX = "5395"
runs = 600
scale_values = [1.5, 2.0, 4.0, 8.0, 12.0]
max_nfev = 120000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605252

def parse_edges(s):
    edges = []
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a) - 1, int(b) - 1))))
    return sorted(set(edges))

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
            rows.append(fut.result())
    return rows

def main():
    with src.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    target_rows = [r for r in rows if r["source_index"] == SOURCE_INDEX]
    if len(target_rows) != 1:
        raise RuntimeError(f"Expected one row for source {SOURCE_INDEX}, got {len(target_rows)}")

    row = target_rows[0]
    edges = parse_edges(row["q_edges_plus_target"])
    n = int(row["q_vertex_count"])

    print("=== SUBCORE 021 FINAL HIGH-BLOCK SURVIVOR PROBE ===")
    print("source_index:", row["source_index"])
    print("qV:", row["q_vertex_count"])
    print("qE_before_target:", row["q_edge_count"])
    print("target_q:", row["target_q"])
    print("edge_count_with_target:", len(edges))
    print("representative_blocks:", row["representative_blocks"])
    print("q_edges_plus_target:", row["q_edges_plus_target"])

    summary = []
    all_rows = []

    for scale in scale_values:
        probe_rows = run_batch(edges, n, scale)
        probe_rows.sort(key=lambda r: r["max_abs_edge_squared_error"])

        vals = [r["max_abs_edge_squared_error"] for r in probe_rows]
        rms_vals = [r["rms_edge_squared_error"] for r in probe_rows]
        best = probe_rows[0]

        item = {
            "scale": scale,
            "runs": len(probe_rows),
            "best_max_abs": best["max_abs_edge_squared_error"],
            "best_rms": best["rms_edge_squared_error"],
            "best_seed": best["seed"],
            "best_nfev": best["nfev"],
            "median_max_abs": statistics.median(vals),
            "median_rms": statistics.median(rms_vals),
            "solved_1e8": sum(1 for r in probe_rows if r["max_abs_edge_squared_error"] <= 1e-8),
            "solved_1e6": sum(1 for r in probe_rows if r["max_abs_edge_squared_error"] <= 1e-6),
            "solved_1e4": sum(1 for r in probe_rows if r["max_abs_edge_squared_error"] <= 1e-4),
        }
        summary.append(item)

        print(
            f"scale={scale:<4} "
            f"best_abs={item['best_max_abs']:.6e} "
            f"best_rms={item['best_rms']:.6e} "
            f"median_abs={item['median_max_abs']:.6e} "
            f"solved<=1e-8:{item['solved_1e8']} "
            f"<=1e-6:{item['solved_1e6']} "
            f"<=1e-4:{item['solved_1e4']}",
            flush=True,
        )

        for r in probe_rows:
            all_rows.append({
                "scale": scale,
                "seed": r["seed"],
                "success": r["success"],
                "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                "rms_edge_squared_error": r["rms_edge_squared_error"],
                "nfev": r["nfev"],
                "runtime_seconds": r["runtime_seconds"],
            })

    with (outdir / "final_high_block_survivor_probe_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    with (outdir / "final_high_block_survivor_probe_runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    metadata = {
        "source": str(src),
        "source_index": SOURCE_INDEX,
        "q_vertex_count": row["q_vertex_count"],
        "q_edge_count_before_target": row["q_edge_count"],
        "target_q": row["target_q"],
        "edge_count_with_target": len(edges),
        "representative_blocks": row["representative_blocks"],
        "q_edges_plus_target": row["q_edges_plus_target"],
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": (
            "Focused numerical probe of the single qV=9..11 unresolved quotient "
            "that survived triangle, distance-label, and finite trilateration filters."
        ),
    }
    (outdir / "final_high_block_survivor_probe_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nWROTE:")
    print(outdir / "final_high_block_survivor_probe_summary.csv")
    print(outdir / "final_high_block_survivor_probe_runs.csv")
    print(outdir / "final_high_block_survivor_probe_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
