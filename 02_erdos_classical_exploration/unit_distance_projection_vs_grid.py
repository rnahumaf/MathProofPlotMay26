#!/usr/bin/env python3
"""
Toy visualization for the planar unit-distance problem.

This script is NOT the actual OpenAI/CM-field construction.
It is a small, reproducible toy model meant to illustrate the visual mechanism:
many exact unit distances can survive after projecting a higher-dimensional
combinatorial object down to the plane.

Construction:
    Start with all 8-bit vectors b in {0,1}^8.
    Choose 8 unit vectors u_j in the complex plane.
    Project each bit vector to 2D by

        P(b) = sum_j b_j * u_j.

If two bit vectors differ in exactly one coordinate j, then

        P(b') - P(b) = +/- u_j,

so their Euclidean distance in the plane is exactly |u_j| = 1.

The script compares this projected point set with a regular 16x16 grid,
using the same number of points: 256.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def projected_hypercube_points(k: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build a projected k-dimensional Boolean hypercube.

    Returns:
        points_df:
            id, x, y for all 2^k projected points.

        constructive_edges_df:
            all pairs that differ in one bit. These are guaranteed to be
            exactly unit-distance pairs by construction.
    """
    angles_deg = np.array([0, 31, 79, 127, 181, 229, 283, 331], dtype=float)
    if k != len(angles_deg):
        raise ValueError("This demo is configured for k=8.")

    angles = np.deg2rad(angles_deg)
    unit_vectors = np.column_stack([np.cos(angles), np.sin(angles)])

    rows = []
    for mask in range(1 << k):
        bits = np.array([(mask >> j) & 1 for j in range(k)])
        xy = bits @ unit_vectors
        rows.append(
            {
                "id": mask,
                "bits": "".join(str(int(b)) for b in bits[::-1]),
                "x": xy[0],
                "y": xy[1],
            }
        )

    points_df = pd.DataFrame(rows)

    edge_rows = []
    for mask in range(1 << k):
        for bit in range(k):
            mask2 = mask ^ (1 << bit)
            if mask < mask2:
                p = points_df.loc[points_df["id"] == mask, ["x", "y"]].to_numpy()[0]
                q = points_df.loc[points_df["id"] == mask2, ["x", "y"]].to_numpy()[0]
                distance = float(np.linalg.norm(q - p))
                edge_rows.append(
                    {
                        "from_id": mask,
                        "to_id": mask2,
                        "changed_bit": bit,
                        "x1": p[0],
                        "y1": p[1],
                        "x2": q[0],
                        "y2": q[1],
                        "distance": distance,
                    }
                )

    constructive_edges_df = pd.DataFrame(edge_rows)
    return points_df, constructive_edges_df


def brute_force_unit_pairs(points_df: pd.DataFrame, tolerance: float = 1e-10) -> pd.DataFrame:
    """
    Count all point pairs whose projected Euclidean distance is numerically 1.

    The one-bit-flip pairs are guaranteed. This brute-force pass can also catch
    extra accidental unit distances caused by the particular angular choices.
    """
    points = points_df[["x", "y"]].to_numpy()
    ids = points_df["id"].to_numpy()

    rows = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            distance = float(np.linalg.norm(points[j] - points[i]))
            if abs(distance - 1.0) <= tolerance:
                rows.append(
                    {
                        "from_id": int(ids[i]),
                        "to_id": int(ids[j]),
                        "distance": distance,
                    }
                )

    return pd.DataFrame(rows)


