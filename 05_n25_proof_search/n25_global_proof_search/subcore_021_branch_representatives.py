from pathlib import Path
import csv, json, math, os, random, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import freeze_support

import numpy as np

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
outdir = root / "subcore_021_branch_representatives"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3 - 1, 12 - 1)
runs = 800
scale_values = [2.0, 4.0, 8.0]
max_nfev = 120000
workers = max(1, min(12, (os.cpu_count() or 2) - 1))
seed0 = 202605249

def read_edges(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def d2(coords, a, b):
    p = np.array(coords[a])
    q = np.array(coords[b])
    d = p - q
    return float(d @ d)

def distance_table(coords, edges):
    edge_set = {tuple(sorted(e)) for e in edges}
    rows = []
    n = len(coords)
    for i in range(n):
        for j in range(i + 1, n):
            value = d2(coords, i, j)
            rows.append({
                "i": i + 1,
                "j": j + 1,
                "pair": f"{i+1}-{j+1}",
                "is_edge": tuple(sorted((i, j))) in edge_set,
                "d2": value,
                "dist": math.sqrt(max(value, 0.0)),
                "near_0": abs(value) <= 1e-8,
                "near_1": abs(value - 1.0) <= 1e-8,
                "near_3": abs(value - 3.0) <= 1e-8,
                "abs_to_0": abs(value),
                "abs_to_1": abs(value - 1.0),
                "abs_to_3": abs(value - 3.0),
            })
    return rows

def rigidity_matrix(coords, edges):
    coords = np.array(coords, dtype=float)
    n = coords.shape[0]
    mat = np.zeros((len(edges), 2 * n), dtype=float)
    for r, (i, j) in enumerate(edges):
        dx = coords[i, 0] - coords[j, 0]
        dy = coords[i, 1] - coords[j, 1]
        mat[r, 2*i] = dx
        mat[r, 2*i+1] = dy
        mat[r, 2*j] = -dx
        mat[r, 2*j+1] = -dy
    return mat

def numeric_rank(mat, tol=1e-7):
    s = np.linalg.svd(mat, compute_uv=False)
    return int(np.sum(s > tol)), s.tolist()

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

def branch_name(value):
    if abs(value) <= 1e-8:
        return "d2_0"
    if abs(value - 3.0) <= 1e-8:
        return "d2_3"
    if abs(value - 1.0) <= 1e-8:
        return "d2_1"
    return "other"

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def main():
    edges = read_edges(edges_path)
    n = max(max(i, j) for i, j in edges) + 1

    print("=== SUBCORE 021 BRANCH REPRESENTATIVES ===")
    print("edges:", len(edges), "target:", "3-12")

    all_solved = []
    for scale in scale_values:
        rows = run_batch(edges, n, scale)
        solved = [r for r in rows if r["max_abs_edge_squared_error"] <= 1e-8]
        for r in solved:
            value = d2(r["coords"], TARGET[0], TARGET[1])
            r["target_d2"] = value
            r["branch"] = branch_name(value)
            r["scale"] = scale
        all_solved.extend(solved)

        counts = {}
        for r in solved:
            counts[r["branch"]] = counts.get(r["branch"], 0) + 1
        print(f"scale={scale} solved={len(solved)}/{len(rows)} counts={counts}", flush=True)

    branches = {}
    for branch in ["d2_0", "d2_3", "other", "d2_1"]:
        candidates = [r for r in all_solved if r["branch"] == branch]
        if not candidates:
            continue
        candidates.sort(key=lambda r: r["max_abs_edge_squared_error"])
        branches[branch] = candidates[0]

    summary = {
        "source_edges": str(edges_path),
        "edge_count": len(edges),
        "target_pair": [3, 12],
        "total_solved": len(all_solved),
        "branch_counts": {},
        "representatives": {},
    }

    for r in all_solved:
        summary["branch_counts"][r["branch"]] = summary["branch_counts"].get(r["branch"], 0) + 1

    for branch, rep in branches.items():
        coords = np.array(rep["coords"], dtype=float)
        distances = distance_table(coords, edges)

        rank, singular = numeric_rank(rigidity_matrix(coords, edges))
        rank_aug, singular_aug = numeric_rank(rigidity_matrix(coords, edges + [TARGET]))

        near0 = [row for row in distances if row["near_0"]]
        near1_nonedges = [row for row in distances if row["near_1"] and not row["is_edge"]]
        near3 = [row for row in distances if row["near_3"]]

        print(f"\nbranch={branch}")
        print(f"seed={rep['seed']} scale={rep['scale']} max_abs={rep['max_abs_edge_squared_error']:.3e}")
        print(f"target_d2={rep['target_d2']:.15g}")
        print(f"rigidity_rank={rank} max_rank={2*n-3} rank_with_3_12={rank_aug}")
        print("near-zero pairs:", " ".join(row["pair"] for row in near0) or "none")
        print("nonedge unit pairs:", " ".join(row["pair"] for row in near1_nonedges[:30]) or "none")
        print("sqrt3 pairs:", " ".join(row["pair"] for row in near3[:30]) or "none")

        np.savetxt(outdir / f"{branch}_coords.csv", coords, delimiter=",", header="x,y", comments="")
        write_csv(outdir / f"{branch}_distance_table.csv", sorted(distances, key=lambda x: (x["dist"], x["pair"])))

        summary["representatives"][branch] = {
            "seed": rep["seed"],
            "scale": rep["scale"],
            "max_abs": rep["max_abs_edge_squared_error"],
            "target_d2": rep["target_d2"],
            "rigidity_rank": rank,
            "rigidity_rank_with_3_12": rank_aug,
            "max_planar_rank": 2*n - 3,
            "near_zero_pairs": [row["pair"] for row in near0],
            "nonedge_unit_pairs": [row["pair"] for row in near1_nonedges],
            "sqrt3_pairs": [row["pair"] for row in near3],
            "smallest_distances": [
                {
                    "pair": row["pair"],
                    "is_edge": row["is_edge"],
                    "d2": row["d2"],
                    "dist": row["dist"],
                }
                for row in sorted(distances, key=lambda x: x["dist"])[:20]
            ],
        }

    (outdir / "branch_representatives_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nWROTE:")
    print(outdir / "branch_representatives_summary.json")
    for branch in branches:
        print(outdir / f"{branch}_coords.csv")
        print(outdir / f"{branch}_distance_table.csv")

if __name__ == "__main__":
    freeze_support()
    main()
