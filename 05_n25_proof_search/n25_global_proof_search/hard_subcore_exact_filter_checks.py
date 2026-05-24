from pathlib import Path
import json, csv, subprocess, sys

root = Path("n25_global_proof_search")
details_path = root / "collision_forced_subcore_audit" / "subcore_collision_details.json"
outdir = root / "hard_subcore_exact_filter_checks"
outdir.mkdir(parents=True, exist_ok=True)

target_indices = [21, 18, 20, 3, 15]
details = json.loads(details_path.read_text(encoding="utf-8"))

targets = []
for item in details:
    if item["subcore_index"] in target_indices:
        path = outdir / f"subcore_{item['subcore_index']:03d}_edges.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["i", "j"])
            writer.writerows(item["remapped_edges"])
        targets.append((item["subcore_index"], path))

targets.sort(key=lambda x: target_indices.index(x[0]))

commands = []
for idx, path in targets:
    commands.append((
        idx,
        "triangle",
        [
            sys.executable,
            str(root / "triangle_lattice_filter.py"),
            "--edges",
            str(path),
            "--max-nodes",
            "200000",
        ],
    ))
    commands.append((
        idx,
        "distance_labels",
        [
            sys.executable,
            str(root / "distance_label_eliminator.py"),
            "--edges",
            str(path),
        ],
    ))
    commands.append((
        idx,
        "trilateration",
        [
            sys.executable,
            str(root / "trilateration_eliminator.py"),
            "--edges",
            str(path),
            "--max-states",
            "200000",
            "--precision",
            "100",
            "--tolerance",
            "1e-40",
        ],
    ))

print("=== HARD SUBCORE EXACT FILTER CHECKS ===")

summary_rows = []

for idx, name, cmd in commands:
    print(f"\n--- subcore={idx:03d} filter={name} ---", flush=True)
    print(" ".join(cmd), flush=True)

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        output = proc.stdout.strip()
        print(output[-3000:] if len(output) > 3000 else output)

        summary_rows.append({
            "subcore_index": idx,
            "filter": name,
            "returncode": proc.returncode,
            "output_tail": output[-1000:],
        })
    except subprocess.TimeoutExpired as e:
        print("TIMEOUT")
        summary_rows.append({
            "subcore_index": idx,
            "filter": name,
            "returncode": "timeout",
            "output_tail": "",
        })

with (outdir / "hard_subcore_exact_filter_checks_summary.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["subcore_index", "filter", "returncode", "output_tail"])
    writer.writeheader()
    writer.writerows(summary_rows)

print("\nWROTE:")
print(outdir / "hard_subcore_exact_filter_checks_summary.csv")
for _, path in targets:
    print(path)
