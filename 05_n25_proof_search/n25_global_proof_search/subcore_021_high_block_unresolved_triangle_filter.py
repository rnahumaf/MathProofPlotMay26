from pathlib import Path
import csv, json, subprocess, sys, time, collections

root = Path("n25_global_proof_search")
src = root / "subcore_021_high_block_collision_quotient_enumeration" / "high_block_unique_quotient_graphs.csv"
outdir = root / "subcore_021_high_block_unresolved_triangle_filter"
outdir.mkdir(parents=True, exist_ok=True)

summary_path = outdir / "high_block_unresolved_triangle_filter_summary.csv"
metadata_path = outdir / "high_block_unresolved_triangle_filter_metadata.json"

def parse_edges(s):
    edges = []
    if not s.strip():
        return edges
    for item in s.split():
        a, b = item.split("-")
        edges.append(tuple(sorted((int(a), int(b)))))
    return sorted(set(edges))

def parse_target(s):
    a, b = s.split("-")
    return tuple(sorted((int(a), int(b))))

def write_edges(path, edges):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j"])
        w.writerows(edges)

def run_triangle(edge_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "triangle_lattice_filter.py"),
            "--edges",
            str(edge_path),
            "--max-nodes",
            "200000",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    text = proc.stdout.strip()
    try:
        data = json.loads(text[text.find("{"):])
    except Exception:
        data = {"parse_error": True, "raw_tail": text[-2000:]}
    return proc.returncode, data, text[-1000:]

def load_done():
    if not summary_path.exists():
        return set(), []
    with summary_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {int(r["source_index"]) for r in rows}, rows

with src.open(newline="", encoding="utf-8") as f:
    all_rows = list(csv.DictReader(f))

targets = []
for source_index, r in enumerate(all_rows, 1):
    if r["target_status"] == "unresolved":
        qv = int(r["q_vertex_count"])
        if qv in (9, 10, 11):
            targets.append((source_index, r))

done, existing_rows = load_done()
out_rows = list(existing_rows)

print("=== SUBCORE 021 HIGH-BLOCK UNRESOLVED TRIANGLE FILTER ===")
print("source unique quotient graphs:", len(all_rows))
print("qV=9..11 unresolved targets:", len(targets))
print("already done:", len(done))

start = time.time()

for local_idx, (source_index, r) in enumerate(targets, 1):
    if source_index in done:
        continue

    q_edges = parse_edges(r["q_edges"])
    target = parse_target(r["target_q"])
    q_edges_plus_target = sorted(set(q_edges + [target]))

    edge_path = outdir / f"qv{r['q_vertex_count']}_source_{source_index:05d}_target_edges.csv"
    write_edges(edge_path, q_edges_plus_target)

    try:
        rc, tri, tail = run_triangle(edge_path)
        eliminated = bool(tri.get("eliminated"))
        failure_reason = tri.get("failure_reason", "")
        triangle_count = tri.get("triangle_count", "")
        component_count = tri.get("triangle_component_count", "")
        largest_component_vertices = tri.get("largest_component_vertices", "")
        search_nodes = tri.get("search_nodes", "")
        status = "triangle_eliminated" if eliminated else "triangle_survived"
    except subprocess.TimeoutExpired:
        rc = "timeout"
        eliminated = False
        failure_reason = "timeout"
        triangle_count = ""
        component_count = ""
        largest_component_vertices = ""
        search_nodes = ""
        tail = ""
        status = "triangle_timeout"

    row = {
        "source_index": source_index,
        "local_index": local_idx,
        "status": status,
        "q_vertex_count": r["q_vertex_count"],
        "q_edge_count": r["q_edge_count"],
        "partition_count": r["partition_count"],
        "target_q": r["target_q"],
        "triangle_eliminated": eliminated,
        "failure_reason": failure_reason,
        "triangle_count": triangle_count,
        "triangle_component_count": component_count,
        "largest_component_vertices": largest_component_vertices,
        "search_nodes": search_nodes,
        "representative_blocks": r["representative_blocks"],
        "q_edges": r["q_edges"],
        "q_edges_plus_target": " ".join(f"{a}-{b}" for a, b in q_edges_plus_target),
        "returncode": rc,
        "output_tail": tail,
    }
    out_rows.append(row)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    if local_idx <= 20 or local_idx % 100 == 0 or status != "triangle_eliminated":
        print(
            f"[{local_idx:04d}/{len(targets)}] "
            f"source={source_index} qV={r['q_vertex_count']} qE={r['q_edge_count']} "
            f"target={r['target_q']} status={status} reason={failure_reason}",
            flush=True,
        )

counts = collections.Counter(r["status"] for r in out_rows)
qv_counts = collections.Counter((r["q_vertex_count"], r["status"]) for r in out_rows)

metadata = {
    "source": str(src),
    "target_qv": [9, 10, 11],
    "target_count": len(targets),
    "completed_count": len(out_rows),
    "status_counts": dict(counts),
    "qv_status_counts": {f"qV={k[0]},{k[1]}": v for k, v in sorted(qv_counts.items())},
    "runtime_seconds": time.time() - start,
    "interpretation": (
        "Triangle-filter pass over qV=9..11 unresolved quotient graphs after "
        "reinserting the quotient target edge. Any survivors need distance-label "
        "and trilateration filters."
    ),
}

metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

print("\nstatus counts:")
for k, v in counts.most_common():
    print(f"{k}: {v}")

print("\nqV/status counts:")
for k, v in sorted(qv_counts.items()):
    print(f"qV={k[0]} {k[1]}: {v}")

print("\nWROTE:")
print(summary_path)
print(metadata_path)
