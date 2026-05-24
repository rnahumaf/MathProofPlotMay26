#!/usr/bin/env sage -python
"""
Stage 7: Generate many exact norm-one translations via quotients u = q / c(q).

Motivation
----------
Stage 6 used the naive lattice O_L + O_L*i and searched for elements u with

    u * c(u) = 1.

For small coefficient boxes this finds very few translations, e.g. only
+/-1, +/-i in many cases.

The standard way to produce many relative norm-one elements in K = L(i) is:

    u = q / c(q),

where q in K^* and c is CM conjugation over L. Then exactly:

    u * c(u) = 1.

Every embedding has |sigma(u)| = 1, so each such u is a valid unit-distance
translation after projection to any complex coordinate.

This script:
    1. builds a totally real field L = Q(a);
    2. constructs K = L(i);
    3. enumerates small q = A + B*i;
    4. builds many exact norm-one translations u = q / c(q);
    5. selects a set of directions;
    6. forms points as subset sums of the selected translations;
    7. filters by a product-of-discs window across embeddings;
    8. projects to sigma_1(K) ~= C;
    9. counts edges x -> x + u_j exactly by construction;
    10. compares against a same-n near-square grid.

This is still not the final split-prime/class-group-fiber construction of the
paper, but it implements the key "many norm-one translations + polydisc
window + 2D projection" mechanism.
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
    """Parse a polynomial in x over QQ."""
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
    return itertools.product(range(-bound, bound + 1), repeat=dim)


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


def element_parts(z, L, iK):
    """Return z = real_part + imag_part*iK."""
    coeffs = z.list()
    zero = L(0)

    if len(coeffs) == 0:
        return zero, zero
    if len(coeffs) == 1:
        return coeffs[0], zero
    return coeffs[0], coeffs[1]


def cm_conjugate(z, L, iK):
    """CM conjugation: fixes L and sends i -> -i."""
    real_part, imag_part = element_parts(z, L, iK)
    return real_part - imag_part * iK


def embedding_values(z, L, L_embeddings, iK):
    """
    For z = a + b*i and real embeddings tau_r: L -> R,
    return sigma_r(z) = tau_r(a) + i tau_r(b).
    """
    real_part, imag_part = element_parts(z, L, iK)
    values = []

    for emb in L_embeddings:
        a = complex(emb(real_part))
        b = complex(emb(imag_part))
        values.append(complex(a.real, b.real))

    return values


def tuple_to_element(tup: tuple[int, ...], L_basis, iK, denominator: int):
    """
    Convert tuple to A + B*i over the power basis of L.

    tup length = 2f:
        first f entries = coefficients of A
        last f entries  = coefficients of B
    """
    f = len(L_basis)
    real_coeffs = tup[:f]
    imag_coeffs = tup[f:]

    A = sum(real_coeffs[j] * L_basis[j] for j in range(f))
    B = sum(imag_coeffs[j] * L_basis[j] for j in range(f))

    return (A + B * iK) / denominator


def principal_angle(values: list[complex]) -> float:
    angle = math.atan2(values[0].imag, values[0].real)
    if angle < 0:
        angle += 2 * math.pi
    return angle


def canonical_sign_key(u, L, iK) -> str:
    """
    Deduplicate u and -u. For undirected unit-distance edges,
    translation by u and by -u give the same direction.
    """
    return min(str(u), str(-u))


def generate_norm_one_translations(
    L,
    L_basis,
    iK,
    q_bound: int,
    q_denominator: int,
    exclude_trivial: bool,
    verbose: bool,
):
    """
    Enumerate q and form u = q/c(q), with exact u*c(u)=1.

    Returns unique translations up to sign.
    """
    f = len(L_basis)
    dim = 2 * f
    L_embeddings = L.embeddings(CC)

    seen = set()
    rows = []

    for tup in coefficient_tuples(dim, q_bound):
        if not any(tup):
            continue

        q = tuple_to_element(tup, L_basis, iK, q_denominator)
        cq = cm_conjugate(q, L, iK)

        if cq == 0:
            continue

        u = q / cq

        # Exact sanity check.
        if u * cm_conjugate(u, L, iK) != 1:
            continue

        if exclude_trivial and (u == 1 or u == -1 or u == iK or u == -iK):
            continue

        key = canonical_sign_key(u, L, iK)
        if key in seen:
            continue
        seen.add(key)

        values = embedding_values(u, L, L_embeddings, iK)
        abs_values = [abs(v) for v in values]
        angle = principal_angle(values)

        rows.append(
            {
                "u": u,
                "q_tuple": tup,
                "principal_dx": float(values[0].real),
                "principal_dy": float(values[0].imag),
                "principal_abs": float(abs_values[0]),
                "angle": float(angle),
                "hidden_max_abs": float(max(abs_values[1:]) if len(abs_values) > 1 else 0.0),
                "embedding_values": values,
            }
        )

    rows.sort(key=lambda r: r["angle"])

    if verbose:
        print(f"Generated unique norm-one translations up to sign: {len(rows)}")

    return rows


def select_translations(candidates: list[dict], count: int) -> list[dict]:
    """
    Select directions spread around the unit circle in the principal embedding.
    """
    if count >= len(candidates):
        return candidates

    angles = np.array([row["angle"] for row in candidates], dtype=float)

    selected_indices = [0]

    while len(selected_indices) < count:
        best_idx = None
        best_score = -1.0

        for i, angle in enumerate(angles):
            if i in selected_indices:
                continue

            distances = []
            for j in selected_indices:
                diff = abs(angle - angles[j])
                diff = min(diff, 2 * math.pi - diff)
                distances.append(diff)

            score = min(distances)
            if score > best_score:
                best_score = score
                best_idx = i

        assert best_idx is not None
        selected_indices.append(best_idx)

    selected = [candidates[i] for i in selected_indices]
    selected.sort(key=lambda r: r["angle"])
    return selected


def build_subset_sum_points(
    translations: list[dict],
    radius: float,
    principal_radius: float | None,
    coefficient_mode: str,
    coeff_bound: int,
    verbose: bool,
):
    """
    Build points as sums of selected norm-one translations.

    coefficient_mode:
        binary: coefficients in {0,1}
        symmetric: coefficients in {-B,...,B}
    """
    r = len(translations)
    f = len(translations[0]["embedding_values"])

    if coefficient_mode == "binary":
        coefficient_ranges = [range(0, 2) for _ in range(r)]
    elif coefficient_mode == "symmetric":
        coefficient_ranges = [range(-coeff_bound, coeff_bound + 1) for _ in range(r)]
    else:
        raise ValueError("coefficient_mode must be 'binary' or 'symmetric'.")

    U = np.array([row["embedding_values"] for row in translations], dtype=complex)

    point_rows = []
    coeff_to_id = {}

    for coeffs_raw in itertools.product(*coefficient_ranges):
        coeffs = tuple(int(c) for c in coeffs_raw)
        cvec = np.array(coeffs, dtype=float)

        values = cvec @ U
        abs_values = np.abs(values)
        max_abs = float(np.max(abs_values))
        principal_abs = float(abs_values[0])

        if max_abs > radius:
            continue
        if principal_radius is not None and principal_abs > principal_radius:
            continue

        pid = len(point_rows)
        coeff_to_id[coeffs] = pid

        point_rows.append(
            {
                "id": pid,
                "coeffs": coeffs,
                "x": float(values[0].real),
                "y": float(values[0].imag),
                "principal_abs": principal_abs,
                "max_embedding_abs": max_abs,
            }
        )

    if verbose:
        total_possible = 2**r if coefficient_mode == "binary" else (2 * coeff_bound + 1) ** r
        print(f"Subset/sum coefficient points kept: {len(point_rows)} of {total_possible}")

    return point_rows, coeff_to_id


def count_edges(point_rows, coeff_to_id, translations: list[dict], coefficient_mode: str, coeff_bound: int):
    """
    Count edges corresponding to changing one generator coefficient by +1.

    For binary coefficients, this is exactly the hypercube edge relation.
    For symmetric coefficients, it counts neighboring lattice layers.
    """
    id_to_point = {row["id"]: row for row in point_rows}
    coeffs_all = list(coeff_to_id.keys())
    r = len(translations)

    edge_seen = set()
    edge_rows = []

    for coeffs in coeffs_all:
        source_id = coeff_to_id[coeffs]

        for j in range(r):
            target = list(coeffs)
            target[j] += 1

            if coefficient_mode == "binary":
                if target[j] > 1:
                    continue
            else:
                if target[j] > coeff_bound:
                    continue

            target_tuple = tuple(target)
            target_id = coeff_to_id.get(target_tuple)
            if target_id is None:
                continue

            key = (source_id, target_id) if source_id < target_id else (target_id, source_id)
            if key in edge_seen:
                continue
            edge_seen.add(key)

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

    return len(edge_rows), edge_rows


def plot_result(output_png, point_rows, edge_rows, summary, translations, max_plot_edges):
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

    # Draw selected translation directions from the origin.
    for tr in translations:
        ax.plot([0, tr["principal_dx"]], [0, tr["principal_dy"]], linewidth=1.0, alpha=0.35)

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(sigma_1(z))")
    ax.set_ylabel("Im(sigma_1(z))")
    ax.set_title("Norm-one quotient translations\nsubset sums + polydisc filter")
    ax.text(
        0.02,
        0.98,
        (
            f"points: {n}\n"
            f"unit-distance pairs: {summary['unit_distance_pairs']}\n"
            f"selected translations: {summary['selected_translations']}\n"
            f"avg. unit neighbors: {summary['avg_unit_neighbors_per_point']:.2f}"
        ),
        transform=ax.transAxes,
        va="top",
        bbox=dict(boxstyle="round", alpha=0.85),
        fontsize=10,
    )

    ax = axes[1]
    occupied = {(idx // grid_cols, idx % grid_cols) for idx in range(n)}
    for rr, cc in occupied:
        if (rr, cc + 1) in occupied:
            ax.plot([cc, cc + 1], [rr, rr], linewidth=0.3, alpha=0.16)
        if (rr + 1, cc) in occupied:
            ax.plot([cc, cc], [rr, rr + 1], linewidth=0.3, alpha=0.16)

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
        "Stage 7: many exact norm-one quotient translations\n"
        f"{summary['unit_distance_pairs']} vs {grid_edges} unit-distance pairs "
        f"({summary['ratio_vs_grid']:.2f}x grid)",
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def write_points_csv(path: Path, point_rows: list[dict]) -> None:
    if not point_rows:
        return
    fieldnames = list(point_rows[0].keys())
    write_csv(path, point_rows, fieldnames)


def write_translations_csv(path: Path, translations: list[dict]) -> None:
    rows = []
    for idx, tr in enumerate(translations):
        rows.append(
            {
                "id": idx,
                "q_tuple": tr["q_tuple"],
                "principal_dx": tr["principal_dx"],
                "principal_dy": tr["principal_dy"],
                "principal_abs": tr["principal_abs"],
                "angle": tr["angle"],
                "hidden_max_abs": tr["hidden_max_abs"],
                "u_exact": str(tr["u"]),
            }
        )

    write_csv(
        path,
        rows,
        ["id", "q_tuple", "principal_dx", "principal_dy", "principal_abs", "angle", "hidden_max_abs", "u_exact"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--L-poly", type=str, default="x^2-2")
    parser.add_argument("--q-bound", type=int, default=3)
    parser.add_argument("--q-denominator", type=int, default=1)
    parser.add_argument("--translation-count", type=int, default=14)
    parser.add_argument("--exclude-trivial", action="store_true")
    parser.add_argument("--point-mode", choices=["binary", "symmetric"], default="binary")
    parser.add_argument("--point-coeff-bound", type=int, default=1)
    parser.add_argument("--radius", type=float, default=6.0)
    parser.add_argument("--principal-radius", type=str, default="none")
    parser.add_argument("--outdir", type=Path, default=Path("stage7_norm_one_quotients_output"))
    parser.add_argument("--max-plot-edges", type=int, default=80000)
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    poly = parse_poly(args.L_poly)
    L = NumberField(poly, "a")
    a = L.gen()

    R = PolynomialRing(L, "y")
    y = R.gen()
    K = L.extension(y**2 + 1, "i")
    iK = K.gen()

    f = L.degree()
    L_basis = [L(a**j) for j in range(f)]
    principal_radius = parse_float_or_none(args.principal_radius)

    print("Stage 7 configuration")
    print(f"L polynomial: {poly}")
    print(f"[L:Q] = {f}")
    print(f"K = L(i), [K:Q] = {2*f}")
    print(f"q_bound = {args.q_bound}")
    print(f"translation_count = {args.translation_count}")
    print(f"point_mode = {args.point_mode}")
    print(f"radius = {args.radius}")
    print()

    candidates = generate_norm_one_translations(
        L=L,
        L_basis=L_basis,
        iK=iK,
        q_bound=args.q_bound,
        q_denominator=args.q_denominator,
        exclude_trivial=args.exclude_trivial,
        verbose=True,
    )

    if not candidates:
        raise SystemExit("No norm-one quotient translations found. Increase --q-bound.")

    selected = select_translations(candidates, args.translation_count)
    print(f"Selected translations: {len(selected)}")

    point_rows, coeff_to_id = build_subset_sum_points(
        translations=selected,
        radius=args.radius,
        principal_radius=principal_radius,
        coefficient_mode=args.point_mode,
        coeff_bound=args.point_coeff_bound,
        verbose=True,
    )

    if not point_rows:
        raise SystemExit("No points survived the polydisc window. Increase --radius.")

    edge_count, edge_rows = count_edges(
        point_rows=point_rows,
        coeff_to_id=coeff_to_id,
        translations=selected,
        coefficient_mode=args.point_mode,
        coeff_bound=args.point_coeff_bound,
    )

    n = len(point_rows)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)
    max_edge_error = max(abs(e["numeric_distance"] - 1.0) for e in edge_rows) if edge_rows else ""

    summary = {
        "L_poly": str(poly),
        "L_degree": f,
        "K_degree": 2 * f,
        "q_bound": args.q_bound,
        "q_denominator": args.q_denominator,
        "candidate_translations": len(candidates),
        "selected_translations": len(selected),
        "point_mode": args.point_mode,
        "point_coeff_bound": args.point_coeff_bound,
        "radius": args.radius,
        "principal_radius": "none" if principal_radius is None else principal_radius,
        "points": n,
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else 0,
        "avg_unit_neighbors_per_point": 2 * edge_count / n,
        "numeric_max_edge_error": max_edge_error,
    }

    stem = (
        f"stage7_Ldeg{f}"
        f"_qb{args.q_bound}"
        f"_tc{len(selected)}"
        f"_R{args.radius}"
        f"_{args.point_mode}"
    ).replace(".", "p")

    summary_path = args.outdir / f"{stem}_summary.csv"
    points_path = args.outdir / f"{stem}_points.csv"
    translations_path = args.outdir / f"{stem}_translations.csv"
    edges_path = args.outdir / f"{stem}_unit_edges.csv"
    plot_path = args.outdir / f"{stem}_comparison.png"

    write_csv(summary_path, [summary], list(summary.keys()))
    write_points_csv(points_path, point_rows)
    write_translations_csv(translations_path, selected)

    if edge_rows:
        write_csv(
            edges_path,
            edge_rows,
            ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"],
        )
    else:
        write_csv(edges_path, [], ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"])

    if not args.no_plot:
        plot_result(
            output_png=plot_path,
            point_rows=point_rows,
            edge_rows=edge_rows,
            summary=summary,
            translations=selected,
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
