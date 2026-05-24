#!/usr/bin/env sage -python
"""
Stage 5: SageMath exact cyclotomic/CM unit-distance laboratory.

Purpose
-------
This script moves the previous Python/numpy exploration toward exact algebraic
verification.

For K = Q(zeta_m), with degree d = phi(m), we enumerate algebraic integers

    z = sum_{j=0}^{d-1} a_j zeta_m^j,

where a_j lies in {-C,...,C}.

We select points by a hidden-embedding polydisc condition:

    max_{k != 1} |sigma_k(z)| <= H,

where sigma_k(zeta_m) = exp(2*pi*i*k/m), k in (Z/mZ)^*.

We then project the surviving points to the principal embedding sigma_1(z),
i.e. to C ~= R^2.

The key upgrade is exact unit-distance verification:
a coefficient-difference vector Delta is accepted only if, in QQbar,

    alpha = sum_j Delta_j zeta_m^j
    alpha * conjugate(alpha) == 1.

Thus every saved edge is supported by an exact algebraic witness, not merely a
floating-point distance check.

This is still a finite cyclotomic/CM laboratory, not the full asymptotic
OpenAI/Sawin construction. It is designed as the bridge to the next step:
general CM fields / ideals / relative norms in Sage or PARI.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import os
from pathlib import Path
from typing import Iterable

import numpy as np

# Sage exact algebraic field.
from sage.all import QQbar, ZZ  # type: ignore


def euler_phi(n: int) -> int:
    """Euler's totient function."""
    result = n
    x = n
    p = 2
    while p * p <= x:
        if x % p == 0:
            while x % p == 0:
                x //= p
            result -= result // p
        p += 1
    if x > 1:
        result -= result // x
    return result


def units_mod_m(m: int) -> list[int]:
    """Units modulo m, i.e. embeddings of Q(zeta_m)."""
    return [k for k in range(1, m) if math.gcd(k, m) == 1]


def parse_optional_radii(items: list[str]) -> list[float | None]:
    radii: list[float | None] = []
    for item in items:
        if item.lower() in {"none", "null", "nan"}:
            radii.append(None)
        else:
            radii.append(float(item))
    return radii


def coefficient_array(degree: int, coeff_bound: int) -> np.ndarray:
    """All coefficient vectors in {-C,...,C}^degree."""
    return np.array(
        list(itertools.product(range(-coeff_bound, coeff_bound + 1), repeat=degree)),
        dtype=np.int16,
    )


def numeric_embedding_matrix(m: int, degree: int) -> tuple[list[int], np.ndarray]:
    """
    Complex embedding matrix for the power basis.

    Matrix row for k contains zeta_m^(k*j), j=0,...,degree-1.
    """
    units = units_mod_m(m)
    zeta = np.exp(2j * np.pi / m)
    matrix = np.array([[zeta ** (k * j) for j in range(degree)] for k in units])
    return units, matrix


def exact_principal_unit_check(m: int, delta: tuple[int, ...]) -> bool:
    """
    Exact check that |sum_j delta_j zeta_m^j| = 1
    in the principal complex embedding.

    Implemented inside QQbar using the chosen primitive root of unity.
    """
    zeta = QQbar.zeta(m)
    alpha = QQbar(0)
    power = QQbar(1)

    for c in delta:
        if c:
            alpha += ZZ(c) * power
        power *= zeta

    return alpha * alpha.conjugate() == 1


