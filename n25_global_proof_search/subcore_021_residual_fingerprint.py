from pathlib import Path
import csv, json, math, random, statistics
import numpy as np
from scipy.optimize import least_squares

root = Path("n25_global_proof_search")
edges_path = root / "hard_subcore_exact_filter_checks" / "subcore_021_edges.csv"
runs_path = root / "subcore_021_with_derived_distance" / "subcore_021_with_derived_distance_runs.csv"
outdir = root / "subcore_021_residual_fingerprint"
outdir.mkdir(parents=True, exist_ok=True)

DERIVED = [(1 - 1, 9 - 1, 3.0)]

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

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

def residuals(vals, n, edges, fixed_edge, derived_weight):
    coords = decode(vals, n, fixed_edge)
    out = []
    for i, j in edges:
        d = coords[i] - coords[j]
        out.append(float(d @ d - 1.0))
    for i, j, target in DERIVED:
        d = coords[i] - coords[j]
        out.append(derived_weight * float(d @ d - target))
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

    derived_rows = []
    for i, j, target in DERIVED:
        d = coords[i] - coords[j]
        d2 = float(d @ d)
        err = d2 - target
        derived_rows.append({
            "pair": f"{i+1}-{j+1}",
            "i": i + 1,
            "j": j + 1,
            "target": target,
            "d2": d2,
            "err": err,
            "abs_err": abs(err),
        })

    pair_rows = []
    n = len(coords)
    edge_set = {tuple(sorted(e)) for e in edges}
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

    max_edge_abs = max(r["abs_err"] for r in edge_rows)
    rms_edge = math.sqrt(statistics.mean(r["err"] * r["err"] for r in edge_rows))
    max_derived_abs = max(r["abs_err"] for r in derived_rows)

    return edge_rows, derived_rows, pair_rows, max_edge_abs, rms_edge, max_derived_abs

edges = read_edges(edges_path)
n = max(max(i, j) for i, j in edges) + 1
fixed_edge = edges[0]

with runs_path.open(newline="", encoding="utf-8") as f:
    run_rows = list(csv.DictReader(f))

# Seleciona bons mínimos por critério combinado.
for r in run_rows:
    r["_score"] = float(r["max_edge_abs"]) + float(r["max_derived_abs"])
    r["_edge"] = float(r["max_edge_abs"])
    r["_derived"] = float(r["max_derived_abs"])

selected = sorted(run_rows, key=lambda r: (r["_score"], r["_edge"]))[:12]

all_edge_residuals = {}
case_summaries = []
case_details = []

print("=== SUBCORE 021 RESIDUAL FINGERPRINT ===")

for case_idx, row in enumerate(selected, 1):
    seed = int(row["seed"])
    scale = float(row["scale"])
    weight = float(row["derived_weight"])

    x0 = initial_values(n, fixed_edge, seed, scale)
    res = least_squares(
        residuals,
        x0,
        args=(n, edges, fixed_edge, weight),
        method="trf",
        loss="soft_l1",
        f_scale=1.0,
        ftol=1e-14,
        xtol=1e-14,
        gtol=1e-14,
        max_nfev=180000,
    )
    coords = decode(res.x, n, fixed_edge)
    edge_rows, derived_rows, pair_rows, max_edge_abs, rms_edge, max_derived_abs = diagnostics(coords, edges)

    edge_rows_sorted = sorted(edge_rows, key=lambda x: -x["abs_err"])
    top_edges = edge_rows_sorted[:8]

    for e in edge_rows:
        all_edge_residuals.setdefault(e["edge"], []).append(e["err"])

    summary = {
        "case": case_idx,
        "seed": seed,
        "scale": scale,
        "derived_weight": weight,
        "max_edge_abs": max_edge_abs,
        "rms_edge": rms_edge,
        "max_derived_abs": max_derived_abs,
        "nfev": int(res.nfev),
        "top_edges": top_edges,
        "derived": derived_rows,
    }
    case_summaries.append(summary)

    print(
        f"\ncase={case_idx} seed={seed} scale={scale} w={weight} "
        f"max_edge={max_edge_abs:.6e} rms={rms_edge:.6e} "
        f"max_derived={max_derived_abs:.6e}"
    )
    print("top failing edges:")
    for e in top_edges:
        print(f"  {e['edge']}: d2={e['d2']:.9f} err={e['err']:+.6e}")

    print("derived:")
    for d in derived_rows:
        print(f"  {d['pair']}: d2={d['d2']:.9f} target={d['target']} err={d['err']:+.6e}")

    # Salva coordenadas do melhor caso.
    if case_idx == 1:
        np.savetxt(outdir / "best_case_coords.csv", coords, delimiter=",", header="x,y", comments="")
        with (outdir / "best_case_edge_residuals.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(edge_rows[0].keys()))
            writer.writeheader()
            writer.writerows(edge_rows_sorted)
        with (outdir / "best_case_pair_distances.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(pair_rows[0].keys()))
            writer.writeheader()
            writer.writerows(sorted(pair_rows, key=lambda x: x["dist"]))

# Agregação por aresta: quais falham com estabilidade?
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

with (outdir / "residual_fingerprint_summary.json").open("w", encoding="utf-8") as f:
    json.dump({
        "selected_cases": case_summaries,
        "stable_failing_edges": agg_sorted,
    }, f, indent=2, ensure_ascii=False)

with (outdir / "stable_failing_edges.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(agg_sorted[0].keys()))
    writer.writeheader()
    writer.writerows(agg_sorted)

print("\nWROTE:")
print(outdir / "best_case_coords.csv")
print(outdir / "best_case_edge_residuals.csv")
print(outdir / "best_case_pair_distances.csv")
print(outdir / "stable_failing_edges.csv")
print(outdir / "residual_fingerprint_summary.json")
