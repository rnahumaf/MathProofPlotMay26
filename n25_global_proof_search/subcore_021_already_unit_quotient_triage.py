from pathlib import Path
import csv, json, collections

root = Path("n25_global_proof_search")
src = root / "subcore_021_collision_quotient_enumeration" / "collision_quotient_partition_enumeration.csv"
outdir = root / "subcore_021_already_unit_quotient_triage"
outdir.mkdir(parents=True, exist_ok=True)

def edge_signature(q_edges):
    if not q_edges.strip():
        return ""
    edges = []
    for e in q_edges.split():
        a, b = e.split("-")
        edges.append(tuple(sorted((int(a), int(b)))))
    return " ".join(f"{a}-{b}" for a, b in sorted(edges))

def block_sizes(blocks):
    sizes = []
    for block in blocks.split(" | "):
        sizes.append(len(block.split(",")))
    return sorted(sizes, reverse=True)

def nontrivial_blocks(blocks):
    out = []
    for block in blocks.split(" | "):
        vals = block.split(",")
        if len(vals) > 1:
            out.append(block)
    return out

def key_for(row):
    return (
        row["q_vertex_count"],
        row["q_edge_count"],
        row["target_q"],
        edge_signature(row["q_edges"]),
    )

with src.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

already = [r for r in rows if r["target_status"] == "already_unit_edge_in_quotient"]

dedup = {}
for r in already:
    k = key_for(r)
    if k not in dedup:
        sizes = block_sizes(r["blocks"])
        dedup[k] = {
            "q_vertex_count": r["q_vertex_count"],
            "q_edge_count": r["q_edge_count"],
            "target_q": r["target_q"],
            "q_edges": edge_signature(r["q_edges"]),
            "representative_blocks": r["blocks"],
            "nontrivial_blocks": " | ".join(nontrivial_blocks(r["blocks"])),
            "largest_collision_block": max(sizes),
            "collision_block_count": sum(1 for s in sizes if s > 1),
            "singleton_count": sum(1 for s in sizes if s == 1),
            "partition_count": 0,
        }
    dedup[k]["partition_count"] += 1

dedup_rows = sorted(
    dedup.values(),
    key=lambda r: (
        int(r["q_vertex_count"]),
        int(r["q_edge_count"]),
        -int(r["partition_count"]),
        r["target_q"],
        r["representative_blocks"],
    ),
)

size_counts = collections.Counter((r["q_vertex_count"], r["q_edge_count"]) for r in already)
target_counts = collections.Counter(r["target_q"] for r in already)
unique_size_counts = collections.Counter((r["q_vertex_count"], r["q_edge_count"]) for r in dedup_rows)
block_profile_counts = collections.Counter(
    (r["largest_collision_block"], r["collision_block_count"], r["singleton_count"])
    for r in dedup_rows
)

with (outdir / "already_unit_unique_quotient_graphs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(dedup_rows[0].keys()))
    w.writeheader()
    w.writerows(dedup_rows)

summary = {
    "already_unit_partition_count": len(already),
    "already_unit_unique_quotient_graph_count": len(dedup_rows),
    "size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(size_counts.items())},
    "unique_size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(unique_size_counts.items())},
    "target_counts": dict(target_counts.most_common()),
    "block_profile_counts": {
        f"largest={k[0]},collision_blocks={k[1]},singletons={k[2]}": v
        for k, v in block_profile_counts.most_common()
    },
    "interpretation": (
        "already_unit_edge_in_quotient branches are not contradictions after reinserting "
        "the target edge, because the target quotient pair is already a unit edge. They "
        "remain degenerate branches because every listed partition has nontrivial collision "
        "blocks. The remaining proof gap is to exclude the singleton/distinct realization "
        "case, not to eliminate these degenerate quotient branches."
    ),
}

(outdir / "already_unit_quotient_triage_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("=== SUBCORE 021 ALREADY-UNIT QUOTIENT TRIAGE ===")
print("already-unit partitions:", len(already))
print("already-unit unique quotient graphs:", len(dedup_rows))

print("\npartition size counts:")
for k, v in sorted(size_counts.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
    print(f"  qV={k[0]} qE={k[1]}: {v}")

print("\nunique quotient size counts:")
for k, v in sorted(unique_size_counts.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
    print(f"  qV={k[0]} qE={k[1]}: {v}")

print("\ntop target_q:")
for k, v in target_counts.most_common(20):
    print(f"  {k}: {v}")

print("\ncollision block profiles among unique quotients:")
for k, v in block_profile_counts.most_common(20):
    print(f"  largest={k[0]} collision_blocks={k[1]} singletons={k[2]}: {v}")

print("\nfirst 30 unique already-unit quotient graphs:")
for r in dedup_rows[:30]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"parts={r['partition_count']} target={r['target_q']} "
        f"collisions={r['nontrivial_blocks']} "
        f"blocks={r['representative_blocks']}"
    )

print("\nWROTE:")
print(outdir / "already_unit_unique_quotient_graphs.csv")
print(outdir / "already_unit_quotient_triage_summary.json")
