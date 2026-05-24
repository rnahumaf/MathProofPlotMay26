from pathlib import Path
import csv, json, itertools, collections, time

root = Path("n25_global_proof_search")
full_edges_path = root / "subcore_021_final_survivor_greedy_core" / "final_greedy_core_edges.csv"
outdir = root / "subcore_021_final_core_collision_partition_enumeration"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3, 11)

OBSERVED = {
    "d2_0": ((1, 8, 9), (2, 4), (3, 10, 11), (5,), (6,), (7,)),
    "d2_3": ((1, 8, 9), (2, 4), (3,), (5,), (6,), (7,), (10, 11)),
}

def read_edges_1based(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [tuple(sorted((int(r["i"]), int(r["j"])))) for r in csv.DictReader(f)]

def norm_edge(a, b):
    return tuple(sorted((a, b)))

def is_independent(block, edge_set):
    for a, b in itertools.combinations(block, 2):
        if norm_edge(a, b) in edge_set:
            return False
    return True

def canonical_partition(blocks):
    return tuple(sorted(tuple(sorted(b)) for b in blocks))

def edge_signature(q_edges):
    return " ".join(f"{a}-{b}" for a, b in sorted(q_edges))

def quotient_from_partition(edges, blocks):
    mapping = {}
    for idx, block in enumerate(blocks, 1):
        for v in block:
            mapping[v] = idx

    q_edges = set()
    loops = []

    for a, b in edges:
        qa, qb = mapping[a], mapping[b]
        if qa == qb:
            loops.append((a, b))
        else:
            q_edges.add(norm_edge(qa, qb))

    qa, qb = mapping[TARGET[0]], mapping[TARGET[1]]
    target_q = norm_edge(qa, qb)

    nb = collections.defaultdict(set)
    for a, b in q_edges:
        nb[a].add(b)
        nb[b].add(a)

    opposite_witnesses = []
    if target_q[0] != target_q[1]:
        common = sorted(nb[target_q[0]] & nb[target_q[1]])
        for c, d in itertools.combinations(common, 2):
            if norm_edge(c, d) in q_edges:
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
        "mapping": mapping,
        "q_vertex_count": len(blocks),
        "q_edge_count": len(q_edges),
        "q_edges": sorted(q_edges),
        "target_q": target_q,
        "target_status": target_status,
        "opposite_witnesses": opposite_witnesses,
        "loops": loops,
    }

def enumerate_independent_partitions(vertices, edge_set):
    results = set()

    def rec(pos, blocks):
        if pos == len(vertices):
            part = canonical_partition(blocks)
            if len(part) < len(vertices):  # exclude singleton/distinct case
                results.add(part)
            return

        v = vertices[pos]

        for i in range(len(blocks)):
            candidate = blocks[i] + [v]
            if is_independent(candidate, edge_set):
                old = blocks[i]
                blocks[i] = candidate
                rec(pos + 1, blocks)
                blocks[i] = old

        blocks.append([v])
        rec(pos + 1, blocks)
        blocks.pop()

    rec(0, [])
    return sorted(results, key=lambda p: (len(p), p))

def blocks_string(part):
    return " | ".join(",".join(map(str, block)) for block in part)

def observed_key(part):
    part = canonical_partition(part)
    for name, observed in OBSERVED.items():
        if part == canonical_partition(observed):
            return name
    return ""

full_edges = read_edges_1based(full_edges_path)
target_edge = norm_edge(*TARGET)
core_edges = [e for e in full_edges if e != target_edge]
edge_set = set(core_edges)
vertices = sorted({v for e in full_edges for v in e})

print("=== SUBCORE 021 FINAL CORE COLLISION PARTITION ENUMERATION ===")
print("full_edge_count:", len(full_edges))
print("core_edge_count_without_3_11:", len(core_edges))
print("vertices:", vertices)
print("target:", TARGET)

t0 = time.time()
parts = enumerate_independent_partitions(vertices, edge_set)
print("candidate collision partitions:", len(parts))
print("enumeration_seconds:", time.time() - t0)

