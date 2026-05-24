from pathlib import Path
import json, csv, itertools, collections

root = Path("n25_global_proof_search")
summary_path = root / "subcore_021_collision_quotients" / "collision_quotients_summary.json"
outdir = root / "subcore_021_collision_quotient_certificate"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3, 12)

def norm_edge(a, b):
    return tuple(sorted((a, b)))

def verify_branch(branch_name, branch):
    q_edges = {tuple(e) for e in branch["quotient_edges"]}
    mapping = {int(k): int(v) for k, v in branch["mapping"].items()}

    a, b = TARGET
    qa, qb = mapping[a], mapping[b]
    target_q = norm_edge(qa, qb)

    result = {
        "branch": branch_name,
        "target_original_pair": list(TARGET),
        "target_quotient_pair": list(target_q),
        "target_is_loop": qa == qb,
        "quotient_vertex_count": branch["quotient_vertex_count"],
        "quotient_edge_count": branch["quotient_edge_count"],
        "quotient_edges": [list(e) for e in sorted(q_edges)],
        "components": branch["components"],
        "valid": False,
        "reason": "",
        "certificate_type": "",
    }

    if qa == qb:
        result["valid"] = True
        result["certificate_type"] = "target_collapses_to_loop"
        result["reason"] = (
            "The target pair 3-12 is identified in the collision quotient. "
            "A unit edge between distinct points cannot be represented by a loop."
        )
        return result

    # Check opposite-distance relation:
    # target endpoints share two common quotient neighbors c,d,
    # and c-d is a quotient unit edge. Then |target|^2 + |c-d|^2 = 4,
    # so |target|^2 = 3.
    nb = collections.defaultdict(set)
    for x, y in q_edges:
        nb[x].add(y)
        nb[y].add(x)

    common = sorted(nb[qa] & nb[qb])
    witnesses = []
    for c, d in itertools.combinations(common, 2):
        if norm_edge(c, d) in q_edges:
            witnesses.append({
                "common_neighbors": [c, d],
                "neighbor_edge": [c, d],
                "relation": f"|Q{qa}-Q{qb}|^2 + |Q{c}-Q{d}|^2 = 4",
                "neighbor_edge_squared_distance": 1,
                "forced_target_squared_distance": 3,
            })

    if witnesses:
        result["valid"] = True
        result["certificate_type"] = "opposite_distance_forces_sqrt3"
        result["reason"] = (
            "The target quotient pair has two common unit-neighbors that are "
            "unit distance apart. The opposite-distance relation forces the "
            "target squared distance to be 3, not 1."
        )
        result["witnesses"] = witnesses
        return result

    result["reason"] = "No loop or opposite-distance witness found."
    return result

summary = json.loads(summary_path.read_text(encoding="utf-8"))
branches = {}

print("=== SUBCORE 021 COLLISION QUOTIENT CERTIFICATE ===")

for name, branch in summary.items():
    cert = verify_branch(name, branch)
    branches[name] = cert

    print(f"\nbranch={name}")
    print("certificate_type:", cert["certificate_type"])
    print("valid:", cert["valid"])
    print("target_quotient_pair:", cert["target_quotient_pair"])
    print("reason:", cert["reason"])

    if "witnesses" in cert:
        for w in cert["witnesses"]:
            print(
                "witness:",
                f"common_neighbors={w['common_neighbors']}",
                f"neighbor_edge={w['neighbor_edge']}",
                f"forced_target_squared_distance={w['forced_target_squared_distance']}",
            )

overall = {
    "source": str(summary_path),
    "original_graph": "subcore_021_without_3_12",
    "target_edge_to_reinsert": [3, 12],
    "claim": (
        "For the two observed exact collision quotient branches of "
        "subcore_021 without edge 3-12, reinserting edge 3-12 is impossible: "
        "in branch d2_0 it becomes a loop, and in branch d2_3 it is forced "
        "to have squared distance 3."
    ),
    "status": (
        "Computational branch certificate for the observed quotient branches. "
        "Not yet a universal proof that these are the only possible exact "
        "branches."
    ),
    "branches": branches,
    "all_observed_branches_certified": all(b["valid"] for b in branches.values()),
    "remaining_gap": (
        "Prove exhaustively or by interval/algebraic means that every exact "
        "realization of the 24-edge core falls into one of these collision "
        "quotients, and then lift the contradiction back to the full 25-edge "
        "subcore_021."
    ),
}

(outdir / "collision_quotient_certificate.json").write_text(
    json.dumps(overall, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nall_observed_branches_certified:", overall["all_observed_branches_certified"])
print("\nWROTE:")
print(outdir / "collision_quotient_certificate.json")
