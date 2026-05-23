#!/usr/bin/env python3
"""
Render style trials for one fixed unit-distance dataset.

This script does not recompute the arithmetic construction. It reads one
existing points/edges CSV pair and varies only visual styling: palette, line
width, point size and alpha.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SOURCE_STEM = "05_random_representative"
SOURCE_DIR = Path("final_geometric_variations")
OUTDIR = Path("final_style_trials")
WIDTH = 1800
HEIGHT = 1400
SCALE = 2


GENERATOR_PALETTE = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#65a30d",
    "#c026d3",
    "#0f766e",
    "#b45309",
]


@dataclass(frozen=True)
class Style:
    slug: str
    title: str
    background: str
    line_mode: str
    line_width: int
    line_alpha: int
    point_mode: str
    point_radius: int
    point_alpha: int
    density_gain: float
    density_width_boost: int
    density_threshold: float
    note: str


STYLES = [
    Style(
        slug="01_balanced_light",
        title="Balanced Light",
        background="#ffffff",
        line_mode="generator",
        line_width=1,
        line_alpha=34,
        point_mode="ink",
        point_radius=4,
        point_alpha=235,
        density_gain=4.8,
        density_width_boost=2,
        density_threshold=0.09,
        note="Baseline: colored generators, compact dark points.",
    ),
    Style(
        slug="02_fine_blueprint",
        title="Fine Blueprint",
        background="#f8fafc",
        line_mode="blueprint",
        line_width=1,
        line_alpha=24,
        point_mode="steel",
        point_radius=3,
        point_alpha=220,
        density_gain=8.0,
        density_width_boost=3,
        density_threshold=0.08,
        note="Thin low-alpha lines to emphasize the point cloud.",
    ),
    Style(
        slug="03_high_contrast",
        title="High Contrast",
        background="#ffffff",
        line_mode="charcoal",
        line_width=1,
        line_alpha=30,
        point_mode="black",
        point_radius=5,
        point_alpha=255,
        density_gain=5.5,
        density_width_boost=2,
        density_threshold=0.10,
        note="Almost monochrome, intended for printed documentation.",
    ),
    Style(
        slug="04_generator_ribbons",
        title="Generator Ribbons",
        background="#ffffff",
        line_mode="generator",
        line_width=2,
        line_alpha=42,
        point_mode="small_ink",
        point_radius=3,
        point_alpha=230,
        density_gain=3.6,
        density_width_boost=1,
        density_threshold=0.14,
        note="Thicker colored edges expose the ten translation directions.",
    ),
    Style(
        slug="05_soft_topographic",
        title="Soft Topographic",
        background="#fcfcf9",
        line_mode="sage",
        line_width=1,
        line_alpha=28,
        point_mode="topographic",
        point_radius=4,
        point_alpha=235,
        density_gain=7.0,
        density_width_boost=3,
        density_threshold=0.09,
        note="Point color follows max embedding radius; edges stay restrained.",
    ),
    Style(
        slug="06_warm_cool",
        title="Warm/Cool",
        background="#ffffff",
        line_mode="warm_cool",
        line_width=1,
        line_alpha=36,
        point_mode="cool_warm",
        point_radius=4,
        point_alpha=238,
        density_gain=5.8,
        density_width_boost=2,
        density_threshold=0.10,
        note="Contrasts local directions with a cool-to-warm point scale.",
    ),
    Style(
        slug="07_dark_neon",
        title="Dark Neon",
        background="#0b1020",
        line_mode="neon_generator",
        line_width=1,
        line_alpha=54,
        point_mode="neon",
        point_radius=4,
        point_alpha=245,
        density_gain=5.0,
        density_width_boost=2,
        density_threshold=0.13,
        note="Presentation mode: high visibility on dark background.",
    ),
    Style(
        slug="08_large_points_low_edges",
        title="Large Points / Low Edges",
        background="#ffffff",
        line_mode="mist",
        line_width=1,
        line_alpha=16,
        point_mode="large_gradient",
        point_radius=6,
        point_alpha=232,
        density_gain=9.0,
        density_width_boost=4,
        density_threshold=0.08,
        note="Prioritizes point organization while retaining faint unit edges.",
    ),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf" if bold else "/mnt/c/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    return (*hex_rgb(value), alpha)


def lerp_color(a: str, b: str, t: float, alpha: int) -> tuple[int, int, int, int]:
    ar, ag, ab = hex_rgb(a)
    br, bg, bb = hex_rgb(b)
    t = max(0.0, min(1.0, t))
    return (
        int(round(ar + (br - ar) * t)),
        int(round(ag + (bg - ag) * t)),
        int(round(ab + (bb - ab) * t)),
        alpha,
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mapper(points: list[dict], box: tuple[int, int, int, int]):
    values = np.array([[float(row["x"]), float(row["y"])] for row in points], dtype=float)
    x0, y0, x1, y1 = box
    min_x, min_y = values.min(axis=0)
    max_x, max_y = values.max(axis=0)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    min_x -= 0.10 * dx
    max_x += 0.10 * dx
    min_y -= 0.10 * dy
    max_y += 0.10 * dy
    scale = min((x1 - x0) / (max_x - min_x), (y1 - y0) / (max_y - min_y))
    cx_data = (min_x + max_x) / 2.0
    cy_data = (min_y + max_y) / 2.0
    cx_pix = (x0 + x1) / 2.0
    cy_pix = (y0 + y1) / 2.0

    def project(x: float, y: float) -> tuple[int, int]:
        return (
            int(round((cx_pix + (x - cx_data) * scale) * SCALE)),
            int(round((cy_pix - (y - cy_data) * scale) * SCALE)),
        )

    return project


def line_color(edge: dict, style: Style) -> tuple[int, int, int, int]:
    generator = int(edge.get("changed_generator", 0))
    if style.line_mode in {"generator", "neon_generator"}:
        base = GENERATOR_PALETTE[generator % len(GENERATOR_PALETTE)]
        return rgba(base, style.line_alpha)
    if style.line_mode == "blueprint":
        return rgba("#2563eb", style.line_alpha)
    if style.line_mode == "charcoal":
        return rgba("#111827", style.line_alpha)
    if style.line_mode == "sage":
        return rgba("#6b8f71", style.line_alpha)
    if style.line_mode == "warm_cool":
        t = generator / 9.0
        return lerp_color("#2563eb", "#f97316", t, style.line_alpha)
    if style.line_mode == "mist":
        return rgba("#64748b", style.line_alpha)
    return rgba("#2563eb", style.line_alpha)


def point_color(row: dict, style: Style, max_abs_min: float, max_abs_max: float) -> tuple[int, int, int, int]:
    span = max(max_abs_max - max_abs_min, 1e-9)
    t = (float(row["max_embedding_abs"]) - max_abs_min) / span
    if style.point_mode == "ink":
        return rgba("#0f172a", style.point_alpha)
    if style.point_mode == "small_ink":
        return rgba("#020617", style.point_alpha)
    if style.point_mode == "steel":
        return lerp_color("#334155", "#0f172a", t, style.point_alpha)
    if style.point_mode == "black":
        return rgba("#000000", style.point_alpha)
    if style.point_mode == "topographic":
        if t < 0.5:
            return lerp_color("#0f766e", "#84cc16", t * 2, style.point_alpha)
        return lerp_color("#84cc16", "#f97316", (t - 0.5) * 2, style.point_alpha)
    if style.point_mode == "cool_warm":
        return lerp_color("#0891b2", "#be123c", t, style.point_alpha)
    if style.point_mode == "neon":
        return lerp_color("#22d3ee", "#f0abfc", t, style.point_alpha)
    if style.point_mode == "large_gradient":
        return lerp_color("#0f766e", "#7c3aed", t, style.point_alpha)
    return rgba("#0f172a", style.point_alpha)


def composite_line(
    canvas: Image.Image,
    p1: tuple[int, int],
    p2: tuple[int, int],
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    """Composite one semi-transparent stroke so overlaps accumulate visually."""
    pad = max(width + 3 * SCALE, 8)
    x0 = max(min(p1[0], p2[0]) - pad, 0)
    y0 = max(min(p1[1], p2[1]) - pad, 0)
    x1 = min(max(p1[0], p2[0]) + pad, canvas.width)
    y1 = min(max(p1[1], p2[1]) + pad, canvas.height)
    if x1 <= x0 or y1 <= y0:
        return

    stroke = Image.new("RGBA", (x1 - x0, y1 - y0), (255, 255, 255, 0))
    stroke_draw = ImageDraw.Draw(stroke)
    stroke_draw.line(
        [(p1[0] - x0, p1[1] - y0), (p2[0] - x0, p2[1] - y0)],
        fill=fill,
        width=width,
    )
    canvas.alpha_composite(stroke, (x0, y0))


def accumulate_line(
    alpha_acc: np.ndarray,
    color_acc: np.ndarray,
    p1: tuple[int, int],
    p2: tuple[int, int],
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    pad = max(width + 3 * SCALE, 8)
    x0 = max(min(p1[0], p2[0]) - pad, 0)
    y0 = max(min(p1[1], p2[1]) - pad, 0)
    x1 = min(max(p1[0], p2[0]) + pad, alpha_acc.shape[1])
    y1 = min(max(p1[1], p2[1]) + pad, alpha_acc.shape[0])
    if x1 <= x0 or y1 <= y0:
        return

    mask_image = Image.new("L", (x1 - x0, y1 - y0), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    mask_draw.line(
        [(p1[0] - x0, p1[1] - y0), (p2[0] - x0, p2[1] - y0)],
        fill=fill[3],
        width=width,
    )
    mask = np.asarray(mask_image, dtype=np.float32) / 255.0
    if not np.any(mask):
        return

    alpha_acc[y0:y1, x0:x1] += mask
    rgb = np.array(fill[:3], dtype=np.float32)
    color_acc[y0:y1, x0:x1, :] += mask[:, :, None] * rgb


def composite_accumulated_lines(
    canvas: Image.Image,
    alpha_acc: np.ndarray,
    color_acc: np.ndarray,
    density_gain: float,
    threshold: float = 0.0,
) -> Image.Image:
    background = np.asarray(canvas, dtype=np.float32)
    # Exponential optical-density curve:
    # one stroke remains light, but repeated strokes darken quickly.
    active_density = np.maximum(alpha_acc - threshold, 0.0)
    alpha = 1.0 - np.exp(-density_gain * active_density)
    alpha = np.clip(alpha, 0.0, 1.0)
    color = np.zeros_like(color_acc, dtype=np.float32)
    nonzero = alpha_acc > 1e-6
    color[nonzero] = color_acc[nonzero] / alpha_acc[nonzero, None]
    output = background[:, :, :3] * (1.0 - alpha[:, :, None]) + color * alpha[:, :, None]
    rgba_out = np.dstack([np.clip(output, 0, 255), background[:, :, 3]])
    return Image.fromarray(rgba_out.astype(np.uint8), "RGBA")


def text_color(style: Style, muted: bool = False) -> str:
    if style.background == "#0b1020":
        return "#e5e7eb" if not muted else "#a5b4fc"
    return "#111827" if not muted else "#475569"


def render_style(points: list[dict], edges: list[dict], style: Style) -> Image.Image:
    canvas = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), rgba(style.background, 255))
    draw = ImageDraw.Draw(canvas)
    project = mapper(points, (90, 168, WIDTH - 90, HEIGHT - 250))
    max_abs_values = [float(row["max_embedding_abs"]) for row in points]
    max_abs_min = min(max_abs_values)
    max_abs_max = max(max_abs_values)

    title_font = font(39 * SCALE, True)
    sub_font = font(22 * SCALE)
    draw.text((78 * SCALE, 46 * SCALE), style.title, fill=text_color(style), font=title_font)
    draw.text(
        (78 * SCALE, 101 * SCALE),
        f"{SOURCE_STEM}: 1,024 points, 5,120 unit edges",
        fill=text_color(style, muted=True),
        font=sub_font,
    )

    visible_width = max(1, style.line_width * SCALE)
    density_width = max(visible_width, (style.line_width + style.density_width_boost) * SCALE)
    visible_alpha_acc = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    visible_color_acc = np.zeros((canvas.height, canvas.width, 3), dtype=np.float32)
    density_alpha_acc = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    density_color_acc = np.zeros((canvas.height, canvas.width, 3), dtype=np.float32)
    for edge in edges:
        p1 = project(float(edge["x1"]), float(edge["y1"]))
        p2 = project(float(edge["x2"]), float(edge["y2"]))
        fill = line_color(edge, style)
        accumulate_line(
            visible_alpha_acc,
            visible_color_acc,
            p1,
            p2,
            fill,
            width=visible_width,
        )
        accumulate_line(
            density_alpha_acc,
            density_color_acc,
            p1,
            p2,
            fill,
            width=density_width,
        )
    canvas = composite_accumulated_lines(
        canvas,
        visible_alpha_acc,
        visible_color_acc,
        density_gain=1.0,
        threshold=0.0,
    )
    canvas = composite_accumulated_lines(
        canvas,
        density_alpha_acc,
        density_color_acc,
        density_gain=style.density_gain,
        threshold=style.density_threshold,
    )
    draw = ImageDraw.Draw(canvas)

    radius = style.point_radius * SCALE
    for row in points:
        px, py = project(float(row["x"]), float(row["y"]))
        fill = point_color(row, style, max_abs_min, max_abs_max)
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=fill)

    note_font = font(20 * SCALE)
    footer_y = HEIGHT - 165
    footer = (
        f"{style.note}  line={style.line_width}px/{style.line_alpha} alpha; "
        f"density gain={style.density_gain:g}, threshold={style.density_threshold:g}; "
        f"point={style.point_radius}px/{style.point_alpha} alpha."
    )
    draw.text((78 * SCALE, footer_y * SCALE), footer, fill=text_color(style, muted=True), font=note_font)

    small_font = font(18 * SCALE)
    key_x = 78 * SCALE
    key_y = (footer_y + 42) * SCALE
    for i, color in enumerate(GENERATOR_PALETTE[:10]):
        x = key_x + (i % 5) * 175 * SCALE
        y = key_y + (i // 5) * 32 * SCALE
        draw.line((x, y + 12 * SCALE, x + 45 * SCALE, y + 12 * SCALE), fill=rgba(color, 210), width=4 * SCALE)
        draw.text((x + 55 * SCALE, y), f"u{i}", fill=text_color(style, muted=True), font=small_font)

    return canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert("RGB")


def make_contact_sheet(paths: list[Path]) -> None:
    images = [(path, Image.open(path).convert("RGB")) for path in paths]
    tile_w = WIDTH
    tile_h = HEIGHT
    label_h = 72
    gutter = 44
    margin = 44
    sheet_w = 2 * tile_w + 3 * margin
    sheet_h = 4 * (tile_h + label_h) + 5 * gutter
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#ffffff")
    draw = ImageDraw.Draw(sheet)
    label_font = font(34, True)
    for index, (path, image) in enumerate(images):
        col = index % 2
        row = index // 2
        x = margin + col * (tile_w + margin)
        y = gutter + row * (tile_h + label_h + gutter)
        draw.text((x, y), path.stem, fill="#111827", font=label_font)
        sheet.paste(image, (x, y + label_h))
    sheet.save(OUTDIR / "contact_sheet.png", quality=95)


def write_manifest(paths: list[Path]) -> None:
    with (OUTDIR / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "file",
            "source_stem",
            "line_mode",
            "line_width",
            "line_alpha",
            "point_mode",
            "point_radius",
            "point_alpha",
            "density_gain",
            "density_width_boost",
            "density_threshold",
            "note",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for style, path in zip(STYLES, paths):
            writer.writerow(
                {
                    "file": path.name,
                    "source_stem": SOURCE_STEM,
                    "line_mode": style.line_mode,
                    "line_width": style.line_width,
                    "line_alpha": style.line_alpha,
                    "point_mode": style.point_mode,
                    "point_radius": style.point_radius,
                    "point_alpha": style.point_alpha,
                    "density_gain": style.density_gain,
                    "density_width_boost": style.density_width_boost,
                    "density_threshold": style.density_threshold,
                    "note": style.note,
                }
            )


def write_readme(paths: list[Path]) -> None:
    table = [
        "| File | Lines | Points | Note |",
        "| --- | --- | --- | --- |",
    ]
    for style, path in zip(STYLES, paths):
        table.append(
            f"| `{path.name}` | `{style.line_mode}`, {style.line_width}px, alpha {style.line_alpha} | "
            f"`{style.point_mode}`, {style.point_radius}px, alpha {style.point_alpha}; "
            f"density {style.density_gain:g}, threshold {style.density_threshold:g} | {style.note} |"
        )
    text = f"""# Style Trials

These images reuse the same dataset:

```text
{SOURCE_DIR / (SOURCE_STEM + "_points.csv")}
{SOURCE_DIR / (SOURCE_STEM + "_edges.csv")}
```

Only the rendering changes: color palette, line width, edge alpha, point radius
and point alpha. The underlying points and unit-distance edges are identical.

## Contact Sheet

`contact_sheet.png` compares all variants at once.

## Variants

{chr(10).join(table)}
"""
    (OUTDIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    points = read_csv(SOURCE_DIR / f"{SOURCE_STEM}_points.csv")
    edges = read_csv(SOURCE_DIR / f"{SOURCE_STEM}_edges.csv")

    paths: list[Path] = []
    for style in STYLES:
        path = OUTDIR / f"{style.slug}.png"
        image = render_style(points, edges, style)
        image.save(path, quality=95)
        paths.append(path)
        print(f"Wrote {path}")

    make_contact_sheet(paths)
    write_manifest(paths)
    write_readme(paths)
    print(f"Style trials written to {OUTDIR}")


if __name__ == "__main__":
    main()
