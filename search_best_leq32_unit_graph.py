#!/usr/bin/env python3
"""
Search for dense small unit-distance graphs in a controlled CM toy family.

This is an exercise, not a proof of the global optimum for all planar point
sets.  It searches projected Boolean boxes

    P(epsilon) = sum_j (epsilon_j - 1/2) zeta_m^a_j,
    epsilon_j in {0, 1}.

For k selected exponents there are n = 2^k points.  A one-bit change always
gives a unit edge, and some exponent choices create extra unit edges.

Because rotating all exponents gives the same graph up to rotation, the search
fixes exponent 0 as selected and enumerates the remaining k-1 exponents.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUTDIR = Path("best_leq32_search")
TOLERANCE = 1e-10


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def unit_vectors(m: int, exponents: tuple[int, ...]) -> np.ndarray:
    angles = np.array(exponents, dtype=float) * 2.0 * math.pi / m
    return np.column_stack([np.cos(angles), np.sin(angles)])


def points_for(m: int, exponents: tuple[int, ...]) -> np.ndarray:
    vectors = unit_vectors(m, exponents)
    k = len(exponents)
    rows = []
    for mask in range(1 << k):
        bits = np.array([(mask >> j) & 1 for j in range(k)], dtype=float)
        rows.append((bits - 0.5) @ vectors)
    return np.array(rows, dtype=float)


def bit_difference_matrix(k: int) -> np.ndarray:
    bits = []
    for mask in range(1 << k):
        bits.append([(mask >> j) & 1 for j in range(k)])
    bit_array = np.array(bits, dtype=float)
    diffs = []
    for i in range(1 << k):
        for j in range(i + 1, 1 << k):
            diffs.append(bit_array[j] - bit_array[i])
    return np.array(diffs, dtype=float)


def unit_edge_rows(points: np.ndarray) -> list[dict]:
    rows: list[dict] = []
    for i in range(len(points)):
        deltas = points[i + 1 :] - points[i]
        distances = np.sqrt((deltas * deltas).sum(axis=1))
        for offset, distance in enumerate(distances, start=1):
            if abs(float(distance) - 1.0) <= TOLERANCE:
                j = i + offset
                rows.append(
                    {
                        "from_id": i,
                        "to_id": j,
                        "distance": float(distance),
                        "x1": float(points[i, 0]),
                        "y1": float(points[i, 1]),
                        "x2": float(points[j, 0]),
                        "y2": float(points[j, 1]),
                    }
                )
    return rows


def count_unit_edges(points: np.ndarray) -> int:
    count = 0
    for i in range(len(points)):
        deltas = points[i + 1 :] - points[i]
        distances = np.sqrt((deltas * deltas).sum(axis=1))
        count += int(np.count_nonzero(np.abs(distances - 1.0) <= TOLERANCE))
    return count


def count_unit_edges_from_diffs(bit_diffs: np.ndarray, vectors: np.ndarray) -> int:
    deltas = bit_diffs @ vectors
    squared = (deltas * deltas).sum(axis=1)
    return int(np.count_nonzero(np.abs(squared - 1.0) <= 4 * TOLERANCE))


def has_distinct_points(points: np.ndarray) -> bool:
    rounded = {tuple(row) for row in np.round(points, 12)}
    return len(rounded) == len(points)


def search(m_values: list[int], k_values: list[int]) -> list[dict]:
    results: list[dict] = []
    for k in k_values:
        bit_diffs = bit_difference_matrix(k)
        for m in m_values:
            if k > m:
                continue
            checked = 0
            best: dict | None = None
            for rest in itertools.combinations(range(1, m), k - 1):
                exponents = (0, *rest)
                checked += 1
                vectors = unit_vectors(m, exponents)
                edges = count_unit_edges_from_diffs(bit_diffs, vectors)
                constructive = k * (1 << (k - 1))
                extra = edges - constructive
                if best is None or (edges, extra, -max(rest)) > (
                    best["unit_edges"],
                    best["extra_edges"],
                    -max(best["exponents"]),
                ):
                    points = points_for(m, exponents)
                    if not has_distinct_points(points):
                        continue
                    best = {
                        "m": m,
                        "k": k,
                        "points": 1 << k,
                        "exponents": exponents,
                        "unit_edges": edges,
                        "constructive_edges": constructive,
                        "extra_edges": extra,
                        "checked_combinations": checked,
                    }
            if best is not None:
                results.append(best)
                print(
                    f"m={m:2d} k={k}: n={best['points']:2d}, "
                    f"edges={best['unit_edges']:3d}, exponents={best['exponents']}"
                )
    return results


def project_mapper(points: np.ndarray, box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    min_x, min_y = points.min(axis=0)
    max_x, max_y = points.max(axis=0)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    min_x -= 0.12 * dx
    max_x += 0.12 * dx
    min_y -= 0.12 * dy
    max_y += 0.12 * dy
    scale = min((x1 - x0) / (max_x - min_x), (y1 - y0) / (max_y - min_y))
    cx_data = (min_x + max_x) / 2
    cy_data = (min_y + max_y) / 2
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    def project(x: float, y: float) -> tuple[int, int]:
        return int(round(cx + (x - cx_data) * scale)), int(round(cy - (y - cy_data) * scale))

    return project


def plot_best(best: dict, path: Path) -> None:
    points = points_for(best["m"], tuple(best["exponents"]))
    edges = unit_edge_rows(points)
    image = Image.new("RGBA", (1400, 1000), "#ffffff")
    draw = ImageDraw.Draw(image)
    title = "Melhor encontrado na familia CM booleana com n <= 32"
    subtitle = (
        f"K=Q(zeta_{best['m']}), n={best['points']}, "
        f"arestas unitarias={best['unit_edges']}, expoentes={best['exponents']}"
    )
    draw.text((60, 44), title, fill="#111827", font=font(34, True))
    draw.text((60, 92), subtitle, fill="#475569", font=font(22))

    project = project_mapper(points, (90, 150, 1310, 850))
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    edge_draw = ImageDraw.Draw(overlay)
    for edge in edges:
        edge_draw.line(
            [project(edge["x1"], edge["y1"]), project(edge["x2"], edge["y2"])],
            fill=(37, 99, 235, 58),
            width=3,
        )
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)
    for idx, (x, y) in enumerate(points):
        px, py = project(float(x), float(y))
        draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill="#111827", outline="#ffffff", width=2)
        if best["points"] <= 32:
            draw.text((px + 10, py - 10), str(idx), fill="#475569", font=font(13))

    note = (
        "Resultado experimental dentro desta familia. Nao e uma prova de otimalidade global\n"
        "para todos os conjuntos planos com ate 32 pontos."
    )
    draw.multiline_text((60, 900), note, fill="#64748b", font=font(20), spacing=6)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, quality=95)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", type=int, nargs="+", default=[12, 16, 18, 20, 24, 30])
    parser.add_argument("--k-values", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--outdir", type=Path, default=OUTDIR)
    args = parser.parse_args()

    results = search(args.m_values, args.k_values)
    if not results:
        raise SystemExit("No valid configurations found.")

    rows = []
    for result in results:
        rows.append(
            {
                **result,
                "exponents": " ".join(str(x) for x in result["exponents"]),
                "edges_per_point": result["unit_edges"] / result["points"],
            }
        )
    best = max(results, key=lambda row: (row["unit_edges"], row["points"]))

    args.outdir.mkdir(parents=True, exist_ok=True)
    fields = [
        "m",
        "k",
        "points",
        "exponents",
        "unit_edges",
        "constructive_edges",
        "extra_edges",
        "edges_per_point",
        "checked_combinations",
    ]
    write_csv(args.outdir / "search_summary.csv", rows, fields)

    best_points = points_for(best["m"], tuple(best["exponents"]))
    best_edges = unit_edge_rows(best_points)
    point_rows = [
        {"id": i, "x": float(point[0]), "y": float(point[1])} for i, point in enumerate(best_points)
    ]
    write_csv(args.outdir / "best_points.csv", point_rows, ["id", "x", "y"])
    write_csv(args.outdir / "best_unit_edges.csv", best_edges, ["from_id", "to_id", "distance", "x1", "y1", "x2", "y2"])
    plot_best(best, args.outdir / "best_leq32_cm_boolean.png")

    print(
        f"Best: m={best['m']}, k={best['k']}, n={best['points']}, "
        f"edges={best['unit_edges']}, exponents={best['exponents']}"
    )
    print(f"Wrote: {args.outdir / 'best_leq32_cm_boolean.png'}")


if __name__ == "__main__":
    main()
