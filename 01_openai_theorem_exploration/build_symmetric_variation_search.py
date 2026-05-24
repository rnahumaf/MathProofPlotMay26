#!/usr/bin/env python3
"""
Search proof-aligned Stage 16 selections with high visual angular symmetry.

Run from WSL after activating Sage:

    source ~/miniforge3/etc/profile.d/conda.sh
    conda activate sage
    python build_symmetric_variation_search.py

The arithmetic engine is the same as the final Stage 16 gallery. The difference
is the selector: directions are compared modulo pi and fitted to regular
angular target sets, so the resulting projected meshes tend to be more
visually symmetric.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stage16_class_fiber_cm_final_plot_v3_1 as s16


OUTDIR = Path("symmetric_variation_search")
M = 24
SPLIT_PRIME_COUNT = 3
MAX_IDEAL_CHOICES = 300000
MAX_PLOT_EDGES = 22000

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
class SymmetricSpec:
    slug: str
    title: str
    count: int
    polydisc_radius: float
    phase_mode: str
    hidden_weight: float = 0.0
    phase_steps: int = 240
    notes: str = ""


SPECS = [
    SymmetricSpec(
        slug="01_regular6_phase_opt",
        title="Regular 6 - fase otimizada",
        count=6,
        polydisc_radius=4.0,
        phase_mode="optimized",
        notes="Seis direcoes quase igualmente espacadas modulo pi.",
    ),
    SymmetricSpec(
        slug="02_regular8_phase_opt",
        title="Regular 8 - fase otimizada",
        count=8,
        polydisc_radius=4.0,
        phase_mode="optimized",
        notes="Oito direcoes com erro angular minimo contra um alvo regular.",
    ),
    SymmetricSpec(
        slug="03_regular10_phase_opt",
        title="Regular 10 - fase otimizada",
        count=10,
        polydisc_radius=4.0,
        phase_mode="optimized",
        notes="Boa escala visual: aproximadamente mil pontos com simetria angular forte.",
    ),
    SymmetricSpec(
        slug="04_regular10_axis_locked",
        title="Regular 10 - eixo travado",
        count=10,
        polydisc_radius=4.0,
        phase_mode="axis_locked",
        notes="Forca um alvo alinhado ao eixo horizontal; util para composicao mais ortogonal.",
    ),
    SymmetricSpec(
        slug="05_regular10_tight_cut",
        title="Regular 10 - corte apertado",
        count=10,
        polydisc_radius=3.0,
        phase_mode="optimized",
        notes="Mesma busca angular com menos pontos para inspecao visual.",
    ),
    SymmetricSpec(
        slug="06_regular10_low_hidden",
        title="Regular 10 - baixa distorcao oculta",
        count=10,
        polydisc_radius=4.0,
        phase_mode="optimized",
        hidden_weight=0.16,
        notes="Equilibra simetria angular e menor tamanho nas demais imersoes.",
    ),
    SymmetricSpec(
        slug="07_regular12_phase_opt",
        title="Regular 12 - fase otimizada",
        count=12,
        polydisc_radius=4.0,
        phase_mode="optimized",
        notes="Mais denso; aumenta pares unitarios preservando alvo angular regular.",
    ),
    SymmetricSpec(
        slug="08_regular12_low_hidden",
        title="Regular 12 - baixa distorcao oculta",
        count=12,
        polydisc_radius=4.0,
        phase_mode="optimized",
        hidden_weight=0.14,
        notes="Versao densa com penalidade leve para evitar translacoes muito distorcidas.",
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


def direction_angle(row: dict) -> float:
    return float(row["angle"]) % math.pi


def period_distance(a: float, b: float, period: float = math.pi) -> float:
    diff = abs(a - b) % period
    return min(diff, period - diff)


def target_angles(count: int, phase: float) -> list[float]:
    step = math.pi / count
    return [(phase + i * step) % math.pi for i in range(count)]


def hidden_norm(row: dict, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return (float(row["max_abs_all_embeddings"]) - lo) / (hi - lo)


def select_for_phase(
    candidates: list[dict],
    count: int,
    phase: float,
    hidden_weight: float,
    hidden_lo: float,
    hidden_hi: float,
) -> tuple[list[dict], dict]:
    selected: list[dict] = []
    used = set()
    errors = []
    targets = target_angles(count, phase)

    for target in targets:
        best = None
        best_score = math.inf
        best_error = math.inf
        for row in candidates:
            key = row["u_key"]
            if key in used:
                continue
            error = period_distance(direction_angle(row), target)
            score = error + hidden_weight * hidden_norm(row, hidden_lo, hidden_hi)
            if score < best_score:
                best = row
                best_score = score
                best_error = error
        if best is None:
            break
        selected.append(best)
        used.add(best["u_key"])
        errors.append(best_error)

    if len(selected) != count:
        return [], {"phase": phase, "angular_rmse_deg": math.inf}

    dirs = sorted(direction_angle(row) for row in selected)
    gaps = []
    for i, angle in enumerate(dirs):
        nxt = dirs[(i + 1) % len(dirs)]
        if i == len(dirs) - 1:
            nxt += math.pi
        gaps.append(nxt - angle)

    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    expected_gap = math.pi / count
    gap_rmse = math.sqrt(sum((g - expected_gap) ** 2 for g in gaps) / len(gaps))
    score = rmse + 0.7 * gap_rmse

    selected.sort(key=direction_angle)
    metrics = {
        "phase": phase,
        "angular_rmse_deg": math.degrees(rmse),
        "max_angular_error_deg": math.degrees(max(errors)),
        "gap_rmse_deg": math.degrees(gap_rmse),
        "min_gap_deg": math.degrees(min(gaps)),
        "max_gap_deg": math.degrees(max(gaps)),
        "symmetry_score": score,
        "target_step_deg": math.degrees(expected_gap),
    }
    return selected, metrics


def select_regular_symmetric(candidates: list[dict], spec: SymmetricSpec) -> tuple[list[dict], dict]:
    candidates = sorted(candidates, key=direction_angle)
    hidden_values = [float(row["max_abs_all_embeddings"]) for row in candidates]
    hidden_lo = min(hidden_values)
    hidden_hi = max(hidden_values)

    if spec.phase_mode == "axis_locked":
        phases = [0.0]
    else:
        period = math.pi / spec.count
        phases = [period * i / spec.phase_steps for i in range(spec.phase_steps)]

    best_selected: list[dict] = []
    best_metrics: dict = {}
    best_score = math.inf
    for phase in phases:
        selected, metrics = select_for_phase(
            candidates,
            spec.count,
            phase,
            spec.hidden_weight,
            hidden_lo,
            hidden_hi,
        )
        if not selected:
            continue
        score = float(metrics["symmetry_score"])
        if score < best_score:
            best_score = score
            best_selected = selected
            best_metrics = metrics

    return best_selected, best_metrics


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


def color_for_generator(generator: int, alpha: int = 56) -> tuple[int, int, int, int]:
    color = PALETTE[generator % len(PALETTE)].lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def plot_symmetric(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, spec: SymmetricSpec) -> None:
    width, height = 1800, 1500
    image = Image.new("RGBA", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)

    draw.text((80, 48), spec.title, fill="#111827", font=font(40, True))
    subtitle = (
        f"Stage 16 CM, tc={summary['selected_translations']}, R={summary['polydisc_radius']}, "
        f"erro angular RMS={float(summary['angular_rmse_deg']):.3f} graus"
    )
    draw.text((80, 104), subtitle, fill="#475569", font=font(23))

    arr = point_array(point_rows)
    project = mapper(arr, (95, 180, 1705, 1180))
    edge_sample = sampled_edges(edge_rows, MAX_PLOT_EDGES)

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    edge_draw = ImageDraw.Draw(overlay)
    for edge in edge_sample:
        edge_draw.line(
            [
                project(float(edge["x1"]), float(edge["y1"])),
                project(float(edge["x2"]), float(edge["y2"])),
            ],
            fill=color_for_generator(int(edge.get("changed_generator", 0))),
            width=2,
        )
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)

    n = int(summary["distinct_points"])
    radius = 5 if n <= 300 else 4 if n <= 2500 else 3
    for x, y in arr:
        px, py = project(float(x), float(y))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill="#0f172a")

    facts = [
        spec.notes,
        f"pontos distintos: {summary['distinct_points']}",
        f"pares unitarios: {summary['unit_distance_pairs']}",
        f"razao vs grade: {float(summary['ratio_vs_grid']):.3f}x",
        f"gap angular alvo: {float(summary['target_step_deg']):.2f} graus",
        f"gap min/max: {float(summary['min_gap_deg']):.2f} / {float(summary['max_gap_deg']):.2f} graus",
        f"hidden_weight: {spec.hidden_weight}",
    ]
    y = 1228
    for item in facts:
        draw.text((80, y), item, fill="#334155", font=font(21))
        y += 32

    key_x = 1080
    key_y = 1228
    draw.text((key_x, key_y), "Arestas coloridas por translacao", fill="#334155", font=font(22, True))
    key_y += 38
    for j in range(int(summary["selected_translations"])):
        x = key_x + (j % 4) * 158
        y = key_y + (j // 4) * 32
        draw.line((x, y + 12, x + 38, y + 12), fill=color_for_generator(j, 220), width=5)
        draw.text((x + 48, y), f"u{j}", fill="#475569", font=font(18))

    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, quality=95)


def write_svg(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, spec: SymmetricSpec) -> None:
    arr = point_array(point_rows)
    width, height = 1200, 900
    project = mapper(arr, (40, 70, width - 40, height - 65))
    edge_sample = sampled_edges(edge_rows, 14000)
    meta = {
        "scheme": "stage16-cm-symmetric-search",
        "slug": spec.slug,
        "title": spec.title,
        "selected_translations": summary["selected_translations"],
        "points": summary["distinct_points"],
        "unit_distance_pairs": summary["unit_distance_pairs"],
        "angular_rmse_deg": summary["angular_rmse_deg"],
    }
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-scheme="stage16-cm-symmetric-search">',
        f"  <title>{escape(spec.title)}</title>",
        "  <metadata>" + escape(json.dumps(meta, ensure_ascii=False)) + "</metadata>",
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        f'  <text x="40" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">{escape(spec.title)}</text>',
        '  <g id="edges" stroke-width="0.75" stroke-linecap="round">',
    ]
    for edge in edge_sample:
        x1, y1 = project(float(edge["x1"]), float(edge["y1"]))
        x2, y2 = project(float(edge["x2"]), float(edge["y2"]))
        generator = int(edge.get("changed_generator", 0))
        color = PALETTE[generator % len(PALETTE)]
        parts.append(
            f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-opacity="0.24" data-generator="{generator}" '
            f'data-from="{edge["from_id"]}" data-to="{edge["to_id"]}"/>'
        )
    parts.extend(['  </g>', '  <g id="points" fill="#111827" fill-opacity="0.86">'])
    radius = 2.8 if len(point_rows) <= 2000 else 1.8
    for row in point_rows:
        x, y = project(float(row["x"]), float(row["y"]))
        parts.append(
            f'    <circle id="p{row["id"]}" cx="{x}" cy="{y}" r="{radius}" '
            f'data-mask="{row["mask"]}"/>'
        )
    parts.extend(["  </g>", "</svg>", ""])
    path.write_text("\n".join(parts), encoding="utf-8")


def selected_rows(selected: list[dict], metrics: dict) -> list[dict]:
    rows = []
    for index, row in enumerate(selected):
        rows.append(
            {
                "index": index,
                "mask": row["mask"],
                "angle": row["angle"],
                "direction_mod_pi": direction_angle(row),
                "principal_abs": row["principal_abs"],
                "max_abs_all_embeddings": row["max_abs_all_embeddings"],
                "u_key": row["u_key"],
                "phase": metrics["phase"],
            }
        )
    return rows


def write_readme(path: Path, rows: list[dict], global_meta: dict) -> None:
    table = [
        "| Variacao | Translacoes | R | Pontos | Pares | RMS angular | Gap min/max | Razao |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in rows:
        table.append(
            f"| `{row['slug']}.png` | {row['selected_translations']} | {row['polydisc_radius']} | "
            f"{row['distinct_points']} | {row['unit_distance_pairs']} | "
            f"{float(row['angular_rmse_deg']):.3f}° | "
            f"{float(row['min_gap_deg']):.2f}°/{float(row['max_gap_deg']):.2f}° | "
            f"{float(row['ratio_vs_grid']):.3f}x |"
        )

    text = f"""# Symmetric Variation Search

