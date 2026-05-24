from pathlib import Path
import csv, json, os, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
src = root / "subcore_021_unresolved_quotient_triage" / "unresolved_unique_quotient_graphs.csv"
outdir = root / "subcore_021_unresolved_quotient_target_probe"
outdir.mkdir(parents=True, exist_ok=True)

runs = 80
scale_values = [2.0, 4.0, 8.0]
max_nfev = 60000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605251

def parse_edges(s):
    edges = []
    if not s.strip():
        return edges
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a) - 1, int(b) - 1))))
    return sorted(set(edges))

def parse_target(s):
    a, b = s.split("-")
    return tuple(sorted((int(a) - 1, int(b) - 1)))

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
        "median_max_abs": statistics.median(vals),
        "median_rms": statistics.median(rms_vals),
        "solved_1e8": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-8),
        "solved_1e6": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-6),
        "solved_1e4": sum(1 for r in rows if r["max_abs_edge_squared_error"] <= 1e-4),
    }

def main():
    with src.open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # Piloto: todos os unresolved qV=6.
    targets = [r for r in all_rows if int(r["q_vertex_count"]) == 6]
    print("=== SUBCORE 021 UNRESOLVED QUOTIENT TARGET PROBE ===")
    print("source unique unresolved:", len(all_rows))
    print("pilot qV=6 targets:", len(targets))

    summary_rows = []
    detail_rows = []

    for idx, row in enumerate(targets, 1):
        q_edges = parse_edges(row["q_edges"])
        target = parse_target(row["target_q"])
        n = int(row["q_vertex_count"])

        q_edges_plus_target = sorted(set(q_edges + [target]))

        best_overall = None
        per_scale = []

        for scale in scale_values:
            rows = run_batch(
                q_edges_plus_target,
                n,
                f"qV{n}_idx{idx}_target_{row['target_q']}",
                scale,
            )
            s = summarize(rows)
            s["scale"] = scale
            per_scale.append(s)

            if best_overall is None or s["best_max_abs"] < best_overall["best_max_abs"]:
                best_overall = s

            for rr in rows:
                detail_rows.append({
                    "quotient_index": idx,
                    "scale": scale,
                    "seed": rr["seed"],
                    "max_abs_edge_squared_error": rr["max_abs_edge_squared_error"],
                    "rms_edge_squared_error": rr["rms_edge_squared_error"],
                    "nfev": rr["nfev"],
                    "success": rr["success"],
                })

        status = (
            "target_plus_quotient_realizable"
            if best_overall["best_max_abs"] <= 1e-8
            else "target_plus_quotient_not_found"
        )

        out = {
            "quotient_index": idx,
            "partition_count": row["partition_count"],
            "q_vertex_count": row["q_vertex_count"],
            "q_edge_count": row["q_edge_count"],
            "target_q": row["target_q"],
            "target_status": status,
            "best_max_abs": best_overall["best_max_abs"],
            "best_rms": best_overall["best_rms"],
            "best_scale": best_overall["scale"],
            "best_seed": best_overall["best_seed"],
            "best_solved_1e8": best_overall["solved_1e8"],
            "best_solved_1e6": best_overall["solved_1e6"],
            "best_solved_1e4": best_overall["solved_1e4"],
            "representative_blocks": row["representative_blocks"],
            "q_edges": row["q_edges"],
            "q_edges_plus_target": " ".join(f"{a+1}-{b+1}" for a, b in q_edges_plus_target),
        }
        summary_rows.append(out)

        print(
            f"[{idx:03d}/{len(targets)}] "
            f"qE={row['q_edge_count']} parts={row['partition_count']} "
            f"target={row['target_q']} "
            f"best={out['best_max_abs']:.3e} "
            f"solved1e8={out['best_solved_1e8']} "
            f"status={status}",
            flush=True,
        )

    with (outdir / "qv6_unresolved_target_probe_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    with (outdir / "qv6_unresolved_target_probe_runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        w.writeheader()
        w.writerows(detail_rows)

    counts = {}
    for r in summary_rows:
        counts[r["target_status"]] = counts.get(r["target_status"], 0) + 1

    metadata = {
        "source": str(src),
        "pilot": "qV=6 unresolved unique quotient graphs",
        "target_count": len(targets),
        "runs_per_scale": runs,
        "scale_values": scale_values,
        "max_nfev": max_nfev,
        "status_counts": counts,
        "interpretation": (
            "Each unresolved quotient graph was tested after reinserting the quotient target edge. "
            "If target_plus_quotient_not_found persists after stronger runs, that quotient branch "
            "is unlikely to support the full subcore_021 target edge."
        ),
    }
    (outdir / "qv6_unresolved_target_probe_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nstatus counts:")
    for k, v in counts.items():
        print(f"{k}: {v}")

    print("\nWROTE:")
    print(outdir / "qv6_unresolved_target_probe_summary.csv")
    print(outdir / "qv6_unresolved_target_probe_runs.csv")
    print(outdir / "qv6_unresolved_target_probe_metadata.json")

if __name__ == "__main__":
    freeze_support()
    main()
