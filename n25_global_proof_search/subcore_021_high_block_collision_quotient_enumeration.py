from pathlib import Path
import csv, json, itertools, collections, time

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
outdir = root / "subcore_021_high_block_collision_quotient_enumeration"
outdir.mkdir(parents=True, exist_ok=True)

TARGET = (3, 12)

def read_edges(path):
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

    common = sorted(nb[target_q[0]] & nb[target_q[1]]) if target_q[0] != target_q[1] else []
    opposite_witnesses = []
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
        "blocks": blocks,
        "q_vertex_count": len(blocks),
        "q_edge_count": len(q_edges),
        "q_edges": sorted(q_edges),
        "loops": loops,
        "target_q": target_q,
        "target_status": target_status,
        "opposite_witnesses": opposite_witnesses,
    }

def enumerate_partitions(vertices, edge_set, min_blocks=9, max_blocks=11, max_block_size=4):
    results = set()

    def rec(pos, blocks):
        remaining = len(vertices) - pos

        # Pruning: even if every remaining vertex becomes singleton,
        # can we still reach min_blocks?
        if len(blocks) + remaining < min_blocks:
            return

        # Pruning: already too many blocks.
        if len(blocks) > max_blocks:
            return

        if pos == len(vertices):
            if min_blocks <= len(blocks) <= max_blocks:
                results.add(canonical_partition(blocks))
            return

        v = vertices[pos]

        for i in range(len(blocks)):
            if len(blocks[i]) >= max_block_size:
                continue
            candidate = blocks[i] + [v]
            if is_independent(candidate, edge_set):
                old = blocks[i]
                blocks[i] = candidate
                rec(pos + 1, blocks)
                blocks[i] = old

        if len(blocks) < max_blocks:
            blocks.append([v])
            rec(pos + 1, blocks)
            blocks.pop()

    rec(0, [])
    return sorted(results, key=lambda x: (len(x), x))

def edge_signature(q_edges):
    return " ".join(f"{a}-{b}" for a, b in sorted(q_edges))

edges = read_edges(edges_path)
edge_set = set(edges)
vertices = sorted({v for e in edges for v in e})

print("=== SUBCORE 021 HIGH-BLOCK COLLISION QUOTIENT ENUMERATION ===")
print("vertices:", vertices)
print("edge_count:", len(edges))
print("target:", TARGET)
print("enumerating qV=9..11")

t0 = time.time()
parts = enumerate_partitions(
    vertices,
    edge_set,
    min_blocks=9,
    max_blocks=11,
    max_block_size=4,
)
print("candidate independent-set partitions:", len(parts))
print("enumeration_seconds:", time.time() - t0)

rows = []
status_counts = collections.Counter()
size_counts = collections.Counter()
unique = {}

for part in parts:
    q = quotient_from_partition(edges, part)
    status_counts[q["target_status"]] += 1
    size_counts[(q["q_vertex_count"], q["q_edge_count"])] += 1

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
            "representative_blocks": " | ".join(",".join(map(str, b)) for b in part),
            "opposite_witnesses": " ".join(f"{a}-{b}" for a, b in q["opposite_witnesses"]),
            "partition_count": 0,
        }
    unique[key]["partition_count"] += 1

    rows.append({
        "blocks": " | ".join(",".join(map(str, b)) for b in part),
        "q_vertex_count": q["q_vertex_count"],
        "q_edge_count": q["q_edge_count"],
        "target_q": f"{q['target_q'][0]}-{q['target_q'][1]}",
        "target_status": q["target_status"],
        "opposite_witnesses": " ".join(f"{a}-{b}" for a, b in q["opposite_witnesses"]),
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

with (outdir / "high_block_collision_quotient_partitions.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

with (outdir / "high_block_unique_quotient_graphs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(unique_rows[0].keys()))
    w.writeheader()
    w.writerows(unique_rows)

summary = {
    "source_edges": str(edges_path),
    "edge_count": len(edges),
    "target_pair": list(TARGET),
    "qv_range": [9, 10, 11],
    "partition_count": len(parts),
    "unique_quotient_graph_count": len(unique_rows),
    "status_counts": dict(status_counts),
    "size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(size_counts.items())},
    "interpretation": (
        "This extends collision-quotient enumeration to weak-collision partitions "
        "with qV=9..11. The singleton qV=12 case remains the fully distinct case."
    ),
}
(outdir / "high_block_collision_quotient_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nstatus counts:")
for k, v in status_counts.most_common():
    print(f"{k}: {v}")

print("\nsize counts:")
for k, v in sorted(size_counts.items()):
    print(f"qV={k[0]} qE={k[1]}: {v}")

print("\nunique quotient graph count:", len(unique_rows))

print("\nfirst unresolved unique quotients:")
for r in [x for x in unique_rows if x["target_status"] == "unresolved"][:30]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"parts={r['partition_count']} target={r['target_q']} "
        f"blocks={r['representative_blocks']}"
    )

print("\nWROTE:")
print(outdir / "high_block_collision_quotient_partitions.csv")
print(outdir / "high_block_unique_quotient_graphs.csv")
print(outdir / "high_block_collision_quotient_summary.json")