Esta pasta busca variacoes visualmente mais simetricas dentro da mesma familia
aritmetica Stage 16.

## Invariantes preservados

- Campo CM: `K = Q(zeta_{global_meta['m']})`
- Primos split: `{global_meta['split_primes']}`
- Fibra de classe: `{global_meta['largest_bucket_size']}` escolhas
- Translacoes de norma relativa 1: `u = alpha / c(alpha)`
- Pontos por somas centradas e corte por polidisco
- Arestas por troca de um bit, isto e, por somar uma translacao `u_j`

## Criterio de simetria

As direcoes das translacoes sao comparadas modulo `pi`, porque arestas
unitarias nao orientadas identificam `u` e `-u`. Para cada quantidade de
translacoes, testamos fases de um alvo angular regular e escolhemos o conjunto
com menor erro RMS contra esse alvo. Algumas variacoes incluem uma penalidade
leve por distorcao nas demais imersoes.

## Resultados

{chr(10).join(table)}

## Arquivos

Cada variacao contem `.png`, `.svg`, `_points.csv`, `_edges.csv`,
`_selected_u.csv` e `_summary.json`. `manifest.csv` resume a busca.
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
        selected, symmetry_metrics = select_regular_symmetric(translations, spec)
        if not selected:
            print(f"Skipped {spec.slug}: no selection")
            continue

        summary, data = s16.evaluate_selected(
            selected=selected,
            bucket_id=int(bucket["bucket_id"]),
            bucket_size=len(bucket["members"]),
            candidate_translation_count=len(translations),
            selection_method=f"symmetric_{spec.phase_mode}",
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
        summary["phase_mode"] = spec.phase_mode
        summary["hidden_weight"] = spec.hidden_weight
        summary["notes"] = spec.notes

        points = data["point_rows"]
        edges = data["edge_rows"]
        selected_detail_rows = selected_rows(data["selected"], symmetry_metrics)

        plot_symmetric(OUTDIR / f"{spec.slug}.png", points, edges, summary, spec)
        write_svg(OUTDIR / f"{spec.slug}.svg", points, edges, summary, spec)
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
    print(f"Symmetric variation search written to {OUTDIR}")


if __name__ == "__main__":
    main()
