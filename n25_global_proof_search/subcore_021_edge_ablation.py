from pathlib import Path
import csv, json, os, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "hard_subcore_exact_filter_checks" / "subcore_021_edges.csv"
stable_path = root / "subcore_021_residual_fingerprint" / "stable_failing_edges.csv"
outdir = root / "subcore_021_edge_ablation"
outdir.mkdir(parents=True, exist_ok=True)

runs_per_scale = 50
scale_values = [2.0, 4.0, 8.0]
max_nfev = 100000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605247

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def edge_label(edge):
    return f"{edge[0] + 1}-{edge[1] + 1}"

def parse_label(label):
    a, b = label.split("-")
    return tuple(sorted((int(a) - 1, int(b) - 1)))

def load_candidates(edges):
    with stable_path.open(newline="", encoding="utf-8") as f:
        stable = list(csv.DictReader(f))

    # Primeiro os resíduos mais estáveis; depois o restante das arestas.
    ordered = []
    seen = set()

    for row in stable[:15]:
        e = parse_label(row["edge"])
        if e in edges and e not in seen:
            ordered.append({
                "remove_label": row["edge"],
                "remove_edge": e,
                "source": "stable_failing_top15",
                "mean_abs": float(row["mean_abs"]),
                "mean_err": float(row["mean_err"]),
            })
            seen.add(e)

    for e in edges:
        if e not in seen:
            ordered.append({
                "remove_label": edge_label(e),
                "remove_edge": e,
                "source": "remaining_edges",
                "mean_abs": None,
                "mean_err": None,
            })
            seen.add(e)

    return ordered

def run_batch(edge_subset, tag, scale):
    n = max(max(i, j) for i, j in edge_subset) + 1
    tasks = [
        (
            seed0 + abs(hash((tag, scale, k))) % 1_000_000_000 + k * 104729,
            edge_subset,
            n,
            max_nfev,
            scale,
        )
        for k in range(runs_per_scale)
    ]

    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(exact_worker, t) for t in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    return rows

def summarize_rows(rows):
    rows = sorted(rows, key=lambda r: r["max_abs_edge_squared_error"])
    vals = [r["max_abs_edge_squared_error"] for r in rows]
    rms_vals = [r["rms_edge_squared_error"] for r in rows]
    best = rows[0]
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
    edges = read_edges(edges_path)
    edge_set = set(edges)
    candidates = load_candidates(edges)

    summary = []
    all_runs = []

    print("=== SUBCORE 021 EDGE ABLATION ===")

    # Baseline curto para referência.
    for scale in scale_values:
        rows = run_batch(edges, "baseline", scale)
        s = summarize_rows(rows)
        item = {
            "case": "baseline",
            "removed_edge": "",
            "source": "baseline",
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

    # Remoção de uma aresta por vez.
    for cand_index, cand in enumerate(candidates, 1):
        removed = cand["remove_edge"]
        subset = [e for e in edges if e != removed]
        label = cand["remove_label"]

        best_over_scales = None
        per_scale = []

        for scale in scale_values:
            rows = run_batch(subset, f"remove_{label}", scale)
            s = summarize_rows(rows)

            item = {
                "case": "remove_one_edge",
                "removed_edge": label,
                "source": cand["source"],
                "edge_count": len(subset),
                "scale": scale,
                "stable_mean_abs": cand["mean_abs"],
                "stable_mean_err": cand["mean_err"],
                **s,
            }
            summary.append(item)
            per_scale.append(item)

            if best_over_scales is None or item["best_max_abs"] < best_over_scales["best_max_abs"]:
                best_over_scales = item

            for r in rows:
                all_runs.append({
                    "case": "remove_one_edge",
                    "removed_edge": label,
                    "scale": scale,
                    "seed": r["seed"],
                    "success": r["success"],
                    "max_abs_edge_squared_error": r["max_abs_edge_squared_error"],
                    "rms_edge_squared_error": r["rms_edge_squared_error"],
                    "nfev": r["nfev"],
                    "runtime_seconds": r["runtime_seconds"],
                })

        print(
            f"remove={label:<5} source={cand['source']:<22} "
            f"best_any_scale={best_over_scales['best_max_abs']:.6e} "
            f"best_scale={best_over_scales['scale']} "
            f"solved<=1e-4:{best_over_scales['solved_1e4']}",
            flush=True,
        )

        # Se achou uma aresta crítica que libera o sistema, podemos parar cedo.
        if best_over_scales["best_max_abs"] <= 1e-6:
            print(f"EARLY_STOP solved after removing {label}", flush=True)
            break

    with (outdir / "edge_ablation_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    if all_runs:
        with (outdir / "edge_ablation_runs.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_runs[0].keys()))
            writer.writeheader()
            writer.writerows(all_runs)

    (outdir / "edge_ablation_metadata.json").write_text(json.dumps({
        "source_edges": str(edges_path),
        "stable_failing_edges": str(stable_path),
        "runs_per_scale": runs_per_scale,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "workers": workers,
        "interpretation": "If removing one edge drops best_max_abs near zero, that edge is part of a small obstruction. If no single removal helps, proceed to greedy/core ablation with pairs."
    }, indent=2), encoding="utf-8")

    print("\nWROTE:")
    print(outdir / "edge_ablation_summary.csv")
    print(outdir / "edge_ablation_runs.csv")
    print(outdir / "edge_ablation_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
