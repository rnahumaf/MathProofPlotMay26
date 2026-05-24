from pathlib import Path
import csv, json, os, statistics, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
meta_path = root / "subcore_021_final_high_block_survivor_probe" / "final_high_block_survivor_probe_metadata.json"
outdir = root / "subcore_021_final_survivor_greedy_core"
outdir.mkdir(parents=True, exist_ok=True)

runs = 90
scale_values = [2.0, 4.0, 8.0]
max_nfev = 90000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605254

# Keep removing an edge if the reduced graph still has residual >= this.
keep_obstruction_threshold = 5e-2

# Stop for safety; current graph has 23 edges.
max_rounds = 20

def stable_int(s):
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:12], 16)

def parse_edges(s):
    edges = []
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a) - 1, int(b) - 1))))
    return sorted(set(edges))

def edge_label(e):
    return f"{e[0]+1}-{e[1]+1}"

def edges_label(edges):
    return " ".join(edge_label(e) for e in sorted(edges))

def run_batch(edges, n, tag, scale):
    tasks = [
        (
            seed0 + stable_int(f"{tag}|{scale}|{k}") % 1_000_000_000 + k * 104729,
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

def evaluate_graph(edges, n, tag):
    best_over_scales = None
    scale_summaries = []

    for scale in scale_values:
        rows = run_batch(edges, n, tag, scale)
        s = summarize(rows)
        s["scale"] = scale
        scale_summaries.append(s)

        if best_over_scales is None or s["best_max_abs"] < best_over_scales["best_max_abs"]:
            best_over_scales = s

    return best_over_scales, scale_summaries

def write_edges_csv(path, edges):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j"])
        for a, b in sorted(edges):
            w.writerow([a + 1, b + 1])

def main():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    current_edges = parse_edges(meta["q_edges_plus_target"])
    n = int(meta["q_vertex_count"])

    print("=== SUBCORE 021 FINAL SURVIVOR GREEDY CORE REDUCTION ===")
    print("source_index:", meta["source_index"])
    print("qV:", n)
    print("initial_edge_count:", len(current_edges))
    print("target_q:", meta["target_q"])
    print("keep_obstruction_threshold:", keep_obstruction_threshold)
    print("runs_per_scale:", runs)
    print("scales:", scale_values)
    print("representative_blocks:", meta["representative_blocks"])

    round_rows = []
    test_rows = []

    for round_index in range(1, max_rounds + 1):
        baseline_best, baseline_scales = evaluate_graph(
            current_edges,
            n,
            f"round_{round_index}_baseline_{edges_label(current_edges)}"
        )

        print(
            f"\nROUND {round_index} baseline "
            f"edges={len(current_edges)} "
            f"best={baseline_best['best_max_abs']:.6e} "
            f"best_scale={baseline_best['scale']} "
            f"solved<=1e-4:{baseline_best['solved_1e4']}",
            flush=True,
        )

        candidates = []

        for e in current_edges:
            label = edge_label(e)
            subset = [x for x in current_edges if x != e]

            best, scales = evaluate_graph(
                subset,
                n,
                f"round_{round_index}_remove_{label}_{edges_label(subset)}"
            )

            candidate = {
                "round": round_index,
                "removed_edge": label,
                "remaining_edge_count": len(subset),
                "best_max_abs": best["best_max_abs"],
                "best_rms": best["best_rms"],
                "best_scale": best["scale"],
                "best_seed": best["best_seed"],
                "median_max_abs_at_best_scale": best["median_max_abs"],
                "solved_1e8": best["solved_1e8"],
                "solved_1e6": best["solved_1e6"],
                "solved_1e4": best["solved_1e4"],
                "remaining_edges": edges_label(subset),
            }
            candidates.append(candidate)
            test_rows.append(candidate)

            print(
                f"  remove={label:<5} "
                f"best={best['best_max_abs']:.6e} "
                f"scale={best['scale']} "
                f"solved<=1e-4:{best['solved_1e4']}",
                flush=True,
            )

        # Choose the removal that preserves obstruction best.
        candidates.sort(
            key=lambda r: (
                r["solved_1e4"] > 0,
                -r["best_max_abs"],
                -r["median_max_abs_at_best_scale"],
                r["removed_edge"],
            )
        )
        chosen = candidates[0]

        should_remove = (
            chosen["solved_1e4"] == 0
            and chosen["best_max_abs"] >= keep_obstruction_threshold
        )

        round_item = {
            "round": round_index,
            "edge_count_before": len(current_edges),
            "baseline_best_max_abs": baseline_best["best_max_abs"],
            "baseline_best_scale": baseline_best["scale"],
            "chosen_removed_edge": chosen["removed_edge"],
            "chosen_best_max_abs": chosen["best_max_abs"],
            "chosen_best_scale": chosen["best_scale"],
            "chosen_solved_1e4": chosen["solved_1e4"],
            "removed": should_remove,
            "edges_before": edges_label(current_edges),
            "edges_after": chosen["remaining_edges"] if should_remove else edges_label(current_edges),
        }
        round_rows.append(round_item)

        print(
            f"CHOICE round={round_index}: remove={chosen['removed_edge']} "
            f"best_after_remove={chosen['best_max_abs']:.6e} "
            f"solved<=1e-4:{chosen['solved_1e4']} "
            f"removed={should_remove}",
            flush=True,
        )

        if should_remove:
            rem = tuple(sorted((int(chosen["removed_edge"].split("-")[0]) - 1, int(chosen["removed_edge"].split("-")[1]) - 1)))
            current_edges = [x for x in current_edges if x != rem]
            write_edges_csv(outdir / f"round_{round_index:02d}_core_edges.csv", current_edges)
        else:
            break

    # Final stronger baseline check on the reduced core.
    final_best, final_scales = evaluate_graph(
        current_edges,
        n,
        f"final_core_{edges_label(current_edges)}"
    )

    print("\n=== FINAL CORE ===")
    print("edge_count:", len(current_edges))
    print("edges:", edges_label(current_edges))
    print(
        f"final_best={final_best['best_max_abs']:.6e} "
        f"scale={final_best['scale']} "
        f"solved<=1e-8:{final_best['solved_1e8']} "
        f"<=1e-6:{final_best['solved_1e6']} "
        f"<=1e-4:{final_best['solved_1e4']}"
    )

    write_edges_csv(outdir / "final_greedy_core_edges.csv", current_edges)

    with (outdir / "greedy_core_rounds.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(round_rows[0].keys()))
        w.writeheader()
        w.writerows(round_rows)

    with (outdir / "greedy_core_edge_tests.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(test_rows[0].keys()))
        w.writeheader()
        w.writerows(test_rows)

    metadata = {
        "source": str(meta_path),
        "source_index": meta["source_index"],
        "q_vertex_count": n,
        "initial_edge_count": len(parse_edges(meta["q_edges_plus_target"])),
        "final_edge_count": len(current_edges),
        "target_q": meta["target_q"],
        "representative_blocks": meta["representative_blocks"],
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "keep_obstruction_threshold": keep_obstruction_threshold,
        "workers": workers,
        "final_best": final_best,
        "final_edges": edges_label(current_edges),
        "interpretation": (
            "Greedy reduction of the final high-block quotient survivor. "
            "A removed edge is considered nonessential if the graph without it "
            "still has best residual above the obstruction threshold and no near-exact solution."
        ),
    }
    (outdir / "greedy_core_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nWROTE:")
    print(outdir / "final_greedy_core_edges.csv")
    print(outdir / "greedy_core_rounds.csv")
    print(outdir / "greedy_core_edge_tests.csv")
    print(outdir / "greedy_core_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
