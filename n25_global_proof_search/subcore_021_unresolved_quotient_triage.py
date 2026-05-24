from pathlib import Path
import csv, json, collections

root = Path("n25_global_proof_search")
csv_path = root / "subcore_021_collision_quotient_enumeration" / "collision_quotient_partition_enumeration.csv"
outdir = root / "subcore_021_unresolved_quotient_triage"
outdir.mkdir(parents=True, exist_ok=True)

with csv_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def edge_signature(q_edges):
    if not q_edges.strip():
        return ""
    parts = []
    for e in q_edges.split():
        a, b = e.split("-")
        parts.append(tuple(sorted((int(a), int(b)))))
    return " ".join(f"{a}-{b}" for a, b in sorted(parts))

def key_for(row):
    return (
        row["target_status"],
        row["q_vertex_count"],
        row["q_edge_count"],
        row["target_q"],
        edge_signature(row["q_edges"]),
    )

status_counts = collections.Counter(r["target_status"] for r in rows)
unresolved = [r for r in rows if r["target_status"] == "unresolved"]
already = [r for r in rows if r["target_status"] == "already_unit_edge_in_quotient"]

unresolved_size_counts = collections.Counter((r["q_vertex_count"], r["q_edge_count"]) for r in unresolved)
already_size_counts = collections.Counter((r["q_vertex_count"], r["q_edge_count"]) for r in already)

unresolved_target_counts = collections.Counter(r["target_q"] for r in unresolved)
already_target_counts = collections.Counter(r["target_q"] for r in already)

dedup = {}
for r in unresolved:
    k = key_for(r)
    if k not in dedup:
        dedup[k] = {
            "target_status": r["target_status"],
            "q_vertex_count": r["q_vertex_count"],
            "q_edge_count": r["q_edge_count"],
            "target_q": r["target_q"],
            "q_edges": edge_signature(r["q_edges"]),
            "representative_blocks": r["blocks"],
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

with (outdir / "unresolved_unique_quotient_graphs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(dedup_rows[0].keys()))
    w.writeheader()
    w.writerows(dedup_rows)

summary = {
    "total_rows": len(rows),
    "status_counts": dict(status_counts),
    "unresolved_count": len(unresolved),
    "already_unit_count": len(already),
    "unresolved_unique_quotient_graph_count": len(dedup_rows),
    "unresolved_size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(unresolved_size_counts.items())},
    "already_unit_size_counts": {f"qV={k[0]},qE={k[1]}": v for k, v in sorted(already_size_counts.items())},
    "top_unresolved_target_q": unresolved_target_counts.most_common(30),
    "top_already_target_q": already_target_counts.most_common(30),
}

(outdir / "unresolved_quotient_triage_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("=== SUBCORE 021 UNRESOLVED QUOTIENT TRIAGE ===")
print("total rows:", len(rows))
print("status counts:")
for k, v in status_counts.most_common():
    print(f"  {k}: {v}")

print("\nunresolved:", len(unresolved))
print("unresolved unique quotient graphs:", len(dedup_rows))

print("\nunresolved size counts:")
for k, v in sorted(unresolved_size_counts.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
    print(f"  qV={k[0]} qE={k[1]}: {v}")

print("\nalready-unit size counts:")
for k, v in sorted(already_size_counts.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
    print(f"  qV={k[0]} qE={k[1]}: {v}")

print("\ntop unresolved target_q:")
for k, v in unresolved_target_counts.most_common(20):
    print(f"  {k}: {v}")

print("\nfirst 30 unique unresolved quotient graphs:")
for r in dedup_rows[:30]:
    print(
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"parts={r['partition_count']} target={r['target_q']} "
        f"blocks={r['representative_blocks']}"
    )

print("\nWROTE:")
print(outdir / "unresolved_unique_quotient_graphs.csv")
print(outdir / "unresolved_quotient_triage_summary.json")
