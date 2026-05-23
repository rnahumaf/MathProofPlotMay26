#!/usr/bin/env python3
"""
Build the final Blueprint-style symmetric Stage 16 gallery.

Run from WSL after activating Sage:

    source ~/miniforge3/etc/profile.d/conda.sh
    conda activate sage
    python build_blueprint_symmetric_gallery.py

This script keeps the arithmetic engine fixed and varies only parameters that
belong to the finite Stage 16 construction:

    - number of norm-one translations selected from the class fiber;
    - angular target symmetry;
    - polydisc radius;
    - optional hidden-embedding penalty.

The rendered PNGs use the Blueprint style selected as the default for the
interactive editor.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stage16_class_fiber_cm_final_plot_v3_1 as s16
from build_symmetric_variation_search import (
    SymmetricSpec,
    select_regular_symmetric,
    selected_rows,
)


OUTDIR = Path("final_blueprint_symmetric_variations")
M = 24
SPLIT_PRIME_COUNT = 3
MAX_IDEAL_CHOICES = 300000
MAX_PLOT_EDGES = 36000

BLUEPRINT_BG = "#f5f8fc"
BLUEPRINT_LINE = (37, 99, 235)
BLUEPRINT_POINT = "#0f172a"
BLUEPRINT_TEXT = "#111827"
BLUEPRINT_MUTED = "#64748b"


@dataclass(frozen=True)
class BlueprintSpec:
    slug: str
    title: str
    count: int
    polydisc_radius: float
    phase_mode: str = "optimized"
    hidden_weight: float = 0.0
    phase_steps: int = 300
    visual_shape: str = "regular"
    notes: str = ""


SPECS = [
    BlueprintSpec(
        slug="01_regular6_open",
        title="Blueprint Regular 6",
        count=6,
        polydisc_radius=4.0,
        visual_shape="hexagonal skeleton",
        notes="Smallest presentation layer: six symmetric directions and all 64 subset points.",
    ),
    BlueprintSpec(
        slug="02_regular8_open",
        title="Blueprint Regular 8",
        count=8,
        polydisc_radius=4.0,
        visual_shape="octagonal mesh",
        notes="Eight directions give a compact 256-point lattice-like figure.",
    ),
    BlueprintSpec(
        slug="03_regular10_compact",
        title="Blueprint Regular 10 Compact",
        count=10,
        polydisc_radius=3.0,
        visual_shape="tight decagonal mesh",
        notes="Same decagonal direction system with a tighter Minkowski polydisc cut.",
    ),
    BlueprintSpec(
        slug="04_regular10_balanced",
        title="Blueprint Regular 10 Balanced",
        count=10,
        polydisc_radius=4.0,
        visual_shape="balanced decagonal mesh",
        notes="Recommended medium-density presentation graph.",
    ),
    BlueprintSpec(
        slug="05_regular10_axis_locked",
        title="Blueprint Regular 10 Axis Locked",
        count=10,
        polydisc_radius=4.0,
        phase_mode="axis_locked",
        visual_shape="axis-aligned decagonal mesh",
        notes="Locks one regular target direction to the horizontal axis.",
    ),
    BlueprintSpec(
        slug="06_regular10_low_hidden",
        title="Blueprint Regular 10 Low Hidden",
        count=10,
        polydisc_radius=4.0,
        hidden_weight=0.16,
        visual_shape="low-hidden decagonal mesh",
        notes="Adds a light penalty for large values in the other complex embeddings.",
    ),
    BlueprintSpec(
        slug="07_regular11_balanced",
        title="Blueprint Regular 11",
        count=11,
        polydisc_radius=4.0,
        visual_shape="eleven-direction mesh",
        notes="Intermediate density between the 10- and 12-translation examples.",
    ),
    BlueprintSpec(
        slug="08_regular12_compact",
        title="Blueprint Regular 12 Compact",
        count=12,
        polydisc_radius=3.0,
        visual_shape="tight dodecagonal mesh",
        notes="Twelve directions with a tighter cut to reduce the central mass.",
    ),
    BlueprintSpec(
        slug="09_regular12_balanced",
        title="Blueprint Regular 12 Balanced",
        count=12,
        polydisc_radius=4.0,
        visual_shape="dense dodecagonal mesh",
        notes="Highest-density Blueprint variant kept in the default final gallery.",
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
    min_x -= 0.1 * dx
    max_x += 0.1 * dx
    min_y -= 0.1 * dy
    max_y += 0.1 * dy
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


def draw_blueprint(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, spec: BlueprintSpec) -> None:
    width, height = 1800, 1400
    image = Image.new("RGB", (width, height), BLUEPRINT_BG)
    draw = ImageDraw.Draw(image, "RGBA")

    draw.text((78, 56), spec.title, fill=BLUEPRINT_TEXT, font=font(42, True))
    subtitle = (
        f"{summary['slug']}: {summary['distinct_points']} points, "
        f"{summary['unit_distance_pairs']} unit edges, "
        f"angular RMS {float(summary['angular_rmse_deg']):.3f} deg"
    )
    draw.text((78, 104), subtitle, fill=BLUEPRINT_MUTED, font=font(23))

    arr = point_array(point_rows)
    project = mapper(arr, (72, 168, width - 72, height - 232))
    edge_sample = sampled_edges(edge_rows, MAX_PLOT_EDGES)

    for edge in edge_sample:
        draw.line(
            [
                project(float(edge["x1"]), float(edge["y1"])),
                project(float(edge["x2"]), float(edge["y2"])),
            ],
            fill=(*BLUEPRINT_LINE, 28),
            width=4,
        )
    for edge in edge_sample:
        draw.line(
            [
                project(float(edge["x1"]), float(edge["y1"])),
                project(float(edge["x2"]), float(edge["y2"])),
            ],
            fill=(*BLUEPRINT_LINE, 38),
            width=1,
        )

    n = int(summary["distinct_points"])
    radius = 4 if n <= 300 else 3 if n <= 2500 else 2
    for x, y in arr:
        px, py = project(float(x), float(y))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=BLUEPRINT_POINT)

    footer = (
        f"K=Q(zeta_{M}), split primes {summary['split_primes']}; "
        f"tc={summary['selected_translations']}, R={summary['polydisc_radius']}, "
        f"ratio vs grid={float(summary['ratio_vs_grid']):.3f}x"
    )
    draw.text((78, height - 86), footer, fill=BLUEPRINT_MUTED, font=font(20))
    draw.text((78, height - 50), spec.notes, fill=BLUEPRINT_MUTED, font=font(19))

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=96)


def spec_to_symmetric(spec: BlueprintSpec) -> SymmetricSpec:
    return SymmetricSpec(
        slug=spec.slug,
        title=spec.title,
        count=spec.count,
        polydisc_radius=spec.polydisc_radius,
        phase_mode=spec.phase_mode,
        hidden_weight=spec.hidden_weight,
        phase_steps=spec.phase_steps,
        notes=spec.notes,
    )


def write_readme(path: Path, rows: list[dict], global_meta: dict) -> None:
    table = [
        "| Variacao | Forma | Translacoes | R | Pontos | Pares | RMS angular | Razao |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        table.append(
            f"| `{row['slug']}.png` | {row['visual_shape']} | {row['selected_translations']} | "
            f"{row['polydisc_radius']} | {row['distinct_points']} | {row['unit_distance_pairs']} | "
            f"{float(row['angular_rmse_deg']):.3f} deg | {float(row['ratio_vs_grid']):.3f}x |"
        )

    text = f"""# Final Blueprint Symmetric Variations

