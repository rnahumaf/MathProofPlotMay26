from pathlib import Path
import csv, json, subprocess, sys, collections

root = Path("n25_global_proof_search")
src = root / "subcore_021_unresolved_quotient_target_probe" / "qv6_unresolved_target_probe_summary.csv"
outdir = root / "subcore_021_qv6_quotient_exact_filters"
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

def run_json(cmd, timeout=120):
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
            data = {"parse_error": True, "raw_tail": text[-2000:]}
        return p.returncode, data, text[-2000:]
    except subprocess.TimeoutExpired:
        return "timeout", {"timeout": True}, ""

with src.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("=== SUBCORE 021 QV6 QUOTIENT EXACT FILTERS ===")
print("qV=6 quotient targets:", len(rows))

summary = []
counts = collections.Counter()

for idx, r in enumerate(rows, 1):
    edges = parse_edges(r["q_edges_plus_target"])
    edge_path = outdir / f"qv6_{idx:03d}_target_edges.csv"
    write_edges(edge_path, edges)

    triangle_rc, triangle, triangle_tail = run_json([
        sys.executable,
        str(root / "triangle_lattice_filter.py"),
        "--edges",
        str(edge_path),
        "--max-nodes",
        "200000",
    ])

    distance_rc, distance, distance_tail = run_json([
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
        "200000",
        "--precision",
        "100",
        "--tolerance",
        "1e-40",
    ], timeout=180)

    if triangle.get("eliminated"):
        status = "triangle_eliminated"
    elif distance.get("eliminated"):
        status = "distance_label_eliminated"
    elif trilat.get("status") == "eliminated":
        status = "trilateration_eliminated"
    elif trilat.get("status") == "survived":
        status = "trilateration_survived"
    else:
        status = "not_eliminated_by_current_exact_filters"

    counts[status] += 1

    out = {
        "index": idx,
        "status": status,
        "partition_count": r["partition_count"],
        "q_vertex_count": r["q_vertex_count"],
        "q_edge_count": r["q_edge_count"],
        "target_q": r["target_q"],
        "numeric_best_max_abs": r["best_max_abs"],
        "triangle_eliminated": triangle.get("eliminated"),
        "triangle_reason": triangle.get("failure_reason", ""),
        "distance_eliminated": distance.get("eliminated"),
        "distance_certificate": json.dumps(distance.get("certificate"), ensure_ascii=False),
        "trilateration_status": trilat.get("status"),
        "representative_blocks": r["representative_blocks"],
        "q_edges_plus_target": r["q_edges_plus_target"],
    }
    summary.append(out)

    print(
        f"[{idx:03d}/{len(rows)}] "
        f"qE={r['q_edge_count']} target={r['target_q']} "
        f"num_best={float(r['best_max_abs']):.3e} "
        f"status={status}",
        flush=True,
    )

with (outdir / "qv6_exact_filter_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
    w.writeheader()
    w.writerows(summary)

metadata = {
    "source": str(src),
    "tested_count": len(rows),
    "status_counts": dict(counts),
    "interpretation": (
        "Exact-filter pass over qV=6 unresolved quotient graphs after reinserting "
        "the quotient target edge. These are candidates already numerically not found."
    ),
}
(outdir / "qv6_exact_filter_metadata.json").write_text(
    json.dumps(metadata, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nstatus counts:")
for k, v in counts.most_common():
    print(f"{k}: {v}")

print("\nWROTE:")
print(outdir / "qv6_exact_filter_summary.csv")
print(outdir / "qv6_exact_filter_metadata.json")