def enumerate_unit_deltas(
    m: int,
    degree: int,
    coeff_bound: int,
    numeric_tolerance: float,
    exact: bool,
) -> list[dict]:
    """
    Enumerate coefficient-difference vectors Delta such that
    |sum_j Delta_j zeta_m^j| = 1.

    We use a fast numeric prefilter and then, by default, confirm each candidate
    exactly in QQbar.
    """
    delta_range = range(-2 * coeff_bound, 2 * coeff_bound + 1)
    zeta = np.exp(2j * np.pi / m)
    powers = np.array([zeta ** j for j in range(degree)])

    rows: list[dict] = []

    for delta_raw in itertools.product(delta_range, repeat=degree):
        if not any(delta_raw):
            continue

        delta = tuple(int(x) for x in delta_raw)
        negative = tuple(-x for x in delta)

        # Keep one orientation only to avoid double-counting edges.
        if delta < negative:
            continue

        value = np.dot(np.array(delta, dtype=float), powers)
        length = abs(value)

        if abs(length - 1.0) > numeric_tolerance:
            continue

        if exact and not exact_principal_unit_check(m, delta):
            continue

        rows.append(
            {
                "delta": delta,
                "dx": float(value.real),
                "dy": float(value.imag),
                "numeric_length": float(length),
                "exact_verified": bool(exact),
            }
        )

    return rows