def regular_grid_points(side: int = 16) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build a regular side x side grid with spacing 1.

    In a regular square grid, unit-distance pairs are exactly the horizontal
    and vertical adjacent pairs, giving 2 * side * (side - 1).
    """
    rows = []
    for y in range(side):
        for x in range(side):
            rows.append({"id": y * side + x, "x": float(x), "y": float(y)})
    points_df = pd.DataFrame(rows)

    edge_rows = []
    for y in range(side):
        for x in range(side):
            id1 = y * side + x
            if x + 1 < side:
                id2 = y * side + (x + 1)
                edge_rows.append(
                    {
                        "from_id": id1,
                        "to_id": id2,
                        "x1": float(x),
                        "y1": float(y),
                        "x2": float(x + 1),
                        "y2": float(y),
                        "distance": 1.0,
                    }
                )
            if y + 1 < side:
                id2 = (y + 1) * side + x
                edge_rows.append(
                    {
                        "from_id": id1,
                        "to_id": id2,
                        "x1": float(x),
                        "y1": float(y),
                        "x2": float(x),
                        "y2": float(y + 1),
                        "distance": 1.0,
                    }
                )

    edges_df = pd.DataFrame(edge_rows)
    return points_df, edges_df


def plot_comparison(
    projected_points: pd.DataFrame,
    projected_edges: pd.DataFrame,
    grid_points: pd.DataFrame,
    grid_edges: pd.DataFrame,
    output_png: Path,
) -> None:
    """Create a side-by-side comparison figure."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.2), dpi=220)

    ax = axes[0]
    point_lookup = projected_points.set_index("id")[["x", "y"]]
    for _, edge in projected_edges.iterrows():
        p = point_lookup.loc[int(edge["from_id"])].to_numpy()
        q = point_lookup.loc[int(edge["to_id"])].to_numpy()
        ax.plot([p[0], q[0]], [p[1], q[1]], linewidth=0.3, alpha=0.08)

    ax.scatter(projected_points["x"], projected_points["y"], s=16, alpha=0.78)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.35, alpha=0.3)
    ax.set_title(
        "2D projection of 256 points\n"
        f"unit-distance pairs: {len(projected_edges)}"
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.text(
        0.02,
        0.98,
        (
            "n = 256\n"
            f"measured unit pairs: {len(projected_edges)}\n"
            f"avg. unit neighbors per point: {2 * len(projected_edges) / len(projected_points):.2f}"
        ),
        transform=ax.transAxes,
        va="top",
        bbox=dict(boxstyle="round", alpha=0.85),
        fontsize=10,
    )

    ax = axes[1]
    for _, edge in grid_edges.iterrows():
        ax.plot([edge["x1"], edge["x2"]], [edge["y1"], edge["y2"]], linewidth=0.5, alpha=0.25)

    ax.scatter(grid_points["x"], grid_points["y"], s=16, alpha=0.78)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.35, alpha=0.3)
    ax.set_title(
        "Regular 16x16 grid = 256 points\n"
        f"unit-distance pairs: {len(grid_edges)}"
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.text(
        0.02,
        0.98,
        (
            "n = 256\n"
            "horizontal pairs: 240\n"
            "vertical pairs: 240\n"
            f"total: {len(grid_edges)}\n"
            f"avg. unit neighbors per point: {2 * len(grid_edges) / len(grid_points):.2f}"
        ),
        transform=ax.transAxes,
        va="top",
        bbox=dict(boxstyle="round", alpha=0.85),
        fontsize=10,
    )

    ratio = len(projected_edges) / len(grid_edges)
    fig.suptitle(
        (
            "Same number of points: 2D projection vs regular grid\n"
            f"{len(projected_edges)} vs {len(grid_edges)} unit-distance pairs "
            f"({ratio:.2f}x more in the projection)"
        ),
        y=1.02,
        fontsize=15,
    )

    fig.tight_layout()
    fig.savefig(output_png, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    output_dir = Path(".")
    output_png = output_dir / "unit_distance_projection_vs_grid.png"
    output_summary_csv = output_dir / "unit_distance_summary.csv"
    output_projected_points_csv = output_dir / "projected_points.csv"
    output_projected_pairs_csv = output_dir / "projected_unit_pairs.csv"

    projected_points, constructive_edges = projected_hypercube_points(k=8)
    measured_projected_pairs = brute_force_unit_pairs(projected_points, tolerance=1e-10)
    grid_points, grid_edges = regular_grid_points(side=16)

    projected_points.to_csv(output_projected_points_csv, index=False)
    measured_projected_pairs.to_csv(output_projected_pairs_csv, index=False)

    summary = pd.DataFrame(
        [
            {
                "model": "toy_projected_8d_boolean_hypercube",
                "points": len(projected_points),
                "constructive_unit_pairs": len(constructive_edges),
                "measured_unit_pairs": len(measured_projected_pairs),
                "average_unit_neighbors_per_point": 2 * len(measured_projected_pairs) / len(projected_points),
                "note": "Toy model, not the actual CM-field/OpenAI construction.",
            },
            {
                "model": "regular_16x16_grid",
                "points": len(grid_points),
                "constructive_unit_pairs": len(grid_edges),
                "measured_unit_pairs": len(grid_edges),
                "average_unit_neighbors_per_point": 2 * len(grid_edges) / len(grid_points),
                "note": "Unit pairs are horizontal and vertical adjacent grid neighbors.",
            },
        ]
    )
    summary.to_csv(output_summary_csv, index=False)

    plot_comparison(
        projected_points=projected_points,
        projected_edges=measured_projected_pairs,
        grid_points=grid_points,
        grid_edges=grid_edges,
        output_png=output_png,
    )

    print(summary.to_string(index=False))
    print()
    print(f"Wrote: {output_png}")
    print(f"Wrote: {output_summary_csv}")
    print(f"Wrote: {output_projected_points_csv}")
    print(f"Wrote: {output_projected_pairs_csv}")


if __name__ == "__main__":
    main()