Esta pasta e a galeria final em estilo Blueprint. Ela substitui a paleta
experimental colorida por uma linguagem unica: fundo claro azulado, linhas
azuis finas com acumulacao visual nas intersecoes e pontos escuros.

## Invariantes matematicos

Todas as figuras preservam o mesmo motor finito alinhado ao Stage 16:

- Campo CM: `K = Q(zeta_{global_meta['m']})`
- Primos split: `{global_meta['split_primes']}`
- Fibra de classe: `{global_meta['largest_bucket_size']}` escolhas
- Translacoes: `u = alpha / c(alpha)`, logo `u*c(u)=1`
- Pontos: somas centradas de translacoes, cortadas por um polidisco de Minkowski
- Arestas: troca de um bit, isto e, soma de uma das translacoes `u_j`
- Projecao final: uma coordenada complexa, identificada com o plano

## Parametros variados

A galeria varia somente parametros permitidos pela construcao finita:

- quantidade de translacoes de norma relativa 1;
- alvo angular regular modulo `pi`;
- raio do corte por polidisco;
- penalidade leve para controlar distorcao nas outras imersoes.

Isso muda a forma visual e o numero de pontos sem abandonar a familia
aritmetica usada na prova.

## Resultados

{chr(10).join(table)}

## Leitura visual recomendada