rows = []
unique = {}
status_counts = collections.Counter()
size_counts = collections.Counter()
observed_found = {name: False for name in OBSERVED}

for part in parts:
    q = quotient_from_partition(core_edges, part)
    status_counts[q["target_status"]] += 1
    size_counts[(q["q_vertex_count"], q["q_edge_count"])] += 1

    obs = observed_key(part)
    if obs:
        observed_found[obs] = True

    key = (
        q["target_status"],
        q["q_vertex_count"],
        q["q_edge_count"],
        q["target_q"],
        edge_signature(q["q_edges"]),
    )

    if key not in unique:
        unique[key] = {
            "target_status": q["target_status"],
            "q_vertex_count": q["q_vertex_count"],
            "q_edge_count": q["q_edge_count"],
            "target_q": f"{q['target_q'][0]}-{q['target_q'][1]}",
            "q_edges": edge_signature(q["q_edges"]),
            "representative_blocks": blocks_string(part),
            "opposite_witnesses": " ".join(f"{a}-{b}" for a, b in q["opposite_witnesses"]),
            "observed_branch": obs,
            "partition_count": 0,
        }

    unique[key]["partition_count"] += 1
    if obs:
        unique[key]["observed_branch"] = obs

    rows.append({
        "blocks": blocks_string(part),
        "q_vertex_count": q["q_vertex_count"],
        "q_edge_count": q["q_edge_count"],
        "target_q": f"{q['target_q'][0]}-{q['target_q'][1]}",
        "target_status": q["target_status"],
        "opposite_witnesses": " ".join(f"{a}-{b}" for a, b in q["opposite_witnesses"]),
        "observed_branch": obs,
        "q_edges": edge_signature(q["q_edges"]),
    })

unique_rows = sorted(
    unique.values(),
    key=lambda r: (
        r["target_status"],
        int(r["q_vertex_count"]),
        int(r["q_edge_count"]),
        -int(r["partition_count"]),
        r["target_q"],
        r["representative_blocks"],
    ),
)

with (outdir / "final_core_collision_partitions.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

with (outdir / "final_core_unique_quotient_graphs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(unique_rows[0].keys()))
    w.writeheader()
    w.writerows(unique_rows)

summary = {
    "source_edges": str(full_edges_path),
    "full_edge_count": len(full_edges),
    "core_edge_count_without_target": len(core_edges),
    "target_edge": list(TARGET),
    "collision_partition_count": len(parts),
    "unique_quotient_graph_count": len(unique_rows),
    "status_counts": dict(status_counts),
    "size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(size_counts.items())},
    "observed_found": observed_found,
    "interpretation": (
        "Exhaustive independent collision-partition enumeration for the final "
        "17-edge core obtained by removing target edge 3-11 from the 18-edge core. "
        "The fully singleton qV=11 case is excluded and remains the distinct case."
    ),
}
(outdir / "final_core_collision_partition_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nstatus counts:")
for k, v in status_counts.most_common():
    print(f"{k}: {v}")

print("\nsize counts:")
for k, v in sorted(size_counts.items()):
    print(f"qV={k[0]} qE={k[1]}: {v}")

print("\nobserved found:")
for k, v in observed_found.items():
    print(f"{k}: {v}")

print("\nunique quotient graph count:", len(unique_rows))

print("\nfirst unresolved unique quotients:")
for r in [x for x in unique_rows if x["target_status"] == "unresolved"][:30]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"parts={r['partition_count']} target={r['target_q']} "
        f"blocks={r['representative_blocks']}"
    )

print("\nfirst already-unit unique quotients:")
for r in [x for x in unique_rows if x["target_status"] == "already_unit_edge_in_quotient"][:20]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"parts={r['partition_count']} target={r['target_q']} "
        f"blocks={r['representative_blocks']}"
    )

print("\nWROTE:")
print(outdir / "final_core_collision_partitions.csv")
print(outdir / "final_core_unique_quotient_graphs.csv")
print(outdir / "final_core_collision_partition_summary.json")
