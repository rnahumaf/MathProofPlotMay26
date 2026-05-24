#!/usr/bin/env sage -python
"""
Stage 6: General CM field K = L(i), exact norm-one translations.

This is the next step after the exact cyclotomic experiment.

Instead of hard-coding K = Q(zeta_m), this script accepts a totally real base
field L = Q(a) from a polynomial and constructs the CM field

    K = L(i).

The relative conjugation c fixes L and sends i -> -i. We enumerate a finite
piece of the fractional lattice

    (1/D) * O_L + (1/D) * O_L * i

using the power basis of L.

We then:
    1. enumerate candidate translations u in that lattice;
    2. keep only exact norm-one translations:
           u * c(u) == 1;
    3. enumerate lattice points x in a product of discs in the Minkowski
       embeddings;
    4. count pairs x, x+u that remain in the window;
    5. project the points to the first complex coordinate and plot them in R^2.

This implements the geometric mechanism of the theorem in a directly runnable
finite model:

    norm-one translations in K = L(i)
    -> product-of-discs window in C^[L:Q]
    -> projection to one complex coordinate.

It is not yet the full Golod-Shafarevich / ideal-class-fiber construction.
The next stage will construct many norm-one u's from split prime ideals and
class group fibers, as in the proof.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
from pathlib import Path

import numpy as np

from sage.all import PolynomialRing, QQ, CC, NumberField, sage_eval  # type: ignore


def parse_poly(poly_text: str):
    """
    Parse a polynomial in x over QQ.

    Works in plain `python` inside a Sage environment and in `sage -python`.
    `sage_eval` handles Sage-style expressions such as x^2-2.
    """
    R = PolynomialRing(QQ, "x")
    x = R.gen()
    return R(sage_eval(poly_text, locals={"x": x}))


def parse_float_or_none(value: str) -> float | None:
    if value.lower() in {"none", "null", "nan"}:
        return None
    return float(value)


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


def coefficient_tuples(dim: int, bound: int):
    """All integer tuples in [-bound,bound]^dim."""
    return itertools.product(range(-bound, bound + 1), repeat=dim)


def tuple_to_element(tup: tuple[int, ...], L_basis, iK, D):
    """
    Convert a 2f-dimensional integer tuple to an element of K = L(i).

    tup = (real_coeffs..., imag_coeffs...)
    element = (sum real_coeffs_j*basis_j + i*sum imag_coeffs_j*basis_j)/D
    """
    f = len(L_basis)
    real_coeffs = tup[:f]
    imag_coeffs = tup[f:]

    real_part = sum(real_coeffs[j] * L_basis[j] for j in range(f))
    imag_part = sum(imag_coeffs[j] * L_basis[j] for j in range(f))

    return (real_part + imag_part * iK) / D


def element_parts(z, L, iK):
    """
    Return z = real_part + imag_part*iK as two elements of L.

    For K = L[i] / (i^2 + 1), Sage represents elements as polynomials in iK
    over L. The list should have length <= 2.
    """
    coeffs = z.list()
    zero = L(0)

    if len(coeffs) == 0:
        return zero, zero
    if len(coeffs) == 1:
        return coeffs[0], zero
    return coeffs[0], coeffs[1]


def cm_conjugate(z, L, iK):
    """CM conjugation over L: i -> -i."""
    real_part, imag_part = element_parts(z, L, iK)
    return real_part - imag_part * iK


def embedding_values(z, L, L_embeddings, iK):
    """
    Evaluate z under one complex extension of every real embedding of L.

    If z = a + b*i, and tau: L -> R, then sigma(z) = tau(a) + i tau(b).
    """
    real_part, imag_part = element_parts(z, L, iK)
    values = []
    for emb in L_embeddings:
        a = complex(emb(real_part))
        b = complex(emb(imag_part))
        # emb(real_part), emb(imag_part) are real up to numerical noise.
        values.append(complex(a.real, b.real))
    return values


def tuple_key(tup: tuple[int, ...]) -> str:
    return " ".join(str(int(x)) for x in tup)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {}
            for k in fieldnames:
                value = row.get(k, "")
                if isinstance(value, tuple):
                    value = tuple_key(value)
                out[k] = value
            writer.writerow(out)


def enumerate_norm_one_translations(
    L,
    L_basis,
    iK,
    translation_bound: int,
    D: int,
    max_hidden_abs: float | None,
    principal_abs_limit: float | None,
    verbose: bool,
):
    """
    Enumerate exact norm-one translations in the finite coefficient box.

    Exact condition:
        u * c(u) == 1.
    """
    f = len(L_basis)
    dim = 2 * f
    L_embeddings = L.embeddings(CC)

    translations = []

    for idx, tup in enumerate(coefficient_tuples(dim, translation_bound)):
        if not any(tup):
            continue

        u = tuple_to_element(tup, L_basis, iK, D)
        if u * cm_conjugate(u, L, iK) != 1:
            continue

        values = embedding_values(u, L, L_embeddings, iK)
        abs_values = [abs(v) for v in values]
        principal_abs = abs_values[0]
        hidden_max = max(abs_values[1:]) if len(abs_values) > 1 else 0.0

        if max_hidden_abs is not None and hidden_max > max_hidden_abs:
            continue
        if principal_abs_limit is not None and principal_abs > principal_abs_limit:
            continue

        translations.append(
            {
                "tuple": tup,
                "principal_dx": float(values[0].real),
                "principal_dy": float(values[0].imag),
                "principal_abs": float(principal_abs),
                "hidden_max_abs": float(hidden_max),
            }
        )

    if verbose:
        print(f"Exact norm-one translations found: {len(translations)}")

    return translations


def enumerate_window_points(
    L,
    L_basis,
    iK,
    point_bound: int,
    D: int,
    radius: float,
    principal_radius: float | None,
    verbose: bool,
):
    """
    Enumerate lattice points in the product of discs.

    Keep x if:
        max_r |sigma_r(x)| <= radius
    and optionally:
        |sigma_1(x)| <= principal_radius.
    """
    f = len(L_basis)
    dim = 2 * f
    L_embeddings = L.embeddings(CC)

    point_rows = []
    tuple_to_id = {}

    for tup in coefficient_tuples(dim, point_bound):
        z = tuple_to_element(tup, L_basis, iK, D)
        values = embedding_values(z, L, L_embeddings, iK)
        abs_values = [abs(v) for v in values]

        max_abs = max(abs_values)
        principal_abs = abs_values[0]

        if max_abs > radius:
            continue
        if principal_radius is not None and principal_abs > principal_radius:
            continue

        pid = len(point_rows)
        tuple_to_id[tup] = pid

        row = {
            "id": pid,
            "tuple": tup,
            "x": float(values[0].real),
            "y": float(values[0].imag),
            "principal_abs": float(principal_abs),
            "max_embedding_abs": float(max_abs),
        }

        for j, c in enumerate(tup):
            row[f"c{j}"] = int(c)

        point_rows.append(row)

    if verbose:
        print(f"Window points found: {len(point_rows)}")

    return point_rows, tuple_to_id


def count_edges(point_rows, tuple_to_id, translations, save_edges: bool):
    """
    Count pairs x, x+u in the same window, using coefficient tuples.

    Since both points and translations live in the same denominator lattice
    (1/D)*basis, tuple addition represents x+u.
    """
    id_to_point = {row["id"]: row for row in point_rows}
    point_tuples = list(tuple_to_id.keys())

    edge_seen = set()
    edge_rows = []

    for tr in translations:
        delta = tr["tuple"]

        for tup in point_tuples:
            target = tuple(tup[j] + delta[j] for j in range(len(tup)))
            target_id = tuple_to_id.get(target)
            if target_id is None:
                continue

            source_id = tuple_to_id[tup]
            if source_id == target_id:
                continue

            key = (source_id, target_id) if source_id < target_id else (target_id, source_id)
            if key in edge_seen:
                continue

            edge_seen.add(key)

            if save_edges:
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
                        "translation_tuple": delta,
                    }
                )

    return len(edge_seen), edge_rows


def plot_result(output_png, point_rows, edge_rows, summary, max_plot_edges):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
    except Exception as exc:
        print(f"Plot skipped: {exc}")
        return

    n = int(summary["points"])
    grid_rows = int(summary["grid_rows"])
    grid_cols = int(summary["grid_cols"])
    grid_edges = int(summary["grid_unit_distance_pairs"])

    xy = np.array([[row["x"], row["y"]] for row in point_rows], dtype=float)
    color = np.array([row["max_embedding_abs"] for row in point_rows], dtype=float)

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

    sc = ax.scatter(xy[:, 0], xy[:, 1], c=color, s=5, alpha=0.9, zorder=3)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("max embedding size")

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(sigma_1(z))")
    ax.set_ylabel("Im(sigma_1(z))")
    ax.set_title("General CM field K = L(i)\nexact norm-one translations")
    ax.text(
        0.02,
        0.98,
        (
            f"points: {n}\n"
            f"unit-distance pairs: {summary['unit_distance_pairs']}\n"
            f"norm-one translations: {summary['norm_one_translations']}\n"
            f"avg. unit neighbors: {summary['avg_unit_neighbors_per_point']:.2f}"
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
        "Stage 6: general K=L(i), exact relative norm-one translations\n"
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
    parser.add_argument("--L-poly", type=str, default="x^2-2", help="Totally real polynomial over QQ in variable x.")
    parser.add_argument("--point-bound", type=int, default=4)
    parser.add_argument("--translation-bound", type=int, default=4)
    parser.add_argument("--denominator", type=int, default=1)
    parser.add_argument("--radius", type=float, default=5.0, help="Product-of-discs radius for point window.")
    parser.add_argument("--principal-radius", type=str, default="none")
    parser.add_argument("--translation-hidden-max", type=str, default="none")
    parser.add_argument("--translation-principal-abs", type=str, default="none")
    parser.add_argument("--outdir", type=Path, default=Path("stage6_general_cm_output"))
    parser.add_argument("--max-plot-edges", type=int, default=60000)
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    poly = parse_poly(args.L_poly)
    L = NumberField(poly, "a")
    a = L.gen()

    # K = L(i) as a relative extension.
    R = PolynomialRing(L, "y")
    y = R.gen()
    K = L.extension(y**2 + 1, "i")
    iK = K.gen()

    # Use the power basis of L for this finite lab.
    f = L.degree()
    L_basis = [L(a**j) for j in range(f)]

    principal_radius = parse_float_or_none(args.principal_radius)
    translation_hidden_max = parse_float_or_none(args.translation_hidden_max)
    translation_principal_abs = parse_float_or_none(args.translation_principal_abs)

    print("Stage 6 configuration")
    print(f"L polynomial: {poly}")
    print(f"[L:Q] = {f}")
    print(f"K = L(i), [K:Q] = {2*f}")
    print(f"point_bound = {args.point_bound}")
    print(f"translation_bound = {args.translation_bound}")
    print(f"denominator D = {args.denominator}")
    print(f"radius R = {args.radius}")
    print(f"principal_radius = {principal_radius}")
    print()

    translations = enumerate_norm_one_translations(
        L=L,
        L_basis=L_basis,
        iK=iK,
        translation_bound=args.translation_bound,
        D=args.denominator,
        max_hidden_abs=translation_hidden_max,
        principal_abs_limit=translation_principal_abs,
        verbose=True,
    )

    point_rows, tuple_to_id = enumerate_window_points(
        L=L,
        L_basis=L_basis,
        iK=iK,
        point_bound=args.point_bound,
        D=args.denominator,
        radius=args.radius,
        principal_radius=principal_radius,
        verbose=True,
    )

    edge_count, edge_rows = count_edges(
        point_rows=point_rows,
        tuple_to_id=tuple_to_id,
        translations=translations,
        save_edges=True,
    )

    n = len(point_rows)
    if n == 0:
        raise SystemExit("No points survived the window. Increase --radius or --point-bound.")

    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    max_edge_error = ""
    if edge_rows:
        max_edge_error = max(abs(float(e["numeric_distance"]) - 1.0) for e in edge_rows)

    summary = {
        "L_poly": str(poly),
        "L_degree": f,
        "K_degree": 2 * f,
        "point_bound": args.point_bound,
        "translation_bound": args.translation_bound,
        "denominator": args.denominator,
        "radius": args.radius,
        "principal_radius": "none" if principal_radius is None else principal_radius,
        "points": n,
        "norm_one_translations": len(translations),
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else 0,
        "avg_unit_neighbors_per_point": 2 * edge_count / n,
        "numeric_max_edge_error": max_edge_error,
    }

    stem = (
        f"stage6_Ldeg{f}"
        f"_pb{args.point_bound}"
        f"_tb{args.translation_bound}"
        f"_D{args.denominator}"
        f"_R{args.radius}"
    ).replace(".", "p")

    summary_path = args.outdir / f"{stem}_summary.csv"
    points_path = args.outdir / f"{stem}_points.csv"
    translations_path = args.outdir / f"{stem}_norm_one_translations.csv"
    edges_path = args.outdir / f"{stem}_unit_edges.csv"
    plot_path = args.outdir / f"{stem}_comparison.png"

    write_csv(summary_path, [summary], list(summary.keys()))

    point_fields = list(point_rows[0].keys()) if point_rows else ["id", "tuple", "x", "y"]
    write_csv(points_path, point_rows, point_fields)

    translation_fields = ["tuple", "principal_dx", "principal_dy", "principal_abs", "hidden_max_abs"]
    write_csv(translations_path, translations, translation_fields)

    edge_fields = ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "translation_tuple"]
    write_csv(edges_path, edge_rows, edge_fields)

    if not args.no_plot:
        plot_result(
            output_png=plot_path,
            point_rows=point_rows,
            edge_rows=edge_rows,
            summary=summary,
            max_plot_edges=args.max_plot_edges,
        )

    print("Summary")
    for k, v in summary.items():
        print(f"{k}: {v}")

    print()
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {points_path}")
    print(f"Wrote: {translations_path}")
    print(f"Wrote: {edges_path}")
    if not args.no_plot:
        print(f"Wrote: {plot_path}")


if __name__ == "__main__":
    main()