- `01` e `02`: figuras pequenas para explicar a regra de construcao.
- `03` a `06`: zona principal para apresentacao, com cerca de mil pontos.
- `07`: transicao para densidade maior.
- `08` e `09`: variantes densas, mantendo simetria angular forte.

## Arquivos

Cada variacao contem `.png`, `_points.csv`, `_edges.csv`, `_selected_u.csv` e
`_summary.json`. `manifest.csv` resume a colecao e e consumido pelo app
`interactive_graph_styler/`.
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

    manifest_rows = []
    for spec in SPECS:
        selected, symmetry_metrics = select_regular_symmetric(translations, spec_to_symmetric(spec))
        if not selected:
            print(f"Skipped {spec.slug}: no selection")
            continue

        summary, data = s16.evaluate_selected(
            selected=selected,
            bucket_id=int(bucket["bucket_id"]),
            bucket_size=len(bucket["members"]),
            candidate_translation_count=len(translations),
            selection_method=f"blueprint_{spec.phase_mode}",
            selection_attempt=0,
            polydisc_radius=spec.polydisc_radius,
            principal_radius=None,
            save_details=True,
        )
        if summary is None or data is None:
            print(f"Skipped {spec.slug}: empty result")
            continue

        summary.update(metadata)
        summary.update(cluster_stats)
        summary.update(symmetry_metrics)
        summary["slug"] = spec.slug
        summary["title"] = spec.title
        summary["selector"] = f"{spec.visual_shape}; {spec.phase_mode}"
        summary["phase_mode"] = spec.phase_mode
        summary["hidden_weight"] = spec.hidden_weight
        summary["visual_shape"] = spec.visual_shape
        summary["notes"] = spec.notes

        points = data["point_rows"]
        edges = data["edge_rows"]
        selected_detail_rows = selected_rows(data["selected"], symmetry_metrics)

        draw_blueprint(OUTDIR / f"{spec.slug}.png", points, edges, summary, spec)
        write_csv(OUTDIR / f"{spec.slug}_points.csv", points, list(points[0].keys()))
        write_csv(OUTDIR / f"{spec.slug}_edges.csv", edges, list(edges[0].keys()) if edges else ["from_id", "to_id"])
        write_csv(OUTDIR / f"{spec.slug}_selected_u.csv", selected_detail_rows, list(selected_detail_rows[0].keys()))
        (OUTDIR / f"{spec.slug}_summary.json").write_text(
            json.dumps({k: safe_value(v) for k, v in summary.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        manifest_row = {k: safe_value(v) for k, v in summary.items()}
        manifest_rows.append(manifest_row)
        print(
            f"Wrote {spec.slug}: n={summary['distinct_points']} "
            f"edges={summary['unit_distance_pairs']} "
            f"angular_rmse={float(summary['angular_rmse_deg']):.3f} deg"
        )

    fields = [
        "slug",
        "title",
        "selector",
        "visual_shape",
        "phase_mode",
        "hidden_weight",
        "selected_translations",
        "polydisc_radius",
        "distinct_points",
        "unit_distance_pairs",
        "grid_unit_distance_pairs",
        "ratio_vs_grid",
        "angular_rmse_deg",
        "max_angular_error_deg",
        "gap_rmse_deg",
        "min_gap_deg",
        "max_gap_deg",
        "target_step_deg",
        "symmetry_score",
        "candidate_norm_one_translations",
        "bucket_size",
        "notes",
    ]
    write_csv(OUTDIR / "manifest.csv", manifest_rows, fields)
    write_readme(OUTDIR / "README.md", manifest_rows, global_meta)
    print(f"Blueprint symmetric gallery written to {OUTDIR}")


if __name__ == "__main__":
    main()
