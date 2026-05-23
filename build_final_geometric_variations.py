#!/usr/bin/env python3
"""
Build representative geometric variations of the final CM construction.

Run from WSL after activating Sage:

    source ~/miniforge3/etc/profile.d/conda.sh
    conda activate sage
    python build_final_geometric_variations.py

The arithmetic data are kept fixed:

    Q(zeta_24) -> split primes -> conjugate ideal pairs -> class fiber ->
    principal ratios -> norm-one translations.

Only the visual organization changes: translation selection, polydisc cut and
edge coloring. This gives different planar structures inside the same finite
proof-aligned family.
"""

from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stage16_class_fiber_cm_final_plot_v3_1 as s16


OUTDIR = Path("final_geometric_variations")
M = 24
SPLIT_PRIME_COUNT = 3
MAX_IDEAL_CHOICES = 300000
MAX_PLOT_EDGES = 18000

PALETTE = [
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
class Variation:
    slug: str
    title: str
    selector: str
    translation_count: int
    polydisc_radius: float
    principal_radius: float | None = None
    seed: int = 0
    notes: str = ""


VARIATIONS = [
    Variation(
        slug="01_angular_spread_balanced",
        title="Distribuicao angular balanceada",
        selector="angle_spread",
        translation_count=10,
        polydisc_radius=4.0,
        notes="Translacoes espalhadas por angulo; referencia visual mais simetrica.",
    ),
    Variation(
        slug="02_angular_spread_tight_cut",
        title="Mesmo espalhamento, corte apertado",
        selector="angle_spread",
        translation_count=10,
        polydisc_radius=3.0,
        notes="Mesmas regras, menos pontos; deixa as camadas internas mais legiveis.",
    ),
    Variation(
        slug="03_sector_cluster",
        title="Translacoes em setor angular",
        selector="sector_cluster",
        translation_count=10,
        polydisc_radius=4.0,
        notes="Seleciona uma janela angular curta; tende a formar feixes e bandas.",
    ),
    Variation(
        slug="04_low_hidden_distortion",
        title="Baixa distorcao nas demais imersoes",
        selector="low_hidden_distortion",
        translation_count=10,
        polydisc_radius=4.0,
        notes="Prefere translacoes pequenas nas outras imersoes; costuma dar nuvens compactas.",
    ),
    Variation(
        slug="05_random_representative",
        title="Amostra aleatoria controlada",
        selector="random",
        translation_count=10,
        polydisc_radius=4.0,
        seed=20260523,
        notes="Mostra que a familia nao depende de uma unica escolha estetica.",
    ),
    Variation(
        slug="06_dense_angular_spread",
        title="Espalhamento angular denso",
        selector="angle_spread",
        translation_count=12,
        polydisc_radius=4.0,
        notes="Mais translacoes, mais pares unitarios e mais densidade visual.",
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


def safe_value(value):
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def point_array(point_rows: list[dict]) -> np.ndarray:
    return np.array([[float(row["x"]), float(row["y"])] for row in point_rows], dtype=float)


def mapper(values: np.ndarray, box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    min_x, min_y = values.min(axis=0)
    max_x, max_y = values.max(axis=0)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    min_x -= 0.12 * dx
    max_x += 0.12 * dx
    min_y -= 0.12 * dy
    max_y += 0.12 * dy
    scale = min((x1 - x0) / (max_x - min_x), (y1 - y0) / (max_y - min_y))
    cx_data = (min_x + max_x) / 2.0
    cy_data = (min_y + max_y) / 2.0
    cx_pix = (x0 + x1) / 2.0
    cy_pix = (y0 + y1) / 2.0

    def project(x: float, y: float) -> tuple[int, int]:
        return (
            int(round(cx_pix + (x - cx_data) * scale)),
            int(round(cy_pix - (y - cy_data) * scale)),
        )

    return project


def sampled_edges(edge_rows: list[dict], limit: int) -> list[dict]:
    if len(edge_rows) <= limit:
        return edge_rows
    idx = np.linspace(0, len(edge_rows) - 1, limit).astype(int)
    return [edge_rows[int(i)] for i in idx]


def cyclic_distance(a: float, b: float) -> float:
    diff = abs(a - b)
    return min(diff, 2 * math.pi - diff)


def select_sector_cluster(candidates: list[dict], count: int) -> list[dict]:
    ordered = sorted(candidates, key=lambda row: row["angle"])
    doubled = ordered + [{**row, "angle": row["angle"] + 2 * math.pi} for row in ordered]
    best_start = 0
    best_width = math.inf
    for start in range(len(ordered)):
        width = doubled[start + count - 1]["angle"] - doubled[start]["angle"]
        if width < best_width:
            best_width = width
            best_start = start
    selected = doubled[best_start : best_start + count]
    normalized = []
    for row in selected:
        original = dict(row)
        original["angle"] = original["angle"] % (2 * math.pi)
        normalized.append(original)
    normalized.sort(key=lambda row: row["angle"])
    return normalized


def select_low_hidden_distortion(candidates: list[dict], count: int) -> list[dict]:
    selected: list[dict] = []
    for row in sorted(candidates, key=lambda r: (float(r["max_abs_all_embeddings"]), float(r["principal_abs"]))):
        if all(cyclic_distance(float(row["angle"]), float(prev["angle"])) > 0.05 for prev in selected):
            selected.append(row)
        if len(selected) == count:
            break
    selected.sort(key=lambda row: row["angle"])
    return selected


def select_translations(candidates: list[dict], variation: Variation) -> list[dict]:
    if variation.selector == "angle_spread":
        return s16.select_spread_by_angle(candidates, variation.translation_count)
    if variation.selector == "sector_cluster":
        return select_sector_cluster(candidates, variation.translation_count)
    if variation.selector == "low_hidden_distortion":
        return select_low_hidden_distortion(candidates, variation.translation_count)
    if variation.selector == "random":
        rng = random.Random(variation.seed)
        return s16.select_random(candidates, variation.translation_count, rng)
    raise ValueError(f"Unknown selector: {variation.selector}")


def color_for_generator(generator: int) -> tuple[int, int, int, int]:
    color = PALETTE[generator % len(PALETTE)].lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4)) + (72,)


def plot_variation(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, variation: Variation) -> None:
    width, height = 1800, 1500
    image = Image.new("RGBA", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)

    draw.text((80, 48), variation.title, fill="#111827", font=font(40, True))
    subtitle = (
        f"Stage 16 CM em K=Q(zeta_{summary['m']}), selector={variation.selector}, "
        f"tc={summary['selected_translations']}, R={summary['polydisc_radius']}"
    )
    draw.text((80, 104), subtitle, fill="#475569", font=font(23))

    arr = point_array(point_rows)
    project = mapper(arr, (95, 180, 1705, 1180))
    edge_sample = sampled_edges(edge_rows, MAX_PLOT_EDGES)

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    edge_draw = ImageDraw.Draw(overlay)
    for edge in edge_sample:
        generator = int(edge.get("changed_generator", 0))
        edge_draw.line(
            [
                project(float(edge["x1"]), float(edge["y1"])),
                project(float(edge["x2"]), float(edge["y2"])),
            ],
            fill=color_for_generator(generator),
            width=2,
        )
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)

    n = int(summary["distinct_points"])
    radius = 5 if n <= 300 else 4 if n <= 2000 else 3
    max_abs = np.array([float(row["max_embedding_abs"]) for row in point_rows], dtype=float)
    lo = float(max_abs.min())
    hi = float(max_abs.max())
    span = max(hi - lo, 1e-9)
    for row, value in zip(point_rows, max_abs):
        px, py = project(float(row["x"]), float(row["y"]))
        t = (float(value) - lo) / span
        shade = int(round(34 + 120 * t))
        fill = (15, 23, 42, max(130, 235 - int(80 * t)))
        outline = (shade, shade + 20, min(255, shade + 80), 210)
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=fill, outline=outline)

    legend_x, legend_y = 82, 1228
    draw.text((legend_x, legend_y), variation.notes, fill="#334155", font=font(22))
    legend_y += 42
    facts = [
        f"pontos distintos: {summary['distinct_points']}",
        f"pares unitarios: {summary['unit_distance_pairs']}",
        f"razao vs grade: {float(summary['ratio_vs_grid']):.3f}x",
        f"fibra de classe: {summary['bucket_size']}",
        f"candidatas de norma 1: {summary['candidate_norm_one_translations']}",
    ]
    for item in facts:
        draw.text((legend_x, legend_y), item, fill="#475569", font=font(21))
        legend_y += 32

    key_x = 1030
    key_y = 1228
    draw.text((key_x, key_y), "Cores das arestas = translacao u_j", fill="#334155", font=font(22, True))
    key_y += 38
    for j in range(int(summary["selected_translations"])):
        x = key_x + (j % 4) * 170
        y = key_y + (j // 4) * 34
        color = color_for_generator(j)
        draw.line((x, y + 12, x + 42, y + 12), fill=color, width=5)
        draw.text((x + 52, y), f"u{j}", fill="#475569", font=font(19))

    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, quality=95)


