#!/usr/bin/env sage -python
"""
Stage 14: Centered Minkowski polydisc for cyclotomic split-prime ideal fibers.

Why this matters
----------------
Stage 13 applied the product-of-discs filter to uncentered subset sums:

    sum_j eps_j u_j,    eps_j in {0,1}.

But a Minkowski window should be centered. Translating all points by a constant
does not change unit distances, so the more faithful finite model is:

    sum_j (eps_j - 1/2) u_j.

This keeps the same unit edges, because changing eps_j from 0 to 1 changes the
point by exactly u_j, but it makes the product-of-discs cut geometrically
meaningful.

Stage 14:
    - reuses the split-prime ideal same-norm fiber machinery from Stage 13;
    - normalizes every q_j in every complex embedding;
    - builds centered subset sums;
    - filters by max_sigma |centered sum_sigma| <= R;
    - projects to sigma_1;
    - deduplicates exact algebraic points using 2*sum eps_j q_j - sum q_j;
    - counts unit-distance edges.

Default:
    - summary CSV only
    - no huge detail files unless --save-details
    - no PNG unless --plot-best
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path

import numpy as np

from sage.all import CyclotomicField, CC  # type: ignore


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, (list, tuple)):
                    value = " ".join(str(x) for x in value)
                out[key] = value
            writer.writerow(out)


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


def primes_split_completely_in_cyclotomic(m: int, count: int) -> list[int]:
    primes = []
    n = 2
    while len(primes) < count:
        if n % m == 1 and is_prime(n):
            primes.append(n)
        n += 1
    return primes


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


def make_cm_conjugation(K):
    zeta = K.gen()
    return K.hom([zeta ** (-1)], K)


def conjugate_ideal(K, conj, I):
    return K.ideal([conj(g) for g in I.gens()])


def pair_conjugate_prime_ideals(K, conj, prime_ideals):
    unused = list(prime_ideals)
    pairs = []
    while unused:
        P = unused.pop(0)
        cP = conjugate_ideal(K, conj, P)
        found_idx = None
        for i, Q in enumerate(unused):
            if Q == cP:
                found_idx = i
                break
        if found_idx is None:
            continue
        Q = unused.pop(found_idx)
        pairs.append((P, Q))
    return pairs


def try_principal_generator(K, I):
    try:
        if hasattr(I, "is_principal") and not I.is_principal():
            return None
    except Exception:
        pass

    for method_name in ["gens_reduced", "gens"]:
        try:
            gens = list(getattr(I, method_name)())
            for g in gens:
                try:
                    if K.ideal(g) == I:
                        return g
                except Exception:
                    continue
        except Exception:
            pass

    for method_name in ["principal_generator", "generator"]:
        try:
            g = getattr(I, method_name)()
            if K.ideal(g) == I:
                return g
        except Exception:
            pass

    return None


def principal_complex_value(z) -> complex:
    return complex(CC(z))


def principal_angle(z) -> float:
    v = principal_complex_value(z)
    t = math.atan2(v.imag, v.real)
    if t < 0:
        t += 2 * math.pi
    return t


def embedding_values(embeddings, z):
    return [complex(emb(z)) for emb in embeddings]


def build_split_ideal_generators(m: int, split_prime_count: int, max_choices: int, verbose: bool):
    K = CyclotomicField(m, "z")
    conj = make_cm_conjugation(K)
    embeddings = K.embeddings(CC)

    primes = primes_split_completely_in_cyclotomic(m, split_prime_count)
    pair_blocks = []
    factor_summary = []

    for p in primes:
        fac = list(K.ideal(p).factor())
        prime_ideals = [P for P, e in fac if e == 1]
        pairs = pair_conjugate_prime_ideals(K, conj, prime_ideals)
        pair_blocks.extend(pairs)

        factor_summary.append(
            {
                "m": m,
                "p": p,
                "prime_ideal_count": len(prime_ideals),
                "conjugate_pair_count": len(pairs),
            }
        )

    total_pairs = len(pair_blocks)
    total_choices = 1 << total_pairs

    if max_choices is not None and total_choices > max_choices:
        raise RuntimeError(
            f"Too many ideal choices: 2^{total_pairs}={total_choices}, "
            f"exceeds --max-ideal-choices={max_choices}."
        )

    if verbose:
        print(f"K = Q(zeta_{m}), degree={K.degree()}")
        print(f"split rational primes: {primes}")
        print(f"conjugate prime-ideal pairs: {total_pairs}")
        print(f"ideal choices to test: {total_choices}")

    q_rows = []
    principal_count = 0
    nonprincipal_count = 0
    seen_q = set()
    one_ideal = K.ideal(1)

    for mask in range(total_choices):
        I = one_ideal

        for j, (P, Q) in enumerate(pair_blocks):
            I *= Q if ((mask >> j) & 1) else P

        q = try_principal_generator(K, I)
        if q is None:
            nonprincipal_count += 1
            continue

        principal_count += 1

        # Deduplicate q and -q.
        q_key = min(exact_key(q), exact_key(-q))
        if q_key in seen_q:
            continue
        seen_q.add(q_key)

        cq = conj(q)
        mu = q * cq
        vals = embedding_values(embeddings, q)
        abs_vals = [abs(v) for v in vals]

        q_rows.append(
            {
                "q": q,
                "q_key": exact_key(q),
                "mask": mask,
                "angle": principal_angle(q),
                "mu": mu,
                "mu_key": exact_key(mu),
                "principal_abs": float(abs_vals[0]),
                "max_abs_all_embeddings": float(max(abs_vals)),
                "embedding_values": vals,
            }
        )

    metadata = {
        "m": m,
        "degree": K.degree(),
        "embedding_count": len(embeddings),
        "split_primes": " ".join(str(p) for p in primes),
        "split_prime_count": split_prime_count,
        "conjugate_pair_count": total_pairs,
        "ideal_choices": total_choices,
        "principal_ideal_products": principal_count,
        "nonprincipal_ideal_products": nonprincipal_count,
        "distinct_q_up_to_sign": len(q_rows),
    }

    return K, conj, embeddings, q_rows, metadata, factor_summary


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


def select_random(candidates: list[dict], count: int, rng: random.Random) -> list[dict]:
    if count >= len(candidates):
        return list(candidates)
    selected = rng.sample(candidates, count)
    selected.sort(key=lambda r: r["angle"])
    return selected


def normalized_embedding_matrix(selected: list[dict]) -> np.ndarray:
    rows = []
    for row in selected:
        normed = []
        for v in row["embedding_values"]:
            av = abs(v)
            if av == 0:
                raise RuntimeError("Unexpected zero embedding value.")
            normed.append(v / av)
        rows.append(normed)
    return np.array(rows, dtype=complex)


def build_centered_polydisc_points(
    selected: list[dict],
    polydisc_radius: float | None,
    principal_radius: float | None,
    save_details: bool,
):
    """
    Build centered subset sums:
        sum_j (eps_j - 1/2) u_j.

    Exact dedup key uses:
        2*sum_j eps_j q_j - sum_j q_j.
    """
    r = len(selected)
    raw_total = 1 << r

    U = normalized_embedding_matrix(selected)
    q_exact = [row["q"] for row in selected]

    total_numeric = np.sum(U, axis=0)
    total_exact = sum(q_exact)

    point_rows = []
    mask_to_point_id = {}
    exact_to_point_id = {}
    raw_kept = 0
    collisions = 0

    numeric_sums = [None] * raw_total
    exact_sums = [None] * raw_total
    numeric_sums[0] = np.zeros(U.shape[1], dtype=complex)
    exact_sums[0] = 0 * q_exact[0] if q_exact else 0

    for mask in range(raw_total):
        if mask != 0:
            lsb = mask & -mask
            j = lsb.bit_length() - 1
            prev = mask ^ lsb
            numeric_sums[mask] = numeric_sums[prev] + U[j]
            exact_sums[mask] = exact_sums[prev] + q_exact[j]

        centered_values = numeric_sums[mask] - 0.5 * total_numeric
        principal_abs = abs(centered_values[0])
        max_abs = float(np.max(np.abs(centered_values)))

        if polydisc_radius is not None and max_abs > polydisc_radius:
            continue
        if principal_radius is not None and principal_abs > principal_radius:
            continue

        raw_kept += 1

        centered_exact_key_element = 2 * exact_sums[mask] - total_exact
        z_key = exact_key(centered_exact_key_element)

        if z_key in exact_to_point_id:
            pid = exact_to_point_id[z_key]
            mask_to_point_id[mask] = pid
            collisions += 1
            continue

        pid = len(point_rows)
        exact_to_point_id[z_key] = pid
        mask_to_point_id[mask] = pid

        row = {
            "id": pid,
            "mask": mask,
            "x": float(centered_values[0].real),
            "y": float(centered_values[0].imag),
            "principal_abs": float(principal_abs),
            "max_embedding_abs": float(max_abs),
        }

        if save_details:
            row["exact_centered_key"] = z_key

        point_rows.append(row)

    return point_rows, mask_to_point_id, raw_total, raw_kept, collisions


def count_edges(point_rows, mask_to_point_id, selected_count: int, save_details: bool):
    id_to_point = {row["id"]: row for row in point_rows}
    edge_seen = set()
    edge_rows = []
    loop_collisions = 0

    for mask, source_id in mask_to_point_id.items():
        for j in range(selected_count):
            if (mask >> j) & 1:
                continue
            target_mask = mask | (1 << j)
            target_id = mask_to_point_id.get(target_mask)
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


def evaluate_selected(
    selected: list[dict],
    mu_key: str,
    fiber_size: int,
    selection_method: str,
    selection_attempt: int,
    polydisc_radius: float | None,
    principal_radius: float | None,
    save_details: bool,
):
    point_rows, mask_to_point_id, raw_total, raw_kept, collisions = build_centered_polydisc_points(
        selected=selected,
        polydisc_radius=polydisc_radius,
        principal_radius=principal_radius,
        save_details=save_details,
    )

    if not point_rows:
        return None, None

    edge_count, edge_rows, loop_collisions = count_edges(
        point_rows=point_rows,
        mask_to_point_id=mask_to_point_id,
        selected_count=len(selected),
        save_details=save_details,
    )

    n = len(point_rows)
    grid_rows, grid_cols, grid_edges = near_square_grid_unit_edges(n)

    max_edge_error = ""
    if edge_rows:
        max_edge_error = max(abs(float(row["numeric_distance"]) - 1.0) for row in edge_rows)

    summary = {
        "mu_key": mu_key,
        "fiber_size": fiber_size,
        "selected_translations": len(selected),
        "selection_method": selection_method,
        "selection_attempt": selection_attempt,
        "polydisc_radius": "none" if polydisc_radius is None else polydisc_radius,
        "principal_radius": "none" if principal_radius is None else principal_radius,
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
        "avg_unit_neighbors_per_point": 2 * edge_count / n,
        "numeric_max_edge_error": max_edge_error,
    }

    data = {
        "point_rows": point_rows,
        "edge_rows": edge_rows,
        "selected": selected,
    }

    return summary, data


def plot_result(output_png: Path, point_rows, edge_rows, summary, max_plot_edges: int):
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
    colors = np.array([row["max_embedding_abs"] for row in point_rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(17, 7.6), dpi=220)

    ax = axes[0]
    plot_edges = edge_rows
    if len(plot_edges) > max_plot_edges:
        idx = np.linspace(0, len(plot_edges) - 1, max_plot_edges).astype(int)
        plot_edges = [plot_edges[int(i)] for i in idx]

    if plot_edges:
        segments = np.array(
            [[[e["x1"], e["y1"]], [e["x2"], e["y2"]]] for e in plot_edges],
            dtype=float,
        )
        ax.add_collection(LineCollection(segments, linewidths=0.18, alpha=0.10))

    sc = ax.scatter(xy[:, 0], xy[:, 1], c=colors, s=5, alpha=0.9, zorder=3)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("max embedding |centered sum|")

    ax.autoscale()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.25)
    ax.set_xlabel("Re(centered normalized sigma_1 sum)")
    ax.set_ylabel("Im(centered normalized sigma_1 sum)")
    ax.set_title("Centered cyclotomic split-prime ideal polydisc")

    ax.text(
        0.02,
        0.98,
        (
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
        "Stage 14: centered Minkowski polydisc, proof-aligned finite visualization\n"
        f"{summary['unit_distance_pairs']} vs {grid_edges} unit-distance pairs "
        f"({summary['ratio_vs_grid']:.2f}x grid)",
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def parse_optional_float_list(items: list[str]) -> list[float | None]:
    out = []
    for item in items:
        if item.lower() in {"none", "null", "nan"}:
            out.append(None)
        else:
            out.append(float(item))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", type=int, nargs="+", default=[8, 12, 16, 20, 24])
    parser.add_argument("--split-prime-counts", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--translation-counts", type=int, nargs="+", default=[8, 10, 12, 14])
    parser.add_argument("--polydisc-radii", type=str, nargs="+", default=["1.5", "2", "2.5", "3", "4"])
    parser.add_argument("--principal-radii", type=str, nargs="+", default=["none"])
    parser.add_argument("--selection-methods", type=str, nargs="+", default=["angle"])
    parser.add_argument("--random-attempts", type=int, default=0)
    parser.add_argument("--random-seed", type=int, default=12345)
    parser.add_argument("--max-ideal-choices", type=int, default=200000)
    parser.add_argument("--max-raw-points", type=int, default=300000)
    parser.add_argument("--min-fiber-size", type=int, default=4)
    parser.add_argument("--outdir", type=Path, default=Path("stage14_centered_polydisc_output"))
    parser.add_argument("--save-details", action="store_true")
    parser.add_argument("--plot-best", action="store_true")
    parser.add_argument("--max-plot-edges", type=int, default=100000)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.random_seed)

    polydisc_radii = parse_optional_float_list(args.polydisc_radii)
    principal_radii = parse_optional_float_list(args.principal_radii)

    global_summaries = []
    factor_summaries = []
    fiber_summaries = []
    best_summary = None
    best_context = None

    for m in args.m_values:
        for spc in args.split_prime_counts:
            print(f"Building split-ideal q's: m={m}, split_prime_count={spc}")

            try:
                K, conj, embeddings, q_rows, metadata, factor_summary = build_split_ideal_generators(
                    m=m,
                    split_prime_count=spc,
                    max_choices=args.max_ideal_choices,
                    verbose=args.verbose,
                )
            except Exception as exc:
                print(f"  failed: {exc}")
                global_summaries.append({"m": m, "split_prime_count": spc, "status": "failed", "error": str(exc)})
                continue

            for row in factor_summary:
                r = dict(metadata)
                r.update(row)
                factor_summaries.append(r)

            groups = {}
            for row in q_rows:
                groups.setdefault(row["mu_key"], []).append(row)

            print(
                f"  q's={len(q_rows)}, mu groups={len(groups)}, "
                f"principal_products={metadata['principal_ideal_products']}, "
                f"nonprincipal={metadata['nonprincipal_ideal_products']}"
            )

            for mu_key, group in groups.items():
                fiber_summaries.append({**metadata, "mu_key": mu_key, "fiber_size": len(group)})

            for mu_key, group in groups.items():
                if len(group) < args.min_fiber_size:
                    continue

                for tc in args.translation_counts:
                    if tc > len(group):
                        continue
                    raw_points = 1 << tc
                    if raw_points > args.max_raw_points:
                        print(f"  skipping tc={tc}: 2^tc={raw_points} exceeds max raw points")
                        continue

                    candidate_selections = []
                    if "angle" in args.selection_methods:
                        candidate_selections.append(("angle", 0, select_spread_by_angle(group, tc)))

                    if "random" in args.selection_methods and args.random_attempts > 0:
                        for attempt in range(1, args.random_attempts + 1):
                            candidate_selections.append(("random", attempt, select_random(group, tc, rng)))

                    for method, attempt, selected in candidate_selections:
                        for polyr in polydisc_radii:
                            for prinr in principal_radii:
                                summary, data = evaluate_selected(
                                    selected=selected,
                                    mu_key=mu_key,
                                    fiber_size=len(group),
                                    selection_method=method,
                                    selection_attempt=attempt,
                                    polydisc_radius=polyr,
                                    principal_radius=prinr,
                                    save_details=False,
                                )
                                if summary is None:
                                    continue

                                summary.update(metadata)
                                summary["status"] = "ok"
                                global_summaries.append(summary)

                                print(
                                    f"  fiber={len(group)} tc={tc} {method}#{attempt} "
                                    f"polyR={polyr} prinR={prinr}: "
                                    f"n={summary['distinct_points']} edges={summary['unit_distance_pairs']} "
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
                                    best_context = (mu_key, selected, polyr, prinr)

    # Write summaries.
    if global_summaries:
        all_fields = sorted({k for row in global_summaries for k in row.keys()})
        write_csv(args.outdir / "stage14_centered_polydisc_summary.csv", global_summaries, all_fields)
    else:
        write_csv(args.outdir / "stage14_centered_polydisc_summary.csv", [], ["status"])

    if factor_summaries:
        all_fields = sorted({k for row in factor_summaries for k in row.keys()})
        write_csv(args.outdir / "stage14_factor_summary.csv", factor_summaries, all_fields)
    else:
        write_csv(args.outdir / "stage14_factor_summary.csv", [], ["m"])

    if fiber_summaries:
        all_fields = sorted({k for row in fiber_summaries for k in row.keys()})
        write_csv(args.outdir / "stage14_fiber_summary.csv", fiber_summaries, all_fields)
    else:
        write_csv(args.outdir / "stage14_fiber_summary.csv", [], ["m"])

    if best_summary is None:
        print("No successful evaluated fiber. Inspect summary files.")
        print(f"Wrote: {args.outdir / 'stage14_centered_polydisc_summary.csv'}")
        print(f"Wrote: {args.outdir / 'stage14_factor_summary.csv'}")
        print(f"Wrote: {args.outdir / 'stage14_fiber_summary.csv'}")
        return

    print()
    print("Best configuration:")
    for key, value in best_summary.items():
        text = str(value)
        if len(text) > 180:
            text = text[:180] + "..."
        print(f"{key}: {text}")

    if args.save_details or args.plot_best:
        mu_key, selected, polyr, prinr = best_context
        summary, data = evaluate_selected(
            selected=selected,
            mu_key=mu_key,
            fiber_size=int(best_summary["fiber_size"]),
            selection_method=str(best_summary["selection_method"]),
            selection_attempt=int(best_summary["selection_attempt"]),
            polydisc_radius=polyr,
            principal_radius=prinr,
            save_details=True,
        )
        summary.update(best_summary)

        stem = (
            f"best_m{best_summary['m']}_spc{best_summary['split_prime_count']}"
            f"_tc{best_summary['selected_translations']}"
            f"_polyR{best_summary['polydisc_radius']}"
            f"_prinR{best_summary['principal_radius']}"
        ).replace(".", "p")

        if args.save_details:
            points_path = args.outdir / f"{stem}_points.csv"
            edges_path = args.outdir / f"{stem}_unit_edges.csv"
            selected_path = args.outdir / f"{stem}_selected_q.csv"

            write_csv(points_path, data["point_rows"], list(data["point_rows"][0].keys()))
            if data["edge_rows"]:
                write_csv(edges_path, data["edge_rows"], list(data["edge_rows"][0].keys()))
            else:
                write_csv(edges_path, [], ["from_id", "to_id"])

            selected_rows = []
            for i, row in enumerate(data["selected"]):
                selected_rows.append(
                    {
                        "id": i,
                        "q_key": row["q_key"],
                        "angle": row["angle"],
                        "principal_abs": row["principal_abs"],
                        "max_abs_all_embeddings": row["max_abs_all_embeddings"],
                    }
                )
            write_csv(selected_path, selected_rows, ["id", "q_key", "angle", "principal_abs", "max_abs_all_embeddings"])

            print(f"Wrote detail file: {points_path}")
            print(f"Wrote detail file: {edges_path}")
            print(f"Wrote detail file: {selected_path}")

        if args.plot_best:
            plot_path = args.outdir / f"{stem}_comparison.png"
            plot_result(
                output_png=plot_path,
                point_rows=data["point_rows"],
                edge_rows=data["edge_rows"],
                summary=summary,
                max_plot_edges=args.max_plot_edges,
            )
            print(f"Wrote plot: {plot_path}")

    print()
    print(f"Wrote: {args.outdir / 'stage14_centered_polydisc_summary.csv'}")
    print(f"Wrote: {args.outdir / 'stage14_factor_summary.csv'}")
    print(f"Wrote: {args.outdir / 'stage14_fiber_summary.csv'}")


if __name__ == "__main__":
    main()
