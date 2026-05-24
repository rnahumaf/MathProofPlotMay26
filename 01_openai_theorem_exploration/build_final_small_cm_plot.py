#!/usr/bin/env python3
"""
Small final figure for the unit-distance CM construction narrative.

This is a deliberately small, exact, didactic slice of the larger Stage 16
idea.  It uses K = Q(zeta_24), a CM field, and selects roots of unity

    u_j = zeta_24^a_j.

For each selected u_j, complex conjugation sends u_j to u_j^-1, so
u_j * c(u_j) = 1.  Under the chosen complex embedding these elements are
ordinary unit vectors in the plane.

The finite point set is the projected Boolean box

    P(epsilon) = sum_j (epsilon_j - 1/2) u_j, epsilon_j in {0, 1}.

Changing one bit translates a point by +/-u_j, hence gives an exact
unit-distance pair.  This is not a replacement for the asymptotic
ideal-class fiber construction; it is the compact final visualization that
keeps the same geometric mechanism visible with few points.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUTDIR = Path("final_small_cm")
M = 24
EXPONENTS = [1, 6, 10, 15, 20]
TOLERANCE = 1e-10

CANVAS_W = 1800
CANVAS_H = 1350
BG = "#ffffff"
INK = "#111827"
MUTED = "#475569"
LIGHT = "#d3d8df"
BLUE = "#2563eb"
RED = "#dc2626"
SLATE = "#64748b"


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


def selected_unit_vectors() -> np.ndarray:
    angles = np.array(EXPONENTS, dtype=float) * 2.0 * math.pi / M
    return np.column_stack([np.cos(angles), np.sin(angles)])


def build_points(unit_vectors: np.ndarray) -> list[dict]:
    k = len(unit_vectors)
    rows: list[dict] = []
    for mask in range(1 << k):
        bits = np.array([(mask >> j) & 1 for j in range(k)], dtype=float)
        xy = (bits - 0.5) @ unit_vectors
        rows.append(
            {
                "id": mask,
                "bits": "".join(str(int(b)) for b in bits[::-1]),
                "x": float(xy[0]),
                "y": float(xy[1]),
            }
        )
    return rows


def point_array(points: list[dict]) -> np.ndarray:
    return np.array([[row["x"], row["y"]] for row in points], dtype=float)


def constructive_edges(points: list[dict]) -> set[tuple[int, int]]:
    k = len(EXPONENTS)
    edges: set[tuple[int, int]] = set()
    for mask in range(1 << k):
        for bit in range(k):
            other = mask ^ (1 << bit)
            edges.add(tuple(sorted((mask, other))))
    return edges


def all_unit_edges(points: list[dict]) -> list[dict]:
    arr = point_array(points)
    forced = constructive_edges(points)
    rows: list[dict] = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            distance = float(np.linalg.norm(arr[j] - arr[i]))
            if abs(distance - 1.0) <= TOLERANCE:
                rows.append(
                    {
                        "from_id": i,
                        "to_id": j,
                        "distance": distance,
                        "constructive": (i, j) in forced,
                        "x1": float(arr[i, 0]),
                        "y1": float(arr[i, 1]),
                        "x2": float(arr[j, 0]),
                        "y2": float(arr[j, 1]),
                    }
                )
    return rows


def grid_points(n: int) -> list[dict]:
    cols = math.ceil(math.sqrt(2 * n))
    rows = math.ceil(n / cols)
    out: list[dict] = []
    for point_id in range(n):
        x = point_id % cols
        y = point_id // cols
        out.append({"id": point_id, "x": float(x), "y": float(y)})
    return out


def grid_unit_edges(points: list[dict]) -> list[dict]:
    arr = point_array(points)
    rows: list[dict] = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            distance = float(np.linalg.norm(arr[j] - arr[i]))
            if abs(distance - 1.0) <= TOLERANCE:
                rows.append(
                    {
                        "from_id": i,
                        "to_id": j,
                        "distance": distance,
                        "x1": float(arr[i, 0]),
                        "y1": float(arr[i, 1]),
                        "x2": float(arr[j, 0]),
                        "y2": float(arr[j, 1]),
                    }
                )
    return rows


def panel_boxes() -> list[tuple[int, int, int, int]]:
    margin_x = 80
    top = 150
    gap_x = 70
    gap_y = 80
    panel_w = (CANVAS_W - 2 * margin_x - gap_x) // 2
    panel_h = (CANVAS_H - top - 80 - gap_y) // 2
    return [
        (margin_x, top, margin_x + panel_w, top + panel_h),
        (margin_x + panel_w + gap_x, top, margin_x + 2 * panel_w + gap_x, top + panel_h),
        (margin_x, top + panel_h + gap_y, margin_x + panel_w, top + 2 * panel_h + gap_y),
        (
            margin_x + panel_w + gap_x,
            top + panel_h + gap_y,
            margin_x + 2 * panel_w + gap_x,
            top + 2 * panel_h + gap_y,
        ),
    ]


def draw_multiline(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, size: int) -> None:
    draw.multiline_text(xy, text, fill=fill, font=font(size), spacing=6)


def mapper(
    values: np.ndarray,
    box: tuple[int, int, int, int],
    top_pad: int = 58,
    bottom_pad: int = 42,
    side_pad: int = 36,
):
    x0, y0, x1, y1 = box
    px0, py0 = x0 + side_pad, y0 + top_pad
    px1, py1 = x1 - side_pad, y1 - bottom_pad
    min_x, min_y = values.min(axis=0)
    max_x, max_y = values.max(axis=0)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    pad_x = dx * 0.14
    pad_y = dy * 0.14
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    scale = min((px1 - px0) / (max_x - min_x), (py1 - py0) / (max_y - min_y))
    cx_data = (min_x + max_x) / 2.0
    cy_data = (min_y + max_y) / 2.0
    cx_pix = (px0 + px1) / 2.0
    cy_pix = (py0 + py1) / 2.0

    def project(x: float, y: float) -> tuple[int, int]:
        return (
            int(round(cx_pix + (x - cx_data) * scale)),
            int(round(cy_pix - (y - cy_data) * scale)),
        )

    return project


def draw_alpha_lines(
    image: Image.Image,
    segments: list[tuple[float, float, float, float]],
    project,
    color: tuple[int, int, int, int],
    width: int,
) -> None:
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    for x1, y1, x2, y2 in segments:
        draw.line([project(x1, y1), project(x2, y2)], fill=color, width=width)
    image.alpha_composite(overlay)


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:
    draw.line([start, end], fill=color, width=5)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 18
    wing = 0.48
    p1 = (
        int(end[0] - head * math.cos(angle - wing)),
        int(end[1] - head * math.sin(angle - wing)),
    )
    p2 = (
        int(end[0] - head * math.cos(angle + wing)),
        int(end[1] - head * math.sin(angle + wing)),
    )
    draw.polygon([end, p1, p2], fill=color)


def draw_panel_title(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    draw.text((box[0], box[1]), title, fill=INK, font=font(24, bold=True))


def draw_unit_circle_panel(image: Image.Image, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw_panel_title(draw, box, "1. Translacoes de norma 1 em K = Q(zeta_24)")
    plot_box = (box[0] + 120, box[1] + 68, box[2] - 120, box[3] - 82)
    values = np.array([[-1.35, -1.35], [1.35, 1.35]], dtype=float)
    project = mapper(values, plot_box, top_pad=0, bottom_pad=0, side_pad=0)

    circle = []
    for i in range(361):
        t = 2.0 * math.pi * i / 360.0
        circle.append(project(math.cos(t), math.sin(t)))
    draw.line(circle, fill="#9aa4b2", width=3)
    draw.line([project(-1.2, 0), project(1.2, 0)], fill=LIGHT, width=2)
    draw.line([project(0, -1.2), project(0, 1.2)], fill=LIGHT, width=2)

    colors = ["#c2410c", BLUE, "#0f766e", "#7c3aed", "#ca8a04"]
    unit_vectors = selected_unit_vectors()
    origin = project(0, 0)
    for idx, ((x, y), exponent) in enumerate(zip(unit_vectors, EXPONENTS)):
        end = project(float(x * 0.92), float(y * 0.92))
        draw_arrow(draw, origin, end, colors[idx % len(colors)])
        label = project(float(x * 1.15), float(y * 1.15))
        draw.text((label[0] - 18, label[1] - 10), f"z^{exponent}", fill=INK, font=font(17))

    draw_multiline(
        draw,
        (box[0], box[3] - 54),
        "Cada raiz escolhida tem u c(u) = 1,\nentao a projecao planar tem comprimento 1.",
        MUTED,
        18,
    )


def draw_projection_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    points: list[dict],
    edges: list[dict],
) -> None:
    draw_panel_title(draw, box, "2. Corte finito e projecao")
    arr = point_array(points)
    project = mapper(arr, box)
    constructive = [edge for edge in edges if edge["constructive"]]
    accidental = [edge for edge in edges if not edge["constructive"]]
    draw_alpha_lines(
        image,
        [(e["x1"], e["y1"], e["x2"], e["y2"]) for e in constructive],
        project,
        (37, 99, 235, 58),
        3,
    )
    draw_alpha_lines(
        image,
        [(e["x1"], e["y1"], e["x2"], e["y2"]) for e in accidental],
        project,
        (220, 38, 38, 95),
        4,
    )

    for x, y in arr:
        px, py = project(float(x), float(y))
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill=INK, outline="#ffffff", width=2)

    draw_multiline(
        draw,
        (box[0], box[3] - 54),
        f"{len(points)} pontos | {len(edges)} pares unitarios\n{len(constructive)} forcados por troca de um bit",
        MUTED,
        18,
    )


def draw_grid_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    points: list[dict],
    edges: list[dict],
    ratio: float,
) -> None:
    draw_panel_title(draw, box, "3. Grade retangular com mesmo n")
    arr = point_array(points)
    project = mapper(arr, box)
    draw_alpha_lines(
        image,
        [(e["x1"], e["y1"], e["x2"], e["y2"]) for e in edges],
        project,
        (100, 116, 139, 125),
        4,
    )
    for x, y in arr:
        px, py = project(float(x), float(y))
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill="#334155", outline="#ffffff", width=2)
    draw_multiline(
        draw,
        (box[0], box[3] - 54),
        f"{len(points)} pontos | {len(edges)} pares unitarios\nfatia CM / grade = {ratio:.2f}x",
        MUTED,
        18,
    )


def draw_evolution_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw_panel_title(draw, box, "4. Evolucao do repositorio")
    rows = [
        ("Stage 5", "Raizes ciclotomicas: deltas unitarios exatos."),
        ("Stages 6-10", "Quocientes CM de norma 1 e varreduras de escala."),
        ("Stages 11-14", "Primos split, mesmas normas relativas, polidiscos."),
        ("Stage 16", "Analogo de fibra de classe; muitos quocientes."),
        ("Final small", "Esta figura explicativa compacta com 32 pontos."),
    ]
    y = box[1] + 72
    for label, text in rows:
        draw.text((box[0], y), label, fill=INK, font=font(20, bold=True))
        draw.text((box[0] + 190, y), text, fill=MUTED, font=font(20))
        y += 74
    draw_multiline(
        draw,
        (box[0], box[3] - 76),
        "A figura pequena preserva a leitura geometrica.\nA forca assintotica vem do Stage 16, nao das raizes isoladas.",
        SLATE,
        18,
    )


def plot(points: list[dict], edges: list[dict], grid: list[dict], grid_edges: list[dict], ratio: float) -> None:
    image = Image.new("RGBA", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(image)
    draw.text(
        (80, 52),
        "Fatia CM pequena: translacoes de norma 1 -> projecao finita",
        fill=INK,
        font=font(34, bold=True),
    )
    draw.text(
        (80, 98),
        "Figura compacta com 32 pontos alinhada a geometria da construcao de 2026.",
        fill=MUTED,
        font=font(21),
    )

    boxes = panel_boxes()
    draw_unit_circle_panel(image, draw, boxes[0])
    draw_projection_panel(image, draw, boxes[1], points, edges)
    draw_grid_panel(image, draw, boxes[2], grid, grid_edges, ratio)
    draw_evolution_panel(draw, boxes[3])

    OUTDIR.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUTDIR / "final_small_cm_unit_distance.png", quality=95)


def main() -> None:
    unit_vectors = selected_unit_vectors()
    points = build_points(unit_vectors)
    edges = all_unit_edges(points)
    grid = grid_points(len(points))
    grid_edges = grid_unit_edges(grid)
    ratio = len(edges) / len(grid_edges)

    summary = [
        {
            "field": "Q(zeta_24)",
            "m": M,
            "selected_exponents": " ".join(str(e) for e in EXPONENTS),
            "selected_translations": len(EXPONENTS),
            "points": len(points),
            "constructive_unit_pairs": len(constructive_edges(points)),
            "all_unit_pairs": len(edges),
            "grid_unit_pairs": len(grid_edges),
            "ratio_vs_grid": ratio,
        }
    ]

    OUTDIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTDIR / "points.csv", points, ["id", "bits", "x", "y"])
    write_csv(
        OUTDIR / "unit_edges.csv",
        edges,
        ["from_id", "to_id", "distance", "constructive", "x1", "y1", "x2", "y2"],
    )
    write_csv(
        OUTDIR / "summary.csv",
        summary,
        [
            "field",
            "m",
            "selected_exponents",
            "selected_translations",
            "points",
            "constructive_unit_pairs",
            "all_unit_pairs",
            "grid_unit_pairs",
            "ratio_vs_grid",
        ],
    )
    plot(points, edges, grid, grid_edges, ratio)

    print(f"Wrote {OUTDIR / 'final_small_cm_unit_distance.png'}")
    print(f"points={len(points)} unit_pairs={len(edges)} grid_unit_pairs={len(grid_edges)} ratio={ratio:.3f}")


if __name__ == "__main__":
    main()