def write_svg(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, variation: Variation) -> None:
    arr = point_array(point_rows)
    width, height = 1200, 900
    project = mapper(arr, (40, 70, width - 40, height - 65))
    edge_sample = sampled_edges(edge_rows, 14000)
    meta = {
        "scheme": "stage16-cm-geometric-variation",
        "variation": variation.slug,
        "selector": variation.selector,
        "m": summary["m"],
        "split_primes": summary["split_primes"],
        "selected_translations": summary["selected_translations"],
        "points": summary["distinct_points"],
        "unit_distance_pairs": summary["unit_distance_pairs"],
    }
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-scheme="stage16-cm-geometric-variation">',
        f"  <title>{escape(variation.title)}</title>",
        "  <metadata>" + escape(json.dumps(meta, ensure_ascii=False)) + "</metadata>",
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        f'  <text x="40" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">{escape(variation.title)}</text>',
        '  <g id="edges" stroke-width="0.75" stroke-linecap="round">',
    ]
    for edge in edge_sample:
        x1, y1 = project(float(edge["x1"]), float(edge["y1"]))
        x2, y2 = project(float(edge["x2"]), float(edge["y2"]))
        generator = int(edge.get("changed_generator", 0))
        color = PALETTE[generator % len(PALETTE)]
        parts.append(
            f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-opacity="0.28" data-generator="{generator}" '
            f'data-from="{edge["from_id"]}" data-to="{edge["to_id"]}"/>'
        )
    parts.extend(['  </g>', '  <g id="points" fill="#111827" fill-opacity="0.82">'])
    radius = 2.8 if len(point_rows) <= 2000 else 1.8
    for row in point_rows:
        x, y = project(float(row["x"]), float(row["y"]))
        parts.append(
            f'    <circle id="p{row["id"]}" cx="{x}" cy="{y}" r="{radius}" '
            f'data-mask="{row["mask"]}" data-max-embedding-abs="{float(row["max_embedding_abs"]):.12f}"/>'
        )
    parts.extend(["  </g>", "</svg>", ""])
    path.write_text("\n".join(parts), encoding="utf-8")


