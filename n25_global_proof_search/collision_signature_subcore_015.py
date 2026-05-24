from pathlib import Path
import csv, json, os, math, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

from distinct_geometric_embedder import worker as distinct_worker
from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "collision_forced_subcore_audit" / "target_subcore_015_edges.csv"
outdir = root / "collision_signature_subcore_015"
outdir.mkdir(parents=True, exist_ok=True)

def load_edges():
    with edges_path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def components_from_coords(coords, threshold):
    n = len(coords)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pair_distances = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            d = math.sqrt(dx * dx + dy * dy)
            pair_distances.append((d, i + 1, j + 1))
            if d <= threshold:
                union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i + 1)

    comps = sorted(
        [tuple(v) for v in groups.values() if len(v) > 1],
        key=lambda x: (x[0], len(x), x),
    )
    signature = " | ".join(",".join(map(str, c)) for c in comps) if comps else "none"
    min_pair = min(pair_distances)[0]
    min_pairs = [(i, j, d) for d, i, j in sorted(pair_distances)[:10]]

    return signature, comps, min_pair, min_pairs

def quotient_edges(edges, comps):
    mapping = {}
    label = 1

    for comp in comps:
        for v in comp:
            mapping[v] = label
        label += 1

    for v in range(1, 13):
        if v not in mapping:
            mapping[v] = label
            label += 1

    q_edges = set()
    loops = []
    for i, j in edges:
        a = mapping[i + 1]
        b = mapping[j + 1]
        if a == b:
            loops.append((i + 1, j + 1))
        else:
            q_edges.add(tuple(sorted((a, b))))

    return {
        "quotient_vertex_count": len(set(mapping.values())),
        "quotient_edge_count": len(q_edges),
        "collapsed_edge_loops": loops,
        "collapsed_edge_loop_count": len(loops),
        "mapping": mapping,
    }

def main():
    edges = load_edges()
    n = max(max(i, j) for i, j in edges) + 1

    runs = 300
    max_nfev = 50000
    scale = 4.0
    seed0 = 202605242
    workers = max(1, min(12, (os.cpu_count() or 2) - 1))

    tasks = [
        (
            seed0 + k * 104729,
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

    rows.sort(key=lambda r: r["max_abs_edge_squared_error"])

    thresholds = [1e-4, 1e-6, 1e-8]
    exact_tol = 1e-8

    all_out = []
    summary = {}

    for threshold in thresholds:
        counts = {}
        examples = {}
        solved = [r for r in rows if r["max_abs_edge_squared_error"] <= exact_tol]

        for r in solved:
            sig, comps, min_pair, min_pairs = components_from_coords(r["coords"], threshold)
            counts[sig] = counts.get(sig, 0) + 1
            if sig not in examples:
                examples[sig] = {
                    "seed": r["seed"],
                    "max_abs": r["max_abs_edge_squared_error"],
                    "rms": r["rms_edge_squared_error"],
                    "min_pair_distance": min_pair,
                    "components": comps,
                    "nearest_pairs": min_pairs,
                    "quotient": quotient_edges(edges, comps),
                }

        ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        summary[str(threshold)] = {
            "threshold": threshold,
            "runs": runs,
            "exact_tol": exact_tol,
            "solved_count": len(solved),
            "signature_count": len(ranked),
            "top_signatures": [
                {
                    "signature": sig,
                    "count": count,
                    "fraction": count / len(solved) if solved else 0,
                    "example": examples[sig],
                }
                for sig, count in ranked[:20]
            ],
        }

        for sig, count in ranked:
            exm = examples[sig]
            all_out.append({
                "threshold": threshold,
                "signature": sig,
                "count": count,
                "fraction": count / len(solved) if solved else 0,
                "example_seed": exm["seed"],
                "example_max_abs": exm["max_abs"],
                "example_min_pair_distance": exm["min_pair_distance"],
                "quotient_vertex_count": exm["quotient"]["quotient_vertex_count"],
                "quotient_edge_count": exm["quotient"]["quotient_edge_count"],
                "collapsed_edge_loop_count": exm["quotient"]["collapsed_edge_loop_count"],
                "collapsed_edge_loops": " ".join(f"{i}-{j}" for i, j in exm["quotient"]["collapsed_edge_loops"]),
            })

    with (outdir / "collision_signature_summary.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "threshold",
            "signature",
            "count",
            "fraction",
            "example_seed",
            "example_max_abs",
            "example_min_pair_distance",
            "quotient_vertex_count",
            "quotient_edge_count",
            "collapsed_edge_loop_count",
            "collapsed_edge_loops",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_out)

    (outdir / "collision_signature_details.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=== COLLISION SIGNATURES ===")
    for threshold in thresholds:
        s = summary[str(threshold)]
        print(f"\nthreshold={threshold} solved={s['solved_count']} signatures={s['signature_count']}")
        for item in s["top_signatures"][:10]:
            q = item["example"]["quotient"]
            print(
                f"count={item['count']:<4} "
                f"frac={item['fraction']:.3f} "
                f"sig={item['signature']} "
                f"qV={q['quotient_vertex_count']} "
                f"qE={q['quotient_edge_count']} "
                f"loops={q['collapsed_edge_loop_count']}"
            )

    print("\nWROTE:")
    print(outdir / "collision_signature_summary.csv")
    print(outdir / "collision_signature_details.json")

if __name__ == "__main__":
    main()
