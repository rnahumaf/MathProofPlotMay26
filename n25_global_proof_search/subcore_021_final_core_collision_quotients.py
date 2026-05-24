from pathlib import Path
import csv, json, math, collections, itertools
import numpy as np

from geometric_embedder import worker as exact_worker

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_final_survivor_greedy_core" / "final_greedy_core_edges.csv"
runs_path = root / "subcore_021_final_core_remove_3_11_distance_audit" / "remove_3_11_distance_runs.csv"
outdir = root / "subcore_021_final_core_collision_quotients"
outdir.mkdir(parents=True, exist_ok=True)

REMOVED = (3 - 1, 11 - 1)
TARGET_1BASED = (3, 11)

def read_edges_0based(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [(int(r["i"]) - 1, int(r["j"]) - 1) for r in csv.DictReader(f)]

def read_runs(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def d2(coords, a1, b1):
    p = np.array(coords[a1 - 1], dtype=float)
    q = np.array(coords[b1 - 1], dtype=float)
    d = p - q
    return float(d @ d)

def edge_label(e0):
    return f"{e0[0] + 1}-{e0[1] + 1}"

def collision_components(coords, threshold=1e-8):
    n = len(coords)
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            if d2(coords, i, j) <= threshold:
                union(i, j)

    groups = collections.defaultdict(list)
    for i in range(1, n + 1):
        groups[find(i)].append(i)

    return sorted([tuple(v) for v in groups.values()], key=lambda c: (c[0], len(c), c))

def quotient(edges_0based, comps, target_1based):
    mapping = {}
    for idx, comp in enumerate(comps, 1):
        for v in comp:
            mapping[v] = idx

    q_edges = set()
    loops = []
    lifts = collections.defaultdict(list)

    for a0, b0 in edges_0based:
        a, b = a0 + 1, b0 + 1
        qa, qb = mapping[a], mapping[b]
        if qa == qb:
            loops.append((a, b))
        else:
            qe = tuple(sorted((qa, qb)))
            q_edges.add(qe)
            lifts[qe].append((a, b))

    ta, tb = target_1based
    target_q = tuple(sorted((mapping[ta], mapping[tb])))

    nb = collections.defaultdict(set)
    for a, b in q_edges:
        nb[a].add(b)
        nb[b].add(a)

    opposite_witnesses = []
    if target_q[0] != target_q[1]:
        common = sorted(nb[target_q[0]] & nb[target_q[1]])
        for c, d in itertools.combinations(common, 2):
            if tuple(sorted((c, d))) in q_edges:
                opposite_witnesses.append((c, d))

    if target_q[0] == target_q[1]:
        target_status = "loop"
    elif opposite_witnesses:
        target_status = "forced_sqrt3_by_opposite_relation"
    elif target_q in q_edges:
        target_status = "already_unit_edge_in_quotient"
    else:
        target_status = "unresolved"

    return {
        "components": comps,
        "mapping": mapping,
        "quotient_vertex_count": len(comps),
        "quotient_edge_count": len(q_edges),
        "quotient_edges": sorted(q_edges),
        "original_edge_loops": loops,
        "target_q": target_q,
        "target_status": target_status,
        "opposite_witnesses": opposite_witnesses,
        "edge_lifts": {
            f"{a}-{b}": lifts[(a, b)]
            for a, b in sorted(lifts)
        },
    }

def choose_branch_rows(rows):
    solved = [
        r for r in rows
        if r["removed_pair_d2"] not in ("", "None", None)
        and float(r["max_abs_edge_squared_error"]) <= 1e-8
    ]

    d0 = [
        r for r in solved
        if abs(float(r["removed_pair_d2"])) <= 1e-8
    ]
    d3 = [
        r for r in solved
        if abs(float(r["removed_pair_d2"]) - 3.0) <= 1e-6
    ]

    if not d0:
        raise RuntimeError("No d2≈0 solved branch found")
    if not d3:
        raise RuntimeError("No d2≈3 solved branch found")

    d0.sort(key=lambda r: float(r["max_abs_edge_squared_error"]))
    d3.sort(key=lambda r: float(r["max_abs_edge_squared_error"]))

    return {
        "d2_0": d0[0],
        "d2_3": d3[0],
    }

def write_edges(path, q_edges):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j"])
        w.writerows(q_edges)

def verify_certificate(q):
    if q["target_status"] == "loop":
        return {
            "valid": True,
            "certificate_type": "target_collapses_to_loop",
            "reason": "The target pair is identified in the collision quotient, so reinserting it as a unit edge would be a loop.",
        }

    if q["target_status"] == "forced_sqrt3_by_opposite_relation":
        witnesses = []
        for c, d in q["opposite_witnesses"]:
            witnesses.append({
                "common_neighbors": [c, d],
                "neighbor_edge": [c, d],
                "relation": f"|Q{q['target_q'][0]}-Q{q['target_q'][1]}|^2 + |Q{c}-Q{d}|^2 = 4",
                "neighbor_edge_squared_distance": 1,
                "forced_target_squared_distance": 3,
            })
        return {
            "valid": True,
            "certificate_type": "opposite_distance_forces_sqrt3",
            "reason": "The target quotient pair has two common unit-neighbors that are unit distance apart, forcing target squared distance 3.",
            "witnesses": witnesses,
        }

    if q["target_status"] == "already_unit_edge_in_quotient":
        return {
            "valid": False,
            "certificate_type": "already_unit_edge_in_quotient",
            "reason": "The target pair is already a quotient unit edge; this is degenerate but not an immediate contradiction.",
        }

    return {
        "valid": False,
        "certificate_type": "unresolved",
        "reason": "No loop or opposite-distance witness found.",
    }

def main():
    full_edges = read_edges_0based(edges_path)
    core_edges = [e for e in full_edges if tuple(sorted(e)) != tuple(sorted(REMOVED))]
    n = max(max(i, j) for i, j in full_edges) + 1

    runs = read_runs(runs_path)
    branch_rows = choose_branch_rows(runs)

    print("=== SUBCORE 021 FINAL CORE COLLISION QUOTIENTS ===")
    print("full_edge_count:", len(full_edges))
    print("without_removed_edge_count:", len(core_edges))
    print("removed_target:", "3-11")

    summary = {}

    for branch, row in branch_rows.items():
        seed = int(row["seed"])
        scale = float(row["scale"])
        task = (
            seed,
            core_edges,
            n,
            160000,
            scale,
        )
        result = exact_worker(task)
        coords = np.array(result["coords"], dtype=float)

        target_d2 = d2(coords, *TARGET_1BASED)
        comps = collision_components(coords, threshold=1e-8)
        q = quotient(core_edges, comps, TARGET_1BASED)
        cert = verify_certificate(q)

        np.savetxt(outdir / f"{branch}_coords.csv", coords, delimiter=",", header="x,y", comments="")
        write_edges(outdir / f"{branch}_quotient_edges.csv", q["quotient_edges"])

        summary[branch] = {
            "source_seed": seed,
            "source_scale": scale,
            "source_removed_pair_d2": float(row["removed_pair_d2"]),
            "reproduced_max_abs": result["max_abs_edge_squared_error"],
            "reproduced_rms": result["rms_edge_squared_error"],
            "target_d2": target_d2,
            **q,
            "certificate": cert,
        }

        print(f"\nbranch={branch}")
        print("seed:", seed, "scale:", scale)
        print("target_d2:", target_d2)
        print("reproduced_max_abs:", result["max_abs_edge_squared_error"])
        print("components:")
        for idx, comp in enumerate(comps, 1):
            print(f"  Q{idx}: {comp}")
        print("quotient V/E:", q["quotient_vertex_count"], q["quotient_edge_count"])
        print("original-edge loops:", q["original_edge_loops"] or "none")
        print("target_q:", q["target_q"])
        print("target_status:", q["target_status"])
        print("certificate_type:", cert["certificate_type"])
        print("certificate_valid:", cert["valid"])
        if "witnesses" in cert:
            for w in cert["witnesses"]:
                print(
                    "witness:",
                    f"common_neighbors={w['common_neighbors']}",
                    f"neighbor_edge={w['neighbor_edge']}",
                    f"forced_target_squared_distance={w['forced_target_squared_distance']}",
                )
        print("quotient_edges:", q["quotient_edges"])

    overall = {
        "source_edges": str(edges_path),
        "removed_target": [3, 11],
        "claim": (
            "For the two observed exact collision quotient branches of the final "
            "18-edge core with edge 3-11 removed, reinserting edge 3-11 is impossible "
            "if the branch certificate is loop or forced_sqrt3."
        ),
        "all_observed_branches_certified": all(
            item["certificate"]["valid"] for item in summary.values()
        ),
        "branches": summary,
    }

    (outdir / "final_core_collision_quotients_summary.json").write_text(
        json.dumps(overall, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nall_observed_branches_certified:", overall["all_observed_branches_certified"])
    print("\nWROTE:")
    print(outdir / "final_core_collision_quotients_summary.json")
    print(outdir / "d2_0_quotient_edges.csv")
    print(outdir / "d2_3_quotient_edges.csv")

if __name__ == "__main__":
    main()