def selected_rows(selected: list[dict]) -> list[dict]:
    rows = []
    for index, row in enumerate(selected):
        rows.append(
            {
                "index": index,
                "mask": row["mask"],
                "angle": row["angle"],
                "principal_abs": row["principal_abs"],
                "max_abs_all_embeddings": row["max_abs_all_embeddings"],
                "u_key": row["u_key"],
            }
        )
    return rows


def write_readme(path: Path, rows: list[dict], global_meta: dict) -> None:
    table = [
        "| Variacao | Selector | Translacoes | R | Pontos | Pares unitarios | Razao vs grade |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        table.append(
            f"| `{row['slug']}.png` | `{row['selector']}` | {row['selected_translations']} | "
            f"{row['polydisc_radius']} | {row['distinct_points']} | {row['unit_distance_pairs']} | "
            f"{float(row['ratio_vs_grid']):.3f}x |"
        )

    text = f"""# Variacoes geometricas finais

Esta pasta mostra organizacoes visuais distintas dentro da mesma construcao
aritmetica finita usada na sequencia final.

## Invariantes preservados

- Campo CM: `K = Q(zeta_{global_meta['m']})`
- Primos split: `{global_meta['split_primes']}`
- Pares de ideais conjugados: `{global_meta['conjugate_pair_count']}`
- Maior fibra de classe: `{global_meta['largest_bucket_size']}`
- Translacoes construidas como `u = alpha / c(alpha)`, com `u*c(u)=1`
- Pontos construidos por somas centradas e corte por polidisco
- Arestas unitarias geradas por troca de um bit, isto e, por somar uma
  translacao `u_j`

## Variacoes

{chr(10).join(table)}

## Leitura visual

As cores das arestas indicam qual translacao `u_j` gerou o par unitario. Os
pontos mais escuros/claros refletem o tamanho maximo da soma centrada nas
imersoes complexas usadas no corte. Assim, a diferenca entre as figuras vem da
organizacao geometrica da mesma fonte aritmetica, nao de uma mudanca para uma
construcao aleatoria.

## Limite conceitual

Estas imagens sao amostras finitas fieis ao mecanismo da prova. Elas nao sao
uma reproducao completa do teorema assintotico, que afirma uma familia infinita
de conjuntos com `n` arbitrariamente grande e depende de controle de torres de
campos, discriminantes e classes.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    K, conj, embeddings, pair_blocks, metadata, factor_summary = s16.build_split_prime_pairs(
        M, SPLIT_PRIME_COUNT, verbose=True
    )
    products = s16.enumerate_product_ideals(K, pair_blocks, MAX_IDEAL_CHOICES)
    buckets, bucket_rows, cluster_stats = s16.cluster_by_principal_ratios(K, products, verbose=True)
    bucket = max(buckets, key=lambda b: len(b["members"]))
    translations = s16.make_norm_one_translation_rows(K, conj, embeddings, bucket)

    global_meta = {**metadata, **cluster_stats}
    (OUTDIR / "factor_summary.json").write_text(json.dumps(factor_summary, indent=2, default=str), encoding="utf-8")
    (OUTDIR / "bucket_summary.json").write_text(json.dumps(bucket_rows, indent=2, default=str), encoding="utf-8")

    manifest_rows: list[dict] = []
    for variation in VARIATIONS:
        selected = select_translations(translations, variation)
        summary, data = s16.evaluate_selected(
            selected=selected,
            bucket_id=int(bucket["bucket_id"]),
            bucket_size=len(bucket["members"]),
            candidate_translation_count=len(translations),
            selection_method=variation.selector,
            selection_attempt=variation.seed,
            polydisc_radius=variation.polydisc_radius,
            principal_radius=variation.principal_radius,
            save_details=True,
        )
        if summary is None or data is None:
            print(f"Skipped {variation.slug}: empty result")
            continue

        summary.update(metadata)
        summary.update(cluster_stats)
        summary["slug"] = variation.slug
        summary["title"] = variation.title
        summary["selector"] = variation.selector
        summary["notes"] = variation.notes

        points = data["point_rows"]
        edges = data["edge_rows"]
        selected_detail_rows = selected_rows(data["selected"])

        plot_variation(OUTDIR / f"{variation.slug}.png", points, edges, summary, variation)
        write_svg(OUTDIR / f"{variation.slug}.svg", points, edges, summary, variation)
        write_csv(OUTDIR / f"{variation.slug}_points.csv", points, list(points[0].keys()))
        write_csv(OUTDIR / f"{variation.slug}_edges.csv", edges, list(edges[0].keys()) if edges else ["from_id", "to_id"])
        write_csv(OUTDIR / f"{variation.slug}_selected_u.csv", selected_detail_rows, list(selected_detail_rows[0].keys()))
        (OUTDIR / f"{variation.slug}_summary.json").write_text(
            json.dumps({k: safe_value(v) for k, v in summary.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        manifest_row = {k: safe_value(v) for k, v in summary.items()}
        manifest_rows.append(manifest_row)
        print(
            f"Wrote {variation.slug}: n={summary['distinct_points']} "
            f"edges={summary['unit_distance_pairs']} ratio={float(summary['ratio_vs_grid']):.3f}x"
        )

    fields = [
        "slug",
        "title",
        "selector",
        "selected_translations",
        "polydisc_radius",
        "principal_radius",
        "distinct_points",
        "unit_distance_pairs",
        "grid_unit_distance_pairs",
        "ratio_vs_grid",
        "avg_unit_neighbors_per_point",
        "candidate_norm_one_translations",
        "bucket_size",
        "notes",
    ]
    write_csv(OUTDIR / "manifest.csv", manifest_rows, fields)
    write_readme(OUTDIR / "README.md", manifest_rows, global_meta)
    print(f"Final geometric variations written to {OUTDIR}")


if __name__ == "__main__":
    main()
