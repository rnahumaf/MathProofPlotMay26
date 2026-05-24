from pathlib import Path
import csv, json, subprocess, sys, collections

root = Path("n25_global_proof_search")
src = root / "subcore_021_high_block_unresolved_triangle_filter" / "high_block_unresolved_triangle_filter_summary.csv"
outdir = root / "subcore_021_high_block_survivor_exact_filters"
outdir.mkdir(parents=True, exist_ok=True)

def parse_edges(s):
    edges = []
    if not s.strip():
        return edges
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a), int(b)))))
    return sorted(set(edges))

def write_edges(path, edges):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j"])
        w.writerows(edges)

def run_json(cmd, timeout=240):
    try:
        p = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        text = p.stdout.strip()
        try:
            data = json.loads(text[text.find("{"):])
        except Exception:
            data = {"parse_error": True, "raw_tail": text[-3000:]}
        return p.returncode, data, text[-3000:]
    except subprocess.TimeoutExpired:
        return "timeout", {"timeout": True}, ""

with src.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

survivors = [r for r in rows if r["status"] == "triangle_survived"]

print("=== SUBCORE 021 HIGH-BLOCK SURVIVOR EXACT FILTERS ===")
print("triangle survivors:", len(survivors))

summary = []
counts = collections.Counter()

for idx, r in enumerate(survivors, 1):
    edges = parse_edges(r["q_edges_plus_target"])
    edge_path = outdir / f"survivor_{idx:03d}_source_{int(r['source_index']):05d}_edges.csv"
    write_edges(edge_path, edges)

    dist_rc, dist, dist_tail = run_json([
        sys.executable,
        str(root / "distance_label_eliminator.py"),
        "--edges",
        str(edge_path),
    ])

    trilat_rc, trilat, trilat_tail = run_json([
        sys.executable,
        str(root / "trilateration_eliminator.py"),
        "--edges",
        str(edge_path),
        "--max-states",
        "500000",
        "--precision",
        "120",
        "--tolerance",
        "1e-50",
    ], timeout=300)

    if dist.get("eliminated"):
        status = "distance_label_eliminated"
    elif trilat.get("status") == "eliminated":
        status = "trilateration_eliminated"
    elif trilat.get("status") == "survived":
        status = "trilateration_survived"
    elif trilat.get("status") == "no_trilateration_order":
        status = "no_trilateration_order"
    else:
        status = "not_eliminated_by_current_exact_filters"

    counts[status] += 1

    item = {
        "survivor_index": idx,
        "source_index": r["source_index"],
        "status": status,
        "q_vertex_count": r["q_vertex_count"],
        "q_edge_count": r["q_edge_count"],
        "partition_count": r["partition_count"],
        "target_q": r["target_q"],
        "distance_eliminated": dist.get("eliminated"),
        "distance_certificate": json.dumps(dist.get("certificate"), ensure_ascii=False),
        "distance_derived_label_count": dist.get("derived_label_count"),
        "distance_linear_derived_label_count": dist.get("linear_derived_label_count"),
        "trilateration_status": trilat.get("status"),
        "trilateration_seed_edge": json.dumps(trilat.get("seed_edge"), ensure_ascii=False),
        "representative_blocks": r["representative_blocks"],
        "q_edges_plus_target": r["q_edges_plus_target"],
        "distance_output_tail": dist_tail,
        "trilateration_output_tail": trilat_tail,
    }
    summary.append(item)

    print(
        f"[{idx:02d}/{len(survivors)}] "
        f"source={r['source_index']} "
        f"qV={r['q_vertex_count']} qE={r['q_edge_count']} "
        f"target={r['target_q']} "
        f"status={status} "
        f"dist_elim={dist.get('eliminated')} "
        f"trilat={trilat.get('status')}",
        flush=True,
    )

with (outdir / "high_block_survivor_exact_filter_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
    w.writeheader()
    w.writerows(summary)

metadata = {
    "source": str(src),
    "triangle_survivor_count": len(survivors),
    "status_counts": dict(counts),
    "interpretation": (
        "Distance-label and trilateration pass over the qV=9..11 quotient graphs "
        "that survived triangle filtering after reinserting the target edge."
    ),
}
(outdir / "high_block_survivor_exact_filter_metadata.json").write_text(
    json.dumps(metadata, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nstatus counts:")
for k, v in counts.most_common():
    print(f"{k}: {v}")

print("\nWROTE:")
print(outdir / "high_block_survivor_exact_filter_summary.csv")
print(outdir / "high_block_survivor_exact_filter_metadata.json")
