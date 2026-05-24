from pathlib import Path
import csv, json, math, random, statistics
import numpy as np
from scipy.optimize import least_squares

root = Path("n25_global_proof_search")
runs_path = root / "subcore_021_final_high_block_survivor_probe" / "final_high_block_survivor_probe_runs.csv"
meta_path = root / "subcore_021_final_high_block_survivor_probe" / "final_high_block_survivor_probe_metadata.json"
outdir = root / "subcore_021_final_survivor_residual_fingerprint"
outdir.mkdir(parents=True, exist_ok=True)

def parse_edges(s):
    edges = []
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a) - 1, int(b) - 1))))
    return sorted(set(edges))

def initial_values(n, fixed_edge, seed, scale):
    rng = random.Random(seed)
    vals = []
    for i in range(n):
        if i in fixed_edge:
            continue
        angle = rng.random() * 2 * math.pi
        radius = scale * math.sqrt(rng.random())
        vals.extend([radius * math.cos(angle), radius * math.sin(angle)])
    return np.array(vals, dtype=float)

def decode(vals, n, fixed_edge):
    coords = np.zeros((n, 2), dtype=float)
    a, b = fixed_edge
    coords[a] = [0.0, 0.0]
    coords[b] = [1.0, 0.0]
    k = 0
    for i in range(n):
        if i in fixed_edge:
            continue
        coords[i] = [vals[k], vals[k + 1]]
        k += 2
    return coords

def residuals(vals, n, edges, fixed_edge):
    coords = decode(vals, n, fixed_edge)
    out = []
    for i, j in edges:
        d = coords[i] - coords[j]
        out.append(float(d @ d - 1.0))
    return np.array(out, dtype=float)

def diagnostics(coords, edges):
    edge_rows = []
    for i, j in edges:
        d = coords[i] - coords[j]
        d2 = float(d @ d)
        err = d2 - 1.0
        edge_rows.append({
            "edge": f"{i+1}-{j+1}",
            "i": i + 1,
            "j": j + 1,
            "d2": d2,
            "err": err,
            "abs_err": abs(err),
        })

    pair_rows = []
    n = len(coords)
    edge_set = set(edges)
    for i in range(n):
        for j in range(i + 1, n):
            d = coords[i] - coords[j]
            d2 = float(d @ d)
            pair_rows.append({
                "pair": f"{i+1}-{j+1}",
                "i": i + 1,
                "j": j + 1,
                "is_edge": tuple(sorted((i, j))) in edge_set,
                "d2": d2,
                "dist": math.sqrt(max(d2, 0.0)),
                "abs_to_1": abs(d2 - 1.0),
                "abs_to_3": abs(d2 - 3.0),
            })

    max_abs = max(r["abs_err"] for r in edge_rows)
    rms = math.sqrt(statistics.mean(r["err"] * r["err"] for r in edge_rows))
    return edge_rows, pair_rows, max_abs, rms

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

meta = json.loads(meta_path.read_text(encoding="utf-8"))
edges = parse_edges(meta["q_edges_plus_target"])
n = int(meta["q_vertex_count"])
fixed_edge = edges[0]

with runs_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    r["_err"] = float(r["max_abs_edge_squared_error"])

selected = sorted(rows, key=lambda r: r["_err"])[:12]

print("=== SUBCORE 021 FINAL SURVIVOR RESIDUAL FINGERPRINT ===")
print("source_index:", meta["source_index"])
print("qV:", n)
print("edge_count:", len(edges))
print("target_q:", meta["target_q"])
print("representative_blocks:", meta["representative_blocks"])

all_edge_residuals = {}
case_summaries = []

for case_idx, row in enumerate(selected, 1):
    seed = int(row["seed"])
    scale = float(row["scale"])

    x0 = initial_values(n, fixed_edge, seed, scale)
    res = least_squares(
        residuals,
        x0,
        args=(n, edges, fixed_edge),
        method="trf",
        loss="soft_l1",
        f_scale=1.0,
        ftol=1e-14,
        xtol=1e-14,
        gtol=1e-14,
        max_nfev=180000,
    )

    coords = decode(res.x, n, fixed_edge)
    edge_rows, pair_rows, max_abs, rms = diagnostics(coords, edges)
    edge_rows_sorted = sorted(edge_rows, key=lambda x: -x["abs_err"])

    print(
        f"\ncase={case_idx} seed={seed} scale={scale} "
        f"max_abs={max_abs:.6e} rms={rms:.6e}"
    )
    print("top failing edges:")
    for e in edge_rows_sorted[:10]:
        print(f"  {e['edge']}: d2={e['d2']:.9f} err={e['err']:+.6e}")

    print("nearest nonedge pairs:")
    nonedges = [p for p in sorted(pair_rows, key=lambda x: x["dist"]) if not p["is_edge"]]
    for p in nonedges[:10]:
        print(f"  {p['pair']}: dist={p['dist']:.6e} d2={p['d2']:.6e}")

    for e in edge_rows:
        all_edge_residuals.setdefault(e["edge"], []).append(e["err"])

    if case_idx == 1:
        np.savetxt(outdir / "best_case_coords.csv", coords, delimiter=",", header="x,y", comments="")
        write_csv(outdir / "best_case_edge_residuals.csv", edge_rows_sorted)
        write_csv(outdir / "best_case_pair_distances.csv", sorted(pair_rows, key=lambda x: x["dist"]))

    case_summaries.append({
        "case": case_idx,
        "seed": seed,
        "scale": scale,
        "max_abs": max_abs,
        "rms": rms,
        "top_edges": edge_rows_sorted[:10],
    })

agg = []
for edge, vals in all_edge_residuals.items():
    abs_vals = [abs(v) for v in vals]
    signs = [1 if v > 0 else -1 if v < 0 else 0 for v in vals]
    agg.append({
        "edge": edge,
        "mean_err": statistics.mean(vals),
        "median_err": statistics.median(vals),
        "mean_abs": statistics.mean(abs_vals),
        "median_abs": statistics.median(abs_vals),
        "max_abs": max(abs_vals),
        "positive_count": sum(1 for s in signs if s > 0),
        "negative_count": sum(1 for s in signs if s < 0),
        "sample_count": len(vals),
    })

agg_sorted = sorted(agg, key=lambda x: -x["mean_abs"])

print("\n=== STABLE FAILING EDGES ===")
for a in agg_sorted[:15]:
    print(
        f"{a['edge']}: mean_abs={a['mean_abs']:.6e} "
        f"median_abs={a['median_abs']:.6e} "
        f"mean_err={a['mean_err']:+.6e} "
        f"signs=+{a['positive_count']}/-{a['negative_count']}"
    )

write_csv(outdir / "stable_failing_edges.csv", agg_sorted)
(outdir / "residual_fingerprint_summary.json").write_text(
    json.dumps({
        "metadata": meta,
        "selected_cases": case_summaries,
        "stable_failing_edges": agg_sorted,
    }, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nWROTE:")
print(outdir / "best_case_coords.csv")
print(outdir / "best_case_edge_residuals.csv")
print(outdir / "best_case_pair_distances.csv")
print(outdir / "stable_failing_edges.csv")
print(outdir / "residual_fingerprint_summary.json")
