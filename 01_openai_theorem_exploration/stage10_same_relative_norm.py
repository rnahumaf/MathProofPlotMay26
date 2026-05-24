#!/usr/bin/env sage -python
"""
Stage 10: Same-relative-norm fibers, closer to the published proof.

This stage moves from the quotient construction u=q/c(q) to the mechanism used
in the paper:

    find many elements q in K with the same relative norm
        q * c(q) = mu in L.

If q_1, ..., q_r have the same relative norm mu, then for every embedding sigma,

    |sigma(q_j)|^2 = sigma(mu).

After scaling the principal projection by sqrt(sigma_1(mu)), each q_j becomes
a unit vector in the plane.

Thus a finite set of subset sums of q_j gives a 2D point set with many exact
unit-distance edges. This is the finite computational analogue of the paper's
Lemma 5 / Lemma 7 mechanism:

    ideal/lattice in a CM field
    many elements with a fixed relative norm
    product-of-discs window
    projection to one complex place

Default behavior:
    - save summary CSV only
    - do NOT save huge points/edges/translations files
    - do NOT plot unless --plot-best is supplied

Use --save-details if you explicitly want large CSV outputs.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from sage.all import PolynomialRing, QQ, CC, NumberField, sage_eval  # type: ignore


def parse_poly(poly_text: str):
    R = PolynomialRing(QQ, "x")
    x = R.gen()
    return R(sage_eval(poly_text, locals={"x": x}))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, tuple):
                    value = " ".join(str(int(x)) for x in value)
                out[key] = value
            writer.writerow(out)


def exact_key(z) -> str:
    return str(z)


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


def tuple_to_element(tup: tuple[int, ...], L_basis, iK, denominator: int):
    f = len(L_basis)
    real_coeffs = tup[:f]
    imag_coeffs = tup[f:]

    A = sum(real_coeffs[j] * L_basis[j] for j in range(f))
    B = sum(imag_coeffs[j] * L_basis[j] for j in range(f))

    return (A + B * iK) / denominator


def embedding_values(z, L, L_embeddings, iK):
    real_part, imag_part = element_parts(z, L, iK)
    values = []

    for emb in L_embeddings:
        a = complex(emb(real_part))
        b = complex(emb(imag_part))
        values.append(complex(a.real, b.real))

    return values


def principal_angle(z_values: list[complex]) -> float:
    angle = math.atan2(z_values[0].imag, z_values[0].real)
    if angle < 0:
        angle += 2 * math.pi
    return angle


def canonical_sign_key(z) -> str:
    return min(exact_key(z), exact_key(-z))


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


def enumerate_same_norm_fibers(
    L,
    L_basis,
    iK,
    q_bound: int,
    denominator: int,
    min_principal_mu: float,
    max_principal_mu: float | None,
    dedup_sign: bool,
    verbose: bool,
):
    """
    Enumerate q and group by exact relative norm mu = q*c(q).

    q and -q may be deduplicated because they produce opposite directions;
    for unit-distance counts with undirected edges, duplicates by sign are
    usually not useful.
    """
    f = len(L_basis)
    dim = 2 * f
    L_embeddings = L.embeddings(CC)

    groups = defaultdict(list)
    mu_info = {}
    seen_q_signs = set()

    total_q = 0
    kept_q = 0

    for tup in coefficient_tuples(dim, q_bound):
        if not any(tup):
            continue

        total_q += 1

        q = tuple_to_element(tup, L_basis, iK, denominator)

        if dedup_sign:
            sign_key = canonical_sign_key(q)
            if sign_key in seen_q_signs:
                continue
            seen_q_signs.add(sign_key)

        cq = cm_conjugate(q, L, iK)
        mu = q * cq

        # mu lies in L, embedded inside K. Extract the L part.
        mu_L, mu_imag = element_parts(mu, L, iK)
        if mu_imag != 0:
            raise RuntimeError("Relative norm unexpectedly has nonzero imaginary part.")

        mu_values = [complex(emb(mu_L)).real for emb in L_embeddings]

        # For totally positive mu, all embedding values should be positive.
        if any(v <= 0 for v in mu_values):
            continue

        principal_mu = float(mu_values[0])
        if principal_mu < min_principal_mu:
            continue
        if max_principal_mu is not None and principal_mu > max_principal_mu:
            continue

        q_values = embedding_values(q, L, L_embeddings, iK)

        mu_key = exact_key(mu_L)
        kept_q += 1

        groups[mu_key].append(
            {
                "q": q,
                "q_tuple": tup,
                "q_key": exact_key(q),
                "q_values": q_values,
                "angle": principal_angle(q_values),
            }
        )

        if mu_key not in mu_info:
            mu_info[mu_key] = {
                "mu": mu_L,
                "mu_key": mu_key,
                "principal_mu": principal_mu,
                "max_mu_embedding": float(max(mu_values)),
                "min_mu_embedding": float(min(mu_values)),
                "mu_values": mu_values,
            }

    if verbose:
        print(f"Enumerated q candidates: {total_q}")
        print(f"Kept q after filters/dedup: {kept_q}")
        print(f"Relative-norm fibers: {len(groups)}")

    return groups, mu_info


def select_spread_by_angle(candidates: list[dict], count: int) -> list[dict]:
    candidates = sorted(candidates, key=lambda r: r["angle"])

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


def normalized_embedding_values(q_values: list[complex], mu_values: list[float]):
    """
    Normalize q in every complex embedding by sqrt(sigma(mu)).

    Each normalized embedding should have absolute value 1.
    """
    return [q_values[i] / math.sqrt(mu_values[i]) for i in range(len(q_values))]


def build_subset_sum_points(
    selected: list[dict],
    mu_values: list[float],
    radius: float,
    save_details: bool,
):
    """
    Build binary subset sums of q_j, normalized in each embedding.

    Exact deduplication uses unnormalized exact q sums.
    Geometric filtering uses normalized embedding sums.
    """
    r = len(selected)

    U_numeric = np.array(
        [normalized_embedding_values(row["q_values"], mu_values) for row in selected],
        dtype=complex,
    )
    U_exact = [row["q"] for row in selected]

    raw_kept = 0
    collisions = 0
    point_rows = []
    coeff_to_point_id = {}
    exact_to_point_id = {}

    for mask in range(1 << r):
        coeffs = tuple((mask >> j) & 1 for j in range(r))
        cvec = np.array(coeffs, dtype=float)

        values = cvec @ U_numeric
        max_abs = float(np.max(np.abs(values)))

        if max_abs > radius:
            continue

        raw_kept += 1

        z_exact = sum(coeffs[j] * U_exact[j] for j in range(r))
        z_key = exact_key(z_exact)

        if z_key in exact_to_point_id:
            point_id = exact_to_point_id[z_key]
            coeff_to_point_id[coeffs] = point_id
            collisions += 1
            continue

        point_id = len(point_rows)
        exact_to_point_id[z_key] = point_id
        coeff_to_point_id[coeffs] = point_id

        if save_details:
            point_rows.append(
                {
                    "id": point_id,
                    "coeffs": coeffs,
                    "x": float(values[0].real),
                    "y": float(values[0].imag),
                    "principal_abs": float(abs(values[0])),
                    "max_embedding_abs": max_abs,
                    "exact_point_key": z_key,
                }
            )
        else:
            # Keep only what is needed for plotting if requested later.
            point_rows.append(
                {
                    "id": point_id,
                    "coeffs": coeffs,
                    "x": float(values[0].real),
                    "y": float(values[0].imag),
                    "max_embedding_abs": max_abs,
                }
            )

    return point_rows, coeff_to_point_id, raw_kept, collisions


def count_edges(point_rows: list[dict], coeff_to_point_id: dict[tuple[int, ...], int], r: int, save_details: bool):
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


def evaluate_fiber(
    mu_key: str,
    fiber: list[dict],
    mu_info: dict,
    translation_count: int,
    radius: float,
    save_details: bool,
):
    if len(fiber) < translation_count:
        return None, None

    selected = select_spread_by_angle(fiber, translation_count)
    info = mu_info[mu_key]
    mu_values = info["mu_values"]

    point_rows, coeff_to_point_id, raw_kept, collisions = build_subset_sum_points(
        selected=selected,
        mu_values=mu_values,
        radius=radius,
        save_details=save_details,
    )

    if not point_rows:
        return None, None

    edge_count, edge_rows, loop_collisions = count_edges(
        point_rows=point_rows,
        coeff_to_point_id=coeff_to_point_id,
        r=len(selected),
        save_details=save_details,
    )

    n = len(point_rows)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    max_edge_error = ""
    if edge_rows:
        max_edge_error = max(abs(float(e["numeric_distance"]) - 1.0) for e in edge_rows)

    summary = {
        "mu_key": mu_key,
        "fiber_size": len(fiber),
        "selected_translations": len(selected),
        "radius": radius,
        "principal_mu": info["principal_mu"],
        "min_mu_embedding": info["min_mu_embedding"],
        "max_mu_embedding": info["max_mu_embedding"],
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
        "mu_info": info,
    }

    return summary, data


def plot_result(output_png, point_rows, edge_rows, summary, max_plot_edges):
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
    cbar.set_label("max normalized embedding size")

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(normalized sigma_1(z))")
    ax.set_ylabel("Im(normalized sigma_1(z))")
    ax.set_title("Same-relative-norm fiber construction")
    ax.text(
        0.02,
        0.98,
        (
            f"distinct points: {n}\n"
            f"fiber size: {summary['fiber_size']}\n"
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
        "Stage 10: same relative norm fiber, normalized projection\n"
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
    parser.add_argument("--L-poly", type=str, default="x^2-2")
    parser.add_argument("--q-bound", type=int, default=5)
    parser.add_argument("--denominator", type=int, default=1)
    parser.add_argument("--translation-counts", type=int, nargs="+", default=[6, 8, 10, 12, 14])
    parser.add_argument("--radii", type=float, nargs="+", default=[4, 5, 6, 7, 8])
    parser.add_argument("--min-fiber-size", type=int, default=6)
    parser.add_argument("--top-fibers", type=int, default=20)
    parser.add_argument("--min-principal-mu", type=float, default=0.0)
    parser.add_argument("--max-principal-mu", type=str, default="none")
    parser.add_argument("--keep-signs", action="store_true", help="Do not identify q and -q during fiber construction.")
    parser.add_argument("--max-raw-points", type=int, default=300000)
    parser.add_argument("--outdir", type=Path, default=Path("stage10_same_norm_output"))
    parser.add_argument("--save-details", action="store_true", help="Save large points/edges/translations CSVs for the best case.")
    parser.add_argument("--plot-best", action="store_true", help="Generate a PNG for the best case. Implies edge details for the best case.")
    parser.add_argument("--max-plot-edges", type=int, default=100000)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    max_principal_mu = None
    if args.max_principal_mu.lower() not in {"none", "null", "nan"}:
        max_principal_mu = float(args.max_principal_mu)

    poly, L, K, iK, L_basis = build_field(args.L_poly)

    print("Stage 10 configuration")
    print(f"L polynomial: {poly}")
    print(f"[L:Q] = {L.degree()}")
    print(f"K = L(i), [K:Q] = {2*L.degree()}")
    print(f"q_bound = {args.q_bound}")
    print(f"denominator = {args.denominator}")
    print(f"save_details = {args.save_details}")
    print(f"plot_best = {args.plot_best}")
    print()

    groups, mu_info = enumerate_same_norm_fibers(
        L=L,
        L_basis=L_basis,
        iK=iK,
        q_bound=args.q_bound,
        denominator=args.denominator,
        min_principal_mu=args.min_principal_mu,
        max_principal_mu=max_principal_mu,
        dedup_sign=not args.keep_signs,
        verbose=True,
    )

    fiber_rows = []
    for mu_key, fiber in groups.items():
        if len(fiber) >= args.min_fiber_size:
            info = mu_info[mu_key]
            fiber_rows.append(
                {
                    "mu_key": mu_key,
                    "fiber_size": len(fiber),
                    "principal_mu": info["principal_mu"],
                    "min_mu_embedding": info["min_mu_embedding"],
                    "max_mu_embedding": info["max_mu_embedding"],
                }
            )

    fiber_rows.sort(key=lambda r: r["fiber_size"], reverse=True)
    fiber_summary_path = args.outdir / "stage10_fiber_summary.csv"
    if fiber_rows:
        write_csv(fiber_summary_path, fiber_rows, list(fiber_rows[0].keys()))
    else:
        write_csv(fiber_summary_path, [], ["mu_key", "fiber_size", "principal_mu", "min_mu_embedding", "max_mu_embedding"])

    print(f"Fibers with size >= {args.min_fiber_size}: {len(fiber_rows)}")
    if fiber_rows[:10]:
        print("Top fibers:")
        for row in fiber_rows[:10]:
            print(
                f"  size={row['fiber_size']} principal_mu={row['principal_mu']:.6g} "
                f"mu={row['mu_key'][:90]}"
            )

    candidate_fibers = fiber_rows[:args.top_fibers]
    summaries = []
    best_summary = None
    best_data = None

    for fiber_row in candidate_fibers:
        mu_key = fiber_row["mu_key"]
        fiber = groups[mu_key]

        for translation_count in args.translation_counts:
            if translation_count > len(fiber):
                continue

            raw_possible = 1 << translation_count
            if raw_possible > args.max_raw_points:
                print(f"Skipping tc={translation_count}: 2^tc={raw_possible} exceeds --max-raw-points.")
                continue

            for radius in args.radii:
                print(f"Evaluating fiber_size={len(fiber)}, tc={translation_count}, radius={radius}")

                summary, data = evaluate_fiber(
                    mu_key=mu_key,
                    fiber=fiber,
                    mu_info=mu_info,
                    translation_count=translation_count,
                    radius=radius,
                    save_details=False,
                )

                if summary is None:
                    continue

                summary.update(
                    {
                        "L_poly": str(poly),
                        "L_degree": L.degree(),
                        "K_degree": 2 * L.degree(),
                        "q_bound": args.q_bound,
                        "denominator": args.denominator,
                    }
                )

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
        raise SystemExit("No same-norm fiber configuration was evaluated. Increase --q-bound or lower --min-fiber-size.")

    summaries.sort(key=lambda r: (float(r["ratio_vs_grid"]), int(r["unit_distance_pairs"])), reverse=True)

    summary_path = args.outdir / "stage10_same_norm_summary.csv"
    write_csv(summary_path, summaries, list(summaries[0].keys()))

    print()
    print("Best configuration:")
    for key, value in summaries[0].items():
        if key == "mu_key":
            print(f"{key}: {str(value)[:160]}")
        else:
            print(f"{key}: {value}")

    # Re-run best with details only if requested.
    if args.save_details or args.plot_best:
        best = summaries[0]
        summary, data = evaluate_fiber(
            mu_key=best["mu_key"],
            fiber=groups[best["mu_key"]],
            mu_info=mu_info,
            translation_count=int(best["selected_translations"]),
            radius=float(best["radius"]),
            save_details=True,
        )

        stem = (
            f"best_Ldeg{L.degree()}"
            f"_qb{args.q_bound}"
            f"_tc{summary['selected_translations']}"
            f"_R{summary['radius']}"
        ).replace(".", "p")

        points_path = args.outdir / f"{stem}_points.csv"
        edges_path = args.outdir / f"{stem}_unit_edges.csv"
        translations_path = args.outdir / f"{stem}_translations.csv"
        plot_path = args.outdir / f"{stem}_comparison.png"

        if args.save_details:
            write_csv(points_path, data["point_rows"], list(data["point_rows"][0].keys()))
            if data["edge_rows"]:
                write_csv(
                    edges_path,
                    data["edge_rows"],
                    ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"],
                )
            else:
                write_csv(edges_path, [], ["from_id", "to_id", "x1", "y1", "x2", "y2", "numeric_distance", "changed_generator"])

            tr_rows = []
            for idx, tr in enumerate(data["selected"]):
                tr_rows.append(
                    {
                        "id": idx,
                        "q_tuple": tr["q_tuple"],
                        "angle": tr["angle"],
                        "q_exact": tr["q_key"],
                    }
                )
            write_csv(translations_path, tr_rows, ["id", "q_tuple", "angle", "q_exact"])

            print(f"Wrote detail file: {points_path}")
            print(f"Wrote detail file: {edges_path}")
            print(f"Wrote detail file: {translations_path}")

        if args.plot_best:
            plot_result(
                output_png=plot_path,
                point_rows=data["point_rows"],
                edge_rows=data["edge_rows"],
                summary=summary,
                max_plot_edges=args.max_plot_edges,
            )
            print(f"Wrote plot: {plot_path}")

    print()
    print(f"Wrote: {fiber_summary_path}")
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
