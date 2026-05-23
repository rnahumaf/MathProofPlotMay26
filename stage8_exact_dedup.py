#!/usr/bin/env sage -python
"""
Stage 8: Exact deduplication audit for norm-one quotient constructions.

Why this stage is necessary
---------------------------
Stage 7 generated many exact norm-one translations

    u = q / c(q),       u*c(u) = 1,

then formed points as subset sums of selected translations.

However, different coefficient vectors may represent the same algebraic element
of K. If so, they are the same point in the plane and must not be counted as
different vertices.

Stage 8 fixes this:
    1. generate translations as in Stage 7;
    2. build subset/symmetric sums;
    3. deduplicate exact algebraic points in K;
    4. map every coefficient vector to its exact point id;
    5. count only unique edges between distinct exact points;
    6. export collision statistics and a corrected 2D plot.

This is a validation stage before moving to split-prime/class-group-fiber
constructions.
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
    R = PolynomialRing(QQ, "x")
    x = R.gen()
    return R(sage_eval(poly_text, locals={"x": x}))


def parse_float_or_none(value: str) -> float | None:
    if value.lower() in {"none", "null", "nan"}:
        return None
    return float(value)


def tuple_key(tup: tuple[int, ...]) -> str:
    return " ".join(str(int(x)) for x in tup)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, tuple):
                    value = tuple_key(value)
                out[key] = value
            writer.writerow(out)


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


def element_parts(z, L, iK):
    coeffs = z.list()
    zero = L(0)

    if len(coeffs) == 0:
        return zero, zero
    if len(coeffs) == 1:
        return coeffs[0], zero
    return coeffs[0], coeffs[1]


def cm_conjugate(z, L, iK):
    real_part, imag_part = element_parts(z, L, iK)
    return real_part - imag_part * iK


def embedding_values(z, L, L_embeddings, iK):
    real_part, imag_part = element_parts(z, L, iK)
    values = []

    for emb in L_embeddings:
        a = complex(emb(real_part))
        b = complex(emb(imag_part))
        values.append(complex(a.real, b.real))

    return values


def tuple_to_element(tup: tuple[int, ...], L_basis, iK, denominator: int):
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


def exact_key(z) -> str:
    """
    Stable exact key for an element of K.

    Sage elements from the same parent have canonical printed representations.
    This is slower than hashing but safer across Sage versions.
    """
    return str(z)


def canonical_sign_key(u) -> str:
    return min(exact_key(u), exact_key(-u))


def generate_norm_one_translations(
    L,
    L_basis,
    iK,
    q_bound: int,
    q_denominator: int,
    exclude_trivial: bool,
    verbose: bool,
):
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

        # Exact relative norm-one check.
        if u * cm_conjugate(u, L, iK) != 1:
            continue

        if exclude_trivial and (u == 1 or u == -1 or u == iK or u == -iK):
            continue

        key = canonical_sign_key(u)
        if key in seen:
            continue
        seen.add(key)

        values = embedding_values(u, L, L_embeddings, iK)
        abs_values = [abs(v) for v in values]
        angle = principal_angle(values)

        rows.append(
            {
                "u": u,
                "u_key": exact_key(u),
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


def coefficient_ranges_for_points(r: int, mode: str, bound: int):
    if mode == "binary":
        return [range(0, 2) for _ in range(r)]
    if mode == "symmetric":
        return [range(-bound, bound + 1) for _ in range(r)]
    raise ValueError("mode must be binary or symmetric")


def build_exact_dedup_points(
    translations: list[dict],
    L,
    iK,
    radius: float,
    principal_radius: float | None,
    coefficient_mode: str,
    coeff_bound: int,
    verbose: bool,
):
    """
    Build points as exact sums of translations and deduplicate exact K-elements.

    Returns:
        point_rows: one row per distinct exact point
        coeff_to_point_id: coefficient vector -> exact point id
        collision_rows: coefficient vectors that collapsed to existing points
        raw_kept_count: coefficient vectors passing the window before dedup
    """
    r = len(translations)
    L_embeddings = L.embeddings(CC)

    coefficient_ranges = coefficient_ranges_for_points(r, coefficient_mode, coeff_bound)
    U_numeric = np.array([row["embedding_values"] for row in translations], dtype=complex)
    U_exact = [row["u"] for row in translations]

    point_rows = []
    collision_rows = []
    coeff_to_point_id = {}
    exact_to_point_id = {}

    raw_kept_count = 0

    for coeffs_raw in itertools.product(*coefficient_ranges):
        coeffs = tuple(int(c) for c in coeffs_raw)
        cvec = np.array(coeffs, dtype=float)

        # Fast numerical embedding filter.
        values = cvec @ U_numeric
        abs_values = np.abs(values)
        max_abs = float(np.max(abs_values))
        principal_abs = float(abs_values[0])

        if max_abs > radius:
            continue
        if principal_radius is not None and principal_abs > principal_radius:
            continue

        raw_kept_count += 1

        # Exact algebraic sum.
        z = sum(coeffs[j] * U_exact[j] for j in range(r))
        z_key = exact_key(z)

        if z_key in exact_to_point_id:
            existing_id = exact_to_point_id[z_key]
            coeff_to_point_id[coeffs] = existing_id
            collision_rows.append(
                {
                    "coeffs": coeffs,
                    "existing_point_id": existing_id,
                    "exact_point_key": z_key,
                }
            )
            continue

        point_id = len(point_rows)
        exact_to_point_id[z_key] = point_id
        coeff_to_point_id[coeffs] = point_id

        point_rows.append(
            {
                "id": point_id,
                "coeffs": coeffs,
                "x": float(values[0].real),
                "y": float(values[0].imag),
                "principal_abs": principal_abs,
                "max_embedding_abs": max_abs,
                "exact_point_key": z_key,
            }
        )

    if verbose:
        print(f"Raw coefficient points kept: {raw_kept_count}")
        print(f"Distinct exact points: {len(point_rows)}")
        print(f"Exact collisions: {len(collision_rows)}")

    return point_rows, coeff_to_point_id, collision_rows, raw_kept_count


def count_exact_edges(
    point_rows: list[dict],
    coeff_to_point_id: dict[tuple[int, ...], int],
    translations: list[dict],
    coefficient_mode: str,
    coeff_bound: int,
):
    """
    Count unique edges between distinct exact points.

    Edges are generated by incrementing one selected translation coefficient.
    Collapsed points are handled by coeff_to_point_id.
    """
    id_to_point = {row["id"]: row for row in point_rows}
    coeffs_all = list(coeff_to_point_id.keys())
    r = len(translations)

    edge_seen = set()
    edge_rows = []
    loop_collisions = 0

    for coeffs in coeffs_all:
        source_id = coeff_to_point_id[coeffs]

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
            target_id = coeff_to_point_id.get(target_tuple)
            if target_id is None:
                continue

            if source_id == target_id:
                loop_collisions += 1
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

    return len(edge_rows), edge_rows, loop_collisions


def plot_result(output_png, point_rows, edge_rows, summary, translations, max_plot_edges):
    try:
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
    ax.set_title("Exact-deduplicated norm-one quotient construction")
    ax.text(
        0.02,
        0.98,
        (
            f"distinct points: {n}\n"
            f"raw kept coeffs: {summary['raw_kept_coefficient_points']}\n"
            f"exact collisions: {summary['exact_point_collisions']}\n"
            f"unit-distance pairs: {summary['unit_distance_pairs']}\n"
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
    ax.set_title(f"Near-square grid with same distinct n\n{grid_rows} rows x {grid_cols} columns")
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
        "Stage 8: exact point deduplication audit\n"
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
        write_csv(path, [], ["id", "coeffs", "x", "y", "principal_abs", "max_embedding_abs", "exact_point_key"])
        return

    write_csv(path, point_rows, list(point_rows[0].keys()))


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
                "u_exact": tr["u_key"],
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
    parser.add_argument("--q-bound", type=int, default=4)
    parser.add_argument("--q-denominator", type=int, default=1)
    parser.add_argument("--translation-count", type=int, default=16)
    parser.add_argument("--exclude-trivial", action="store_true")
    parser.add_argument("--point-mode", choices=["binary", "symmetric"], default="binary")
    parser.add_argument("--point-coeff-bound", type=int, default=1)
    parser.add_argument("--radius", type=float, default=7.0)
    parser.add_argument("--principal-radius", type=str, default="none")
    parser.add_argument("--outdir", type=Path, default=Path("stage8_exact_dedup_output"))
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

    print("Stage 8 configuration")
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

    point_rows, coeff_to_point_id, collision_rows, raw_kept_count = build_exact_dedup_points(
        translations=selected,
        L=L,
        iK=iK,
        radius=args.radius,
        principal_radius=principal_radius,
        coefficient_mode=args.point_mode,
        coeff_bound=args.point_coeff_bound,
        verbose=True,
    )

    if not point_rows:
        raise SystemExit("No distinct points survived the window. Increase --radius.")

    edge_count, edge_rows, loop_collisions = count_exact_edges(
        point_rows=point_rows,
        coeff_to_point_id=coeff_to_point_id,
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
        "raw_kept_coefficient_points": raw_kept_count,
        "distinct_points": n,
        "exact_point_collisions": len(collision_rows),
        "edge_loop_collisions": loop_collisions,
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else 0,
        "avg_unit_neighbors_per_point": 2 * edge_count / n,
        "numeric_max_edge_error": max_edge_error,
    }

    stem = (
        f"stage8_Ldeg{f}"
        f"_qb{args.q_bound}"
        f"_tc{len(selected)}"
        f"_R{args.radius}"
        f"_{args.point_mode}"
    ).replace(".", "p")

    summary_path = args.outdir / f"{stem}_summary.csv"
    points_path = args.outdir / f"{stem}_distinct_points.csv"
    collisions_path = args.outdir / f"{stem}_exact_collisions.csv"
    translations_path = args.outdir / f"{stem}_translations.csv"
    edges_path = args.outdir / f"{stem}_unit_edges.csv"
    plot_path = args.outdir / f"{stem}_comparison.png"

    write_csv(summary_path, [summary], list(summary.keys()))
    write_points_csv(points_path, point_rows)

    if collision_rows:
        write_csv(collisions_path, collision_rows, ["coeffs", "existing_point_id", "exact_point_key"])
    else:
        write_csv(collisions_path, [], ["coeffs", "existing_point_id", "exact_point_key"])

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
    print(f"Wrote: {collisions_path}")
    print(f"Wrote: {translations_path}")
    print(f"Wrote: {edges_path}")
    if not args.no_plot:
        print(f"Wrote: {plot_path}")


if __name__ == "__main__":
    main()
