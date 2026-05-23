#!/usr/bin/env sage -python
"""
Stage 9: Scaling sweep for exact-deduplicated norm-one quotient constructions.

This script automates what Stage 8 did for one configuration.

It tests multiple:
    - totally real fields L = Q(a),
    - q-bounds,
    - translation counts,
    - radii,

and for each configuration it:
    1. generates exact norm-one translations u = q/c(q);
    2. selects well-spaced directions in the principal embedding;
    3. forms binary subset sums;
    4. filters by a product-of-discs radius in all embeddings;
    5. deduplicates exact algebraic points in K;
    6. counts unique unit edges;
    7. compares against a same-n grid.

This does not yet implement the split-prime/class-group-fiber theorem engine.
It is a scaling laboratory for the validated Stage 8 construction.
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
    return str(z)


def canonical_sign_key(u) -> str:
    return min(exact_key(u), exact_key(-u))


def build_field(poly_text: str):
    poly = parse_poly(poly_text)
    L = NumberField(poly, "a")
    a = L.gen()

    R = PolynomialRing(L, "y")
    y = R.gen()
    K = L.extension(y**2 + 1, "i")
    iK = K.gen()

    L_basis = [L(a**j) for j in range(L.degree())]
    return poly, L, K, iK, L_basis


def generate_norm_one_translations(
    L,
    L_basis,
    iK,
    q_bound: int,
    q_denominator: int,
    exclude_trivial: bool,
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

            min_dist = math.inf
            for j in selected_indices:
                diff = abs(angle - angles[j])
                diff = min(diff, 2 * math.pi - diff)
                min_dist = min(min_dist, diff)

            if min_dist > best_score:
                best_score = min_dist
                best_idx = i

        assert best_idx is not None
        selected_indices.append(best_idx)

    selected = [candidates[i] for i in selected_indices]
    selected.sort(key=lambda r: r["angle"])
    return selected


def build_exact_dedup_binary_points(translations: list[dict], radius: float):
    r = len(translations)
    U_numeric = np.array([row["embedding_values"] for row in translations], dtype=complex)
    U_exact = [row["u"] for row in translations]

    point_rows = []
    coeff_to_point_id = {}
    exact_to_point_id = {}
    collision_count = 0
    raw_kept = 0

    for mask in range(1 << r):
        coeffs = tuple((mask >> j) & 1 for j in range(r))
        cvec = np.array(coeffs, dtype=float)

        values = cvec @ U_numeric
        abs_values = np.abs(values)
        max_abs = float(np.max(abs_values))

        if max_abs > radius:
            continue

        raw_kept += 1

        z = sum(coeffs[j] * U_exact[j] for j in range(r))
        z_key = exact_key(z)

        if z_key in exact_to_point_id:
            point_id = exact_to_point_id[z_key]
            coeff_to_point_id[coeffs] = point_id
            collision_count += 1
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
                "principal_abs": float(abs_values[0]),
                "max_embedding_abs": max_abs,
                "exact_point_key": z_key,
            }
        )

    return point_rows, coeff_to_point_id, raw_kept, collision_count


def count_edges(point_rows: list[dict], coeff_to_point_id: dict[tuple[int, ...], int], r: int, save_edges: bool):
    id_to_point = {row["id"]: row for row in point_rows}
    coeffs_all = list(coeff_to_point_id.keys())

    edge_seen = set()
    loop_collisions = 0
    edge_rows = []

    for coeffs in coeffs_all:
        source_id = coeff_to_point_id[coeffs]

        for j in range(r):
            if coeffs[j] == 1:
                continue

            target = list(coeffs)
            target[j] = 1
            target = tuple(target)

            target_id = coeff_to_point_id.get(target)
            if target_id is None:
                continue

            if source_id == target_id:
                loop_collisions += 1
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
                        "changed_generator": j,
                    }
                )

    return len(edge_seen), edge_rows, loop_collisions


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

    for tr in translations:
        ax.plot([0, tr["principal_dx"]], [0, tr["principal_dy"]], linewidth=1.0, alpha=0.25)

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(sigma_1(z))")
    ax.set_ylabel("Im(sigma_1(z))")
    ax.set_title("Best exact-deduplicated scaling candidate")
    ax.text(
        0.02,
        0.98,
        (
            f"distinct points: {n}\n"
            f"unit-distance pairs: {summary['unit_distance_pairs']}\n"
            f"translations: {summary['selected_translations']}\n"
            f"ratio vs grid: {summary['ratio_vs_grid']:.2f}x"
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

    fig.suptitle(
        "Stage 9 scaling sweep: exact-deduplicated norm-one quotient construction\n"
        f"{summary['unit_distance_pairs']} vs {grid_edges} unit-distance pairs "
        f"({summary['ratio_vs_grid']:.2f}x grid)",
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def analyze_configuration(poly_text: str, q_bound: int, translation_count: int, radius: float, q_denominator: int, exclude_trivial: bool, save_edges: bool):
    poly, L, K, iK, L_basis = build_field(poly_text)
    candidates = generate_norm_one_translations(
        L=L,
        L_basis=L_basis,
        iK=iK,
        q_bound=q_bound,
        q_denominator=q_denominator,
        exclude_trivial=exclude_trivial,
    )

    if len(candidates) < translation_count:
        return None, None

    selected = select_translations(candidates, translation_count)
    point_rows, coeff_to_point_id, raw_kept, collisions = build_exact_dedup_binary_points(selected, radius)

    if not point_rows:
        return None, None

    edge_count, edge_rows, loop_collisions = count_edges(point_rows, coeff_to_point_id, translation_count, save_edges)
    n = len(point_rows)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    max_edge_error = ""
    if edge_rows:
        max_edge_error = max(abs(float(e["numeric_distance"]) - 1.0) for e in edge_rows)

    summary = {
        "L_poly": str(poly),
        "L_degree": L.degree(),
        "K_degree": 2 * L.degree(),
        "q_bound": q_bound,
        "q_denominator": q_denominator,
        "candidate_translations": len(candidates),
        "selected_translations": len(selected),
        "radius": radius,
        "raw_kept_coefficient_points": raw_kept,
        "distinct_points": n,
        "exact_point_collisions": collisions,
        "edge_loop_collisions": loop_collisions,
        "unit_distance_pairs": edge_count,
        "grid_rows": grid_rows,
        "grid_cols": grid_cols,
        "grid_unit_distance_pairs": grid_edges,
        "ratio_vs_grid": edge_count / grid_edges if grid_edges else 0,
        "avg_unit_neighbors_per_point": 2 * edge_count / n,
        "numeric_max_edge_error": max_edge_error,
    }

    data = {
        "point_rows": point_rows,
        "edge_rows": edge_rows,
        "selected": selected,
    }

    return summary, data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--L-polys", type=str, nargs="+", default=["x^2-2"])
    parser.add_argument("--q-bounds", type=int, nargs="+", default=[3, 4])
    parser.add_argument("--translation-counts", type=int, nargs="+", default=[14, 16, 18])
    parser.add_argument("--radii", type=float, nargs="+", default=[6, 7, 8])
    parser.add_argument("--q-denominator", type=int, default=1)
    parser.add_argument("--exclude-trivial", action="store_true")
    parser.add_argument("--max-raw-points", type=int, default=1_200_000)
    parser.add_argument("--outdir", type=Path, default=Path("stage9_scaling_sweep_output"))
    parser.add_argument("--max-plot-edges", type=int, default=100000)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    summaries = []

    for poly_text in args.L_polys:
        for q_bound in args.q_bounds:
            for translation_count in args.translation_counts:
                raw_possible = 1 << translation_count
                if raw_possible > args.max_raw_points:
                    print(f"Skipping tc={translation_count}: 2^tc={raw_possible} exceeds --max-raw-points.")
                    continue

                for radius in args.radii:
                    print(f"Running: L={poly_text}, q_bound={q_bound}, tc={translation_count}, radius={radius}")

                    summary, _ = analyze_configuration(
                        poly_text=poly_text,
                        q_bound=q_bound,
                        translation_count=translation_count,
                        radius=radius,
                        q_denominator=args.q_denominator,
                        exclude_trivial=args.exclude_trivial,
                        save_edges=False,
                    )

                    if summary is None:
                        print("  skipped/no candidate")
                        continue

                    summaries.append(summary)
                    print(
                        f"  n={summary['distinct_points']} edges={summary['unit_distance_pairs']} "
                        f"grid={summary['grid_unit_distance_pairs']} ratio={summary['ratio_vs_grid']:.4f} "
                        f"collisions={summary['exact_point_collisions']}"
                    )

    if not summaries:
        raise SystemExit("No configurations completed.")

    summaries.sort(key=lambda r: (float(r["ratio_vs_grid"]), int(r["unit_distance_pairs"])), reverse=True)

    fields = list(summaries[0].keys())
    summary_path = args.outdir / "stage9_scaling_summary.csv"
    write_csv(summary_path, summaries, fields)

    best = summaries[0]
    print()
    print("Best configuration:")
    for k, v in best.items():
        print(f"{k}: {v}")

    # Re-run best with edge export and plot.
    best_summary, best_data = analyze_configuration(
        poly_text=best["L_poly"],
        q_bound=int(best["q_bound"]),
        translation_count=int(best["selected_translations"]),
        radius=float(best["radius"]),
        q_denominator=int(best["q_denominator"]),
        exclude_trivial=args.exclude_trivial,
        save_edges=True,
    )

    stem = (
        f"best_Ldeg{best_summary['L_degree']}"
        f"_qb{best_summary['q_bound']}"
        f"_tc{best_summary['selected_translations']}"
        f"_R{best_summary['radius']}"
    ).replace(".", "p")

    points_path = args.outdir / f"{stem}_points.csv"
    edges_path = args.outdir / f"{stem}_unit_edges.csv"
    translations_path = args.outdir / f"{stem}_translations.csv"
    plot_path = args.outdir / f"{stem}_comparison.png"

    write_csv(points_path, best_data["point_rows"], list(best_data["point_rows"][0].keys()))

    if best_data["edge_rows"]:
        write_csv(
            edges_path,
            best_data["edge_rows"],
            ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"],
        )
    else:
        write_csv(edges_path, [], ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"])

    tr_rows = []
    for idx, tr in enumerate(best_data["selected"]):
        tr_rows.append(
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
        translations_path,
        tr_rows,
        ["id", "q_tuple", "principal_dx", "principal_dy", "principal_abs", "angle", "hidden_max_abs", "u_exact"],
    )

    if not args.no_plot:
        plot_result(
            output_png=plot_path,
            point_rows=best_data["point_rows"],
            edge_rows=best_data["edge_rows"],
            summary=best_summary,
            translations=best_data["selected"],
            max_plot_edges=args.max_plot_edges,
        )

    print()
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {points_path}")
    print(f"Wrote: {edges_path}")
    print(f"Wrote: {translations_path}")
    if not args.no_plot:
        print(f"Wrote: {plot_path}")


if __name__ == "__main__":
    main()
