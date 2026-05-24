#!/usr/bin/env python3
"""Run UCCS restart-stat samples for square n values."""

from __future__ import annotations

from pathlib import Path

import csv
import json
from dataclasses import asdict

from uccs_interactive_runner_v3_resilient import RunParams, run_one


OUTDIR = Path("uccs_square_stat_runs")
SQUARE_SIDES = range(4, 21)

def write_summary(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, side in enumerate(SQUARE_SIDES):
        n = side * side
        params = RunParams(
            n=n,
            closure_rounds=1,
            top_candidates=180,
            restarts=500,
            steps=600,
            seed=20260523 + index * 10007,
            bounds_padding=0.35,
            output_dir=str(OUTDIR),
        )
        result = run_one(params)
        row = asdict(result)
        summaries.append(row)
        print(
            f"n={n}: UCCS best={result.best_edges}, "
            f"restart mean={result.mean_restart_edges:.1f}, "
            f"restart std={result.std_restart_edges:.1f}"
        )
        write_summary(OUTDIR / "restart_summary_results.csv", summaries)
    (OUTDIR / "README.md").write_text(
        "# UCCS Square Restart Stats\n\n"
        "Cada linha roda o UCCS uma vez para `n=m^2`. A media e o desvio padrao "
        "sao calculados sobre o melhor valor atingido por cada restart interno, "
        "nao sobre a trajetoria monotona de recordes globais.\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTDIR / 'restart_summary_results.csv'}")


if __name__ == "__main__":
    main()
