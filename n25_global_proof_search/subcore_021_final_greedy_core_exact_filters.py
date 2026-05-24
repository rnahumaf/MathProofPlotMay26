from pathlib import Path
import subprocess, sys, json

root = Path("n25_global_proof_search")
edges_path = root / "subcore_021_final_survivor_greedy_core" / "final_greedy_core_edges.csv"
outdir = root / "subcore_021_final_greedy_core_exact_filters"
outdir.mkdir(parents=True, exist_ok=True)

commands = [
    (
        "triangle",
        [
            sys.executable,
            str(root / "triangle_lattice_filter.py"),
            "--edges",
            str(edges_path),
            "--max-nodes",
            "500000",
        ],
    ),
    (
        "distance_labels",
        [
            sys.executable,
            str(root / "distance_label_eliminator.py"),
            "--edges",
            str(edges_path),
        ],
    ),
    (
        "trilateration",
        [
            sys.executable,
            str(root / "trilateration_eliminator.py"),
            "--edges",
            str(edges_path),
            "--max-states",
            "1000000",
            "--precision",
            "140",
            "--tolerance",
            "1e-60",
        ],
    ),
]

print("=== SUBCORE 021 FINAL GREEDY CORE EXACT FILTERS ===")
print("edges:", edges_path)

summary = []

for name, cmd in commands:
    print(f"\n--- {name} ---")
    print(" ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=360,
        )
        output = proc.stdout.strip()
        print(output[-5000:] if len(output) > 5000 else output)

        summary.append({
            "filter": name,
            "returncode": proc.returncode,
            "output_tail": output[-3000:],
        })
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        summary.append({
            "filter": name,
            "returncode": "timeout",
            "output_tail": "",
        })

(outdir / "final_greedy_core_exact_filters_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nWROTE:")
print(outdir / "final_greedy_core_exact_filters_summary.json")
