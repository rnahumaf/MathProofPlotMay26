from pathlib import Path
import csv, json, itertools, collections

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_removed_edge_structure_audit" / "subcore_021_without_3_12_edges.csv"
observed_path = root / "subcore_021_collision_quotients" / "collision_quotients_summary.json"
outdir = root / "subcore_021_collision_quotient_enumeration"
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

def enumerate_partitions(vertices, edge_set, min_blocks=2, max_blocks=8, max_block_size=6):
    results = []

    def rec(pos, blocks):
        if pos == len(vertices):
            if min_blocks <= len(blocks) <= max_blocks:
                results.append(canonical_partition(blocks))
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
    return sorted(set(results), key=lambda x: (len(x), x))

def partition_key_from_observed_branch(branch):
    comps = [tuple(comp) for comp in branch["components"]]
    return canonical_partition(comps)

edges = read_edges(edges_path)
edge_set = set(edges)
vertices = sorted({v for e in edges for v in e})

observed = json.loads(observed_path.read_text(encoding="utf-8"))
observed_keys = {
    name: partition_key_from_observed_branch(branch)
    for name, branch in observed.items()
}

print("=== SUBCORE 021 COLLISION QUOTIENT ENUMERATION ===")
print("vertices:", vertices)
print("edge_count:", len(edges))
print("target:", TARGET)
print("observed:")
for name, key in observed_keys.items():
    print(f"  {name}: {key}")

parts = enumerate_partitions(
    vertices,
    edge_set,
    min_blocks=2,
    max_blocks=8,
    max_block_size=6,
)

print("candidate independent-set partitions:", len(parts))

rows = []
status_counts = collections.Counter()
size_counts = collections.Counter()
observed_found = {name: False for name in observed_keys}

for part in parts:
    q = quotient_from_partition(edges, part)
    status_counts[q["target_status"]] += 1
    size_counts[(q["q_vertex_count"], q["q_edge_count"])] += 1

    observed_name = ""
    for name, key in observed_keys.items():
        if part == key:
            observed_found[name] = True
            observed_name = name

    rows.append({
        "blocks": " | ".join(",".join(map(str, b)) for b in part),
        "q_vertex_count": q["q_vertex_count"],
        "q_edge_count": q["q_edge_count"],
        "target_q": f"{q['target_q'][0]}-{q['target_q'][1]}",
        "target_status": q["target_status"],
        "opposite_witnesses": " ".join(f"{a}-{b}" for a, b in q["opposite_witnesses"]),
        "observed_branch": observed_name,
        "q_edges": " ".join(f"{a}-{b}" for a, b in q["q_edges"]),
    })

rows_sorted = sorted(
    rows,
    key=lambda r: (
        r["target_status"] != "unresolved",
        int(r["q_vertex_count"]),
        int(r["q_edge_count"]),
        r["blocks"],
    ),
)

with (outdir / "collision_quotient_partition_enumeration.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows_sorted[0].keys()))
    writer.writeheader()
    writer.writerows(rows_sorted)

summary = {
    "source_edges": str(edges_path),
    "edge_count": len(edges),
    "target_pair": list(TARGET),
    "candidate_partition_count": len(parts),
    "status_counts": dict(status_counts),
    "size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(size_counts.items())},
    "observed_found": observed_found,
    "interpretation": (
        "This is a combinatorial enumeration of collision partitions whose blocks "
        "are independent sets of the 24-edge core. Partitions with target_status "
        "'loop' or 'forced_sqrt3_by_opposite_relation' are immediately incompatible "
        "with reinserting the target edge 3-12 as a unit edge. 'unresolved' partitions "
        "need geometric filtering."
    ),
}

(outdir / "collision_quotient_partition_enumeration_summary.json").write_text(
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

print("\nfirst unresolved candidates:")
unresolved = [r for r in rows_sorted if r["target_status"] == "unresolved"]
for r in unresolved[:30]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"target={r['target_q']} blocks={r['blocks']}"
    )

print("\nWROTE:")
print(outdir / "collision_quotient_partition_enumeration.csv")
print(outdir / "collision_quotient_partition_enumeration_summary.json")
