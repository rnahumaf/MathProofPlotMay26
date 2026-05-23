#!/usr/bin/env python3
"""
Stage 11: Split-prime same-norm fibers in Q(i).

This is a rigorous finite model of one key arithmetic mechanism in the proof:
many elements with the same relative norm.

In K = Q(i), rational primes p == 1 mod 4 split:

    p = (a + b i)(a - b i).

Given split primes p_1, ..., p_t, every product

    q_eps = product_j (a_j + eps_j b_j i),   eps_j in {+1,-1}

has the same norm

    N(q_eps) = product_j p_j = mu.

Therefore q_eps / sqrt(mu) is a unit vector in the plane.

We select r such vectors and form binary subset sums. If two subset sums differ
by one selected q_eps, their normalized 2D distance is exactly 1.

This is still not the full theorem, because it uses L = Q rather than a tower of
totally real fields. But it is now a literal split-prime/same-norm fiber
construction, not a generic laboratory visualization.

Default behavior:
    - saves only summary CSVs
    - does not save huge point/edge files
    - does not plot unless --plot-best is supplied

Use --save-details explicitly for large CSV outputs.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


Gaussian = tuple[int, int]


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def split_primes_1mod4(count: int) -> list[int]:
    primes = []
    n = 5
    while len(primes) < count:
        if n % 4 == 1 and is_prime(n):
            primes.append(n)
        n += 4
    return primes


def sum_two_squares_prime(p: int) -> Gaussian:
    """Return a,b > 0 with p = a^2 + b^2 for p == 1 mod 4."""
    limit = int(math.isqrt(p))
    for a in range(1, limit + 1):
        b2 = p - a * a
        b = int(math.isqrt(b2))
        if b > 0 and b * b == b2:
            return (a, b)
    raise ValueError(f"No representation found for p={p}.")


def gmul(z: Gaussian, w: Gaussian) -> Gaussian:
    a, b = z
    c, d = w
    return (a * c - b * d, a * d + b * c)


def gadd(z: Gaussian, w: Gaussian) -> Gaussian:
    return (z[0] + w[0], z[1] + w[1])


def gneg(z: Gaussian) -> Gaussian:
    return (-z[0], -z[1])


def gnorm(z: Gaussian) -> int:
    return z[0] * z[0] + z[1] * z[1]


def angle(z: Gaussian) -> float:
    t = math.atan2(z[1], z[0])
    if t < 0:
        t += 2 * math.pi
    return t


def generate_same_norm_fiber(primes: list[int]) -> tuple[list[Gaussian], int, list[Gaussian]]:
    """
    Build q_eps = product_j (a_j ± b_j i).

    Returns:
        fiber: exact Gaussian integers q
        mu: common norm
        factors: chosen (a_j,b_j) for each prime
    """
    factors = [sum_two_squares_prime(p) for p in primes]
    fiber = [(1, 0)]

    for a, b in factors:
        new = []
        for z in fiber:
            new.append(gmul(z, (a, b)))
            new.append(gmul(z, (a, -b)))
        fiber = new

    # Deduplicate exact Gaussian integers. Usually unnecessary but safe.
    fiber = sorted(set(fiber), key=angle)
    mu = 1
    for p in primes:
        mu *= p

    # Exact sanity check.
    bad = [z for z in fiber if gnorm(z) != mu]
    if bad:
        raise RuntimeError("Some generated q do not have the common norm mu.")

    return fiber, mu, factors


def select_spread_by_angle(fiber: list[Gaussian], count: int) -> list[Gaussian]:
    fiber = sorted(fiber, key=angle)
    if count >= len(fiber):
        return fiber

    angles = [angle(z) for z in fiber]
    selected = [0]

    while len(selected) < count:
        best_i = None
        best_score = -1.0

        for i, t in enumerate(angles):
            if i in selected:
                continue

            min_dist = math.inf
            for j in selected:
                diff = abs(t - angles[j])
                diff = min(diff, 2 * math.pi - diff)
                min_dist = min(min_dist, diff)

            if min_dist > best_score:
                best_score = min_dist
                best_i = i

        assert best_i is not None
        selected.append(best_i)

    return sorted([fiber[i] for i in selected], key=angle)


def near_square_grid_unit_edges(n: int) -> tuple[int, int, int]:
    rows = int(math.floor(math.sqrt(n)))
    cols = int(math.ceil(n / rows))
    occupied = {(idx // cols, idx % cols) for idx in range(n)}

    edges = 0
    for r, c in occupied:
        if (r, c + 1) in occupied:
            edges += 1
        if (r + 1, c) in occupied:
            edges += 1
    return rows, cols, edges


def build_points(selected: list[Gaussian], mu: int, radius: float | None):
    """
    Build exact subset sums of selected Gaussian integers.

    The plotted point is sum(q_j)/sqrt(mu). Exact dedup is by Gaussian sum.
    """
    r = len(selected)
    raw_total = 1 << r
    coeff_to_point_id: dict[int, int] = {}
    exact_to_point_id: dict[Gaussian, int] = {}
    point_rows = []
    collisions = 0
    raw_kept = 0

    radius_sq_scaled = None
    if radius is not None:
        # |sum/sqrt(mu)| <= radius  <=>  norm(sum) <= radius^2 * mu
        radius_sq_scaled = radius * radius * mu

    # Dynamic programming subset sums by mask.
    sums: list[Gaussian] = [(0, 0)] * raw_total
    for mask in range(1, raw_total):
        lsb = mask & -mask
        j = lsb.bit_length() - 1
        prev = mask ^ lsb
        sums[mask] = gadd(sums[prev], selected[j])

    sqrt_mu = math.sqrt(mu)

    for mask, z in enumerate(sums):
        if radius_sq_scaled is not None and gnorm(z) > radius_sq_scaled + 1e-9:
            continue

        raw_kept += 1

        if z in exact_to_point_id:
            coeff_to_point_id[mask] = exact_to_point_id[z]
            collisions += 1
            continue

        point_id = len(point_rows)
        exact_to_point_id[z] = point_id
        coeff_to_point_id[mask] = point_id

        point_rows.append(
            {
                "id": point_id,
                "mask": mask,
                "gaussian_x": z[0],
                "gaussian_y": z[1],
                "x": z[0] / sqrt_mu,
                "y": z[1] / sqrt_mu,
                "norm_scaled": gnorm(z) / mu,
            }
        )

    return point_rows, coeff_to_point_id, raw_total, raw_kept, collisions


def count_edges(point_rows, coeff_to_point_id: dict[int, int], selected_count: int, save_details: bool):
    id_to_point = {row["id"]: row for row in point_rows}
    edge_seen = set()
    loop_collisions = 0
    edge_rows = []

    for mask, source_id in coeff_to_point_id.items():
        for j in range(selected_count):
            if (mask >> j) & 1:
                continue

            target_mask = mask | (1 << j)
            target_id = coeff_to_point_id.get(target_mask)
            if target_id is None:
                continue

            if source_id == target_id:
                loop_collisions += 1
                continue

            key = (source_id, target_id) if source_id < target_id else (target_id, source_id)
            if key in edge_seen:
                continue

            edge_seen.add(key)

            if save_details:
                p = id_to_point[key[0]]
                q = id_to_point[key[1]]
                dist = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
                edge_rows.append(
                    {
                        "from_id": key[0],
                        "to_id": key[1],
                        "x1": p["x"],
                        "y1": p["y"],
                        "x2": q["x"],
                        "y2": q["y"],
                        "numeric_distance": dist,
                        "changed_generator": j,
                    }
                )

    return len(edge_seen), edge_rows, loop_collisions


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def analyze_configuration(
    prime_count: int,
    translation_count: int,
    radius: float | None,
    save_details: bool,
):
    primes = split_primes_1mod4(prime_count)
    fiber, mu, factors = generate_same_norm_fiber(primes)

    if translation_count > len(fiber):
        return None, None

    selected = select_spread_by_angle(fiber, translation_count)

    point_rows, coeff_to_point_id, raw_total, raw_kept, collisions = build_points(
        selected=selected,
        mu=mu,
        radius=radius,
    )

    edge_count, edge_rows, loop_collisions = count_edges(
        point_rows=point_rows,
        coeff_to_point_id=coeff_to_point_id,
        selected_count=translation_count,
        save_details=save_details,
    )

    n = len(point_rows)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    max_edge_error = ""
    if edge_rows:
        max_edge_error = max(abs(row["numeric_distance"] - 1.0) for row in edge_rows)

    summary = {
        "prime_count": prime_count,
        "primes": " ".join(str(p) for p in primes),
        "sum_two_square_factors": " ; ".join(f"{a}+{b}i" for a, b in factors),
        "mu": mu,
        "fiber_size": len(fiber),
        "selected_translations": translation_count,
        "radius": "none" if radius is None else radius,
        "raw_total_subset_sums": raw_total,
        "raw_kept_subset_sums": raw_kept,
        "distinct_points": n,
        "exact_point_collisions": collisions,
        "edge_loop_collisions": loop_collisions,
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else 0,
        "avg_unit_neighbors_per_point": 2 * edge_count / n if n else 0,
        "numeric_max_edge_error": max_edge_error,
    }

    data = {
        "point_rows": point_rows,
        "edge_rows": edge_rows,
        "fiber": fiber,
        "selected": selected,
        "primes": primes,
        "factors": factors,
        "mu": mu,
    }

    return summary, data


def plot_result(output_png: Path, point_rows, edge_rows, summary, max_plot_edges: int):
    try:
        import numpy as np
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
    except Exception as exc:
        print(f"Plot skipped: {exc}")
        return

    n = int(summary["distinct_points"])
    grid_rows = int(summary["grid_rows"])
    grid_cols = int(summary["grid_cols"])
    grid_edges = int(summary["grid_unit_distance_pairs"])

    xy = np.array([[row["x"], row["y"]] for row in point_rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(17, 7.6), dpi=220)

    ax = axes[0]
    plot_edges = edge_rows
    if len(plot_edges) > max_plot_edges:
        idx = np.linspace(0, len(plot_edges) - 1, max_plot_edges).astype(int)
        plot_edges = [plot_edges[int(i)] for i in idx]

    if plot_edges:
        segments = np.array([[[e["x1"], e["y1"]], [e["x2"], e["y2"]]] for e in plot_edges], dtype=float)
        ax.add_collection(LineCollection(segments, linewidths=0.18, alpha=0.10))

    ax.scatter(xy[:, 0], xy[:, 1], s=5, alpha=0.9, zorder=3)
    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(z / sqrt(mu))")
    ax.set_ylabel("Im(z / sqrt(mu))")
    ax.set_title("Split-prime same-norm fiber in Q(i)")
    ax.text(
        0.02,
        0.98,
        (
            f"split primes: {summary['prime_count']}\n"
            f"fiber size: {summary['fiber_size']}\n"
            f"distinct points: {n}\n"
            f"unit-distance pairs: {summary['unit_distance_pairs']}\n"
            f"ratio vs grid: {summary['ratio_vs_grid']:.2f}x"
        ),
        transform=ax.transAxes,
        va="top",
        bbox=dict(boxstyle="round", alpha=0.85),
        fontsize=10,
    )

    ax = axes[1]
    occupied = {(idx // grid_cols, idx % grid_cols) for idx in range(n)}
    for r, c in occupied:
        if (r, c + 1) in occupied:
            ax.plot([c, c + 1], [r, r], linewidth=0.3, alpha=0.16)
        if (r + 1, c) in occupied:
            ax.plot([c, c], [r, r + 1], linewidth=0.3, alpha=0.16)

    xs = [idx % grid_cols for idx in range(n)]
    ys = [idx // grid_cols for idx in range(n)]
    ax.scatter(xs, ys, s=5, alpha=0.85, zorder=3)

    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"Near-square grid with same n\n{grid_rows} rows x {grid_cols} columns")

    fig.suptitle(
        "Stage 11: split-prime same-norm fiber, exact finite instance\n"
        f"{summary['unit_distance_pairs']} vs {grid_edges} unit-distance pairs "
        f"({summary['ratio_vs_grid']:.2f}x grid)",
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime-counts", type=int, nargs="+", default=[4, 5, 6])
    parser.add_argument("--translation-counts", type=int, nargs="+", default=[14, 16, 18])
    parser.add_argument("--radii", type=str, nargs="+", default=["none"])
    parser.add_argument("--max-raw-points", type=int, default=300000)
    parser.add_argument("--outdir", type=Path, default=Path("stage11_split_prime_gaussian_output"))
    parser.add_argument("--save-details", action="store_true")
    parser.add_argument("--plot-best", action="store_true")
    parser.add_argument("--max-plot-edges", type=int, default=100000)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    radii: list[float | None] = []
    for item in args.radii:
        if item.lower() in {"none", "null", "nan"}:
            radii.append(None)
        else:
            radii.append(float(item))

    summaries = []
    best_summary = None
    best_data = None

    for prime_count in args.prime_counts:
        fiber_size = 1 << prime_count

        for translation_count in args.translation_counts:
            if translation_count > fiber_size:
                continue

            raw_points = 1 << translation_count
            if raw_points > args.max_raw_points:
                print(f"Skipping prime_count={prime_count}, tc={translation_count}: 2^tc={raw_points} exceeds --max-raw-points.")
                continue

            for radius in radii:
                print(f"Running: prime_count={prime_count}, tc={translation_count}, radius={radius}")

                summary, data = analyze_configuration(
                    prime_count=prime_count,
                    translation_count=translation_count,
                    radius=radius,
                    save_details=False,
                )

                if summary is None:
                    continue

                summaries.append(summary)
                print(
                    f"  n={summary['distinct_points']} edges={summary['unit_distance_pairs']} "
                    f"grid={summary['grid_unit_distance_pairs']} ratio={summary['ratio_vs_grid']:.4f} "
                    f"collisions={summary['exact_point_collisions']}"
                )

                if best_summary is None or (
                    float(summary["ratio_vs_grid"]),
                    int(summary["unit_distance_pairs"]),
                ) > (
                    float(best_summary["ratio_vs_grid"]),
                    int(best_summary["unit_distance_pairs"]),
                ):
                    best_summary = summary
                    best_data = data

    if not summaries:
        raise SystemExit("No configurations completed.")

    summaries.sort(key=lambda r: (float(r["ratio_vs_grid"]), int(r["unit_distance_pairs"])), reverse=True)

    summary_path = args.outdir / "stage11_split_prime_summary.csv"
    write_csv(summary_path, summaries, list(summaries[0].keys()))

    print()
    print("Best configuration:")
    for key, value in summaries[0].items():
        text = str(value)
        if len(text) > 200:
            text = text[:200] + "..."
        print(f"{key}: {text}")

    if args.save_details or args.plot_best:
        best = summaries[0]
        radius = None if str(best["radius"]) == "none" else float(best["radius"])

        detail_summary, detail_data = analyze_configuration(
            prime_count=int(best["prime_count"]),
            translation_count=int(best["selected_translations"]),
            radius=radius,
            save_details=True,
        )

        stem = (
            f"best_pc{detail_summary['prime_count']}"
            f"_tc{detail_summary['selected_translations']}"
            f"_R{detail_summary['radius']}"
        ).replace(".", "p")

        if args.save_details:
            points_path = args.outdir / f"{stem}_points.csv"
            edges_path = args.outdir / f"{stem}_unit_edges.csv"
            selected_path = args.outdir / f"{stem}_selected_translations.csv"

            write_csv(points_path, detail_data["point_rows"], list(detail_data["point_rows"][0].keys()))
            if detail_data["edge_rows"]:
                write_csv(edges_path, detail_data["edge_rows"], list(detail_data["edge_rows"][0].keys()))
            else:
                write_csv(edges_path, [], ["from_id", "to_id"])

            selected_rows = [
                {"id": i, "gaussian_x": z[0], "gaussian_y": z[1], "norm": gnorm(z)}
                for i, z in enumerate(detail_data["selected"])
            ]
            write_csv(selected_path, selected_rows, ["id", "gaussian_x", "gaussian_y", "norm"])

            print(f"Wrote detail file: {points_path}")
            print(f"Wrote detail file: {edges_path}")
            print(f"Wrote detail file: {selected_path}")

        if args.plot_best:
            plot_path = args.outdir / f"{stem}_comparison.png"
            plot_result(
                output_png=plot_path,
                point_rows=detail_data["point_rows"],
                edge_rows=detail_data["edge_rows"],
                summary=detail_summary,
                max_plot_edges=args.max_plot_edges,
            )
            print(f"Wrote plot: {plot_path}")

    print()
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