def build_filtered_points(
    m: int,
    degree: int,
    coeff_bound: int,
    hidden_radius: float,
    principal_radius: float | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build points that satisfy the hidden-embedding polydisc condition.

    Returns:
        coeffs_kept: integer coefficient vectors
        xy: projected principal coordinates, shape (n,2)
        principal_abs: |sigma_1(z)|
        hidden_max: max hidden embedding size
    """
    coeffs = coefficient_array(degree, coeff_bound)
    units, matrix = numeric_embedding_matrix(m, degree)

    principal_idx = units.index(1)
    hidden_idx = [i for i in range(len(units)) if i != principal_idx]

    images = coeffs.astype(float) @ matrix.T
    principal = images[:, principal_idx]
    hidden_max = np.max(np.abs(images[:, hidden_idx]), axis=1) if hidden_idx else np.zeros(len(coeffs))

    keep = hidden_max <= hidden_radius
    if principal_radius is not None:
        keep &= np.abs(principal) <= principal_radius

    coeffs_kept = coeffs[keep]
    principal_kept = principal[keep]
    hidden_kept = hidden_max[keep]

    xy = np.column_stack([principal_kept.real.astype(float), principal_kept.imag.astype(float)])
    principal_abs = np.abs(principal_kept).astype(float)

    return coeffs_kept, xy, principal_abs, hidden_kept


def count_edges_from_deltas(
    coeffs: np.ndarray,
    xy: np.ndarray,
    unit_deltas: list[dict],
    save_edges: bool,
) -> tuple[int, list[dict]]:
    """
    Count pairs of kept coefficient vectors separated by an exact unit delta.

    If save_edges=True, return all edge rows with numeric coordinates.
    """
    tuples = [tuple(int(x) for x in row) for row in coeffs]
    index = {t: i for i, t in enumerate(tuples)}

    edge_rows: list[dict] = []
    edge_seen: set[tuple[int, int]] = set()
    edge_count = 0

    for delta_row in unit_deltas:
        delta = tuple(int(x) for x in delta_row["delta"])

        for i, t in enumerate(tuples):
            target = tuple(t[j] + delta[j] for j in range(len(delta)))
            j = index.get(target)

            if j is None:
                continue

            key = (i, j) if i < j else (j, i)
            if key in edge_seen:
                continue

            edge_seen.add(key)
            edge_count += 1

            if save_edges:
                x1, y1 = xy[i]
                x2, y2 = xy[j]
                edge_rows.append(
                    {
                        "from_id": key[0],
                        "to_id": key[1],
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2),
                        "numeric_distance": float(math.hypot(x2 - x1, y2 - y1)),
                        "delta": delta,
                    }
                )

    return edge_count, edge_rows


def near_square_grid_unit_edges(n: int) -> tuple[int, int, int]:
    """Near-square grid with exactly n points, filled row by row."""
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


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {}
            for name in fieldnames:
                value = row.get(name, "")
                if isinstance(value, tuple):
                    value = " ".join(str(x) for x in value)
                out[name] = value
            writer.writerow(out)


def write_points_csv(
    path: Path,
    coeffs: np.ndarray,
    xy: np.ndarray,
    principal_abs: np.ndarray,
    hidden_max: np.ndarray,
) -> None:
    degree = coeffs.shape[1]
    fieldnames = ["id", "x", "y", "principal_abs", "hidden_max_abs"] + [f"a{j}" for j in range(degree)]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(len(coeffs)):
            row = {
                "id": i,
                "x": float(xy[i, 0]),
                "y": float(xy[i, 1]),
                "principal_abs": float(principal_abs[i]),
                "hidden_max_abs": float(hidden_max[i]),
            }
            for j in range(degree):
                row[f"a{j}"] = int(coeffs[i, j])
            writer.writerow(row)


def maybe_plot(
    output_png: Path,
    coeffs: np.ndarray,
    xy: np.ndarray,
    hidden_max: np.ndarray,
    edge_rows: list[dict],
    row: dict,
    max_plot_edges: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
    except Exception as exc:
        print(f"Plot skipped: matplotlib import failed: {exc}")
        return

    n = len(coeffs)
    grid_rows = int(row["grid_rows"])
    grid_cols = int(row["grid_cols"])
    grid_edges = int(row["grid_unit_distance_pairs"])
    edge_count = int(row["unit_distance_pairs"])

    fig, axes = plt.subplots(1, 2, figsize=(17, 7.6), dpi=220)

    ax = axes[0]

    plot_edges = edge_rows
    if len(plot_edges) > max_plot_edges:
        idx = np.linspace(0, len(plot_edges) - 1, max_plot_edges).astype(int)
        plot_edges = [plot_edges[int(i)] for i in idx]

    if plot_edges:
        segments = np.array(
            [
                [[e["x1"], e["y1"]], [e["x2"], e["y2"]]]
                for e in plot_edges
            ],
            dtype=float,
        )
        ax.add_collection(LineCollection(segments, linewidths=0.18, alpha=0.10))

    sc = ax.scatter(
        xy[:, 0],
        xy[:, 1],
        c=hidden_max,
        s=5,
        alpha=0.9,
        zorder=3,
    )
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("max hidden embedding size")

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(sigma_1(z))")
    ax.set_ylabel("Im(sigma_1(z))")
    ax.set_title(
        rf"$\mathbb{{Q}}(\zeta_{{{row['m']}}})$ exact unit-delta projection"
        "\n"
        rf"C={row['coeff_bound']}, hidden H={row['hidden_radius']}, principal R={row['principal_radius']}"
    )
    ax.text(
        0.02,
        0.98,
        (
            f"points: {n}\n"
            f"unit-distance pairs: {edge_count}\n"
            f"exact unit deltas: {row['unit_delta_vectors']}\n"
            f"avg. unit neighbors: {2 * edge_count / n:.2f}"
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
    ax.text(
        0.02,
        0.98,
        (
            f"points: {n}\n"
            f"unit-distance pairs: {grid_edges}\n"
            f"avg. unit neighbors: {2 * grid_edges / n:.2f}"
        ),
        transform=ax.transAxes,
        va="top",
        bbox=dict(boxstyle="round", alpha=0.85),
        fontsize=10,
    )

    fig.suptitle(
        "Stage 5: Sage exact algebraic unit witnesses + 2D projection\n"
        f"{edge_count} vs {grid_edges} unit-distance pairs ({edge_count / grid_edges:.2f}x grid)",
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def analyze_configuration(
    m: int,
    coeff_bound: int,
    hidden_radius: float,
    principal_radius: float | None,
    exact_deltas: bool,
    numeric_tolerance: float,
    save_edges: bool,
) -> tuple[dict, dict]:
    degree = euler_phi(m)

    unit_deltas = enumerate_unit_deltas(
        m=m,
        degree=degree,
        coeff_bound=coeff_bound,
        numeric_tolerance=numeric_tolerance,
        exact=exact_deltas,
    )

    coeffs, xy, principal_abs, hidden_max = build_filtered_points(
        m=m,
        degree=degree,
        coeff_bound=coeff_bound,
        hidden_radius=hidden_radius,
        principal_radius=principal_radius,
    )

    edge_count, edge_rows = count_edges_from_deltas(
        coeffs=coeffs,
        xy=xy,
        unit_deltas=unit_deltas,
        save_edges=save_edges,
    )

    n = len(coeffs)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    numeric_max_edge_error = ""
    if edge_rows:
        numeric_max_edge_error = max(abs(float(e["numeric_distance"]) - 1.0) for e in edge_rows)

    summary = {
        "m": m,
        "phi_m": degree,
        "coeff_bound": coeff_bound,
        "hidden_radius": hidden_radius,
        "principal_radius": "none" if principal_radius is None else principal_radius,
        "points": n,
        "unit_delta_vectors": len(unit_deltas),
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else "",
        "avg_unit_neighbors_per_point": 2 * edge_count / n if n else "",
        "exact_deltas": exact_deltas,
        "numeric_max_edge_error": numeric_max_edge_error,
    }

    data = {
        "coeffs": coeffs,
        "xy": xy,
        "principal_abs": principal_abs,
        "hidden_max": hidden_max,
        "unit_deltas": unit_deltas,
        "edge_rows": edge_rows,
    }

    return summary, data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", type=int, nargs="+", default=[24])
    parser.add_argument("--coeff-bound", type=int, default=1)
    parser.add_argument("--hidden-radii", type=float, nargs="+", default=[3.0, 3.5, 4.0, 4.5, 5.0])
    parser.add_argument("--principal-radii", type=str, nargs="+", default=["none"])
    parser.add_argument("--min-points", type=int, default=100)
    parser.add_argument("--max-points", type=int, default=100000)
    parser.add_argument("--max-delta-box", type=int, default=2_000_000)
    parser.add_argument("--numeric-tolerance", type=float, default=1e-8)
    parser.add_argument("--no-exact-deltas", action="store_true")
    parser.add_argument("--outdir", type=Path, default=Path("stage5_sage_exact_output"))
    parser.add_argument("--max-plot-edges", type=int, default=60000)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    exact_deltas = not args.no_exact_deltas
    principal_radii = parse_optional_radii(args.principal_radii)

    all_summaries: list[dict] = []
    best_summary: dict | None = None
    best_data: dict | None = None

    for m in args.m_values:
        degree = euler_phi(m)
        delta_box = (4 * args.coeff_bound + 1) ** degree

        if delta_box > args.max_delta_box:
            print(
                f"Skipping m={m}: delta box {delta_box} exceeds --max-delta-box={args.max_delta_box}."
            )
            continue

        for hidden_radius in args.hidden_radii:
            for principal_radius in principal_radii:
                summary, data = analyze_configuration(
                    m=m,
                    coeff_bound=args.coeff_bound,
                    hidden_radius=hidden_radius,
                    principal_radius=principal_radius,
                    exact_deltas=exact_deltas,
                    numeric_tolerance=args.numeric_tolerance,
                    save_edges=False,
                )

                n = int(summary["points"])
                if n < args.min_points or n > args.max_points:
                    continue

                all_summaries.append(summary)

                if best_summary is None:
                    best_summary = summary
                    best_data = data
                else:
                    current_ratio = float(summary["ratio_vs_grid"])
                    best_ratio = float(best_summary["ratio_vs_grid"])
                    if (current_ratio, int(summary["unit_distance_pairs"])) > (
                        best_ratio,
                        int(best_summary["unit_distance_pairs"]),
                    ):
                        best_summary = summary
                        best_data = data

    if not all_summaries or best_summary is None:
        raise SystemExit("No configuration survived the selected constraints.")

    summary_fields = [
        "m",
        "phi_m",
        "coeff_bound",
        "hidden_radius",
        "principal_radius",
        "points",
        "unit_delta_vectors",
        "unit_distance_pairs",
        "grid_rows",
        "grid_cols",
        "grid_unit_distance_pairs",
        "ratio_vs_grid",
        "avg_unit_neighbors_per_point",
        "exact_deltas",
        "numeric_max_edge_error",
    ]

    all_summaries.sort(
        key=lambda r: (float(r["ratio_vs_grid"]), int(r["unit_distance_pairs"])),
        reverse=True,
    )

    summary_path = args.outdir / "stage5_summary.csv"
    write_csv(summary_path, all_summaries, summary_fields)

    # Re-run best with edge saving for export and plot.
    best_principal_radius = None
    if best_summary["principal_radius"] != "none":
        best_principal_radius = float(best_summary["principal_radius"])

    best_summary, best_data = analyze_configuration(
        m=int(best_summary["m"]),
        coeff_bound=int(best_summary["coeff_bound"]),
        hidden_radius=float(best_summary["hidden_radius"]),
        principal_radius=best_principal_radius,
        exact_deltas=exact_deltas,
        numeric_tolerance=args.numeric_tolerance,
        save_edges=True,
    )

    stem = (
        f"best_m{best_summary['m']}"
        f"_C{best_summary['coeff_bound']}"
        f"_H{best_summary['hidden_radius']}"
        f"_R{best_summary['principal_radius']}"
    ).replace(".", "p")

    points_path = args.outdir / f"{stem}_points.csv"
    deltas_path = args.outdir / f"{stem}_exact_unit_deltas.csv"
    edges_path = args.outdir / f"{stem}_unit_edges.csv"
    plot_path = args.outdir / f"{stem}_comparison.png"

    write_points_csv(
        points_path,
        best_data["coeffs"],
        best_data["xy"],
        best_data["principal_abs"],
        best_data["hidden_max"],
    )

    write_csv(
        deltas_path,
        best_data["unit_deltas"],
        ["delta", "dx", "dy", "numeric_length", "exact_verified"],
    )

    write_csv(
        edges_path,
        best_data["edge_rows"],
        ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "delta"],
    )

    if not args.no_plot:
        maybe_plot(
            output_png=plot_path,
            coeffs=best_data["coeffs"],
            xy=best_data["xy"],
            hidden_max=best_data["hidden_max"],
            edge_rows=best_data["edge_rows"],
            row=best_summary,
            max_plot_edges=args.max_plot_edges,
        )

    print("Top configurations:")
    for row in all_summaries[:20]:
        print(
            f"m={row['m']} phi={row['phi_m']} C={row['coeff_bound']} "
            f"H={row['hidden_radius']} R={row['principal_radius']} "
            f"n={row['points']} unit_pairs={row['unit_distance_pairs']} "
            f"grid={row['grid_unit_distance_pairs']} ratio={float(row['ratio_vs_grid']):.6f} "
            f"unit_deltas={row['unit_delta_vectors']}"
        )

    print()
    print("Best configuration re-exported with full edge list:")
    print(
        f"m={best_summary['m']} phi={best_summary['phi_m']} "
        f"C={best_summary['coeff_bound']} H={best_summary['hidden_radius']} "
        f"R={best_summary['principal_radius']}"
    )
    print(f"points={best_summary['points']}")
    print(f"unit_distance_pairs={best_summary['unit_distance_pairs']}")
    print(f"grid_unit_distance_pairs={best_summary['grid_unit_distance_pairs']}")
    print(f"ratio_vs_grid={float(best_summary['ratio_vs_grid']):.6f}")
    print(f"exact_deltas={best_summary['exact_deltas']}")
    print(f"numeric_max_edge_error={best_summary['numeric_max_edge_error']}")
    print()
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {points_path}")
    print(f"Wrote: {deltas_path}")
    print(f"Wrote: {edges_path}")
    if not args.no_plot:
        print(f"Wrote: {plot_path}")


if __name__ == "__main__":
    main()
