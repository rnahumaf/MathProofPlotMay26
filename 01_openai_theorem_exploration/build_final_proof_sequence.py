#!/usr/bin/env python3
"""
Build the final proof-aligned visual sequence.

Run from WSL after activating Sage:

    source ~/miniforge3/etc/profile.d/conda.sh
    conda activate sage
    python build_final_proof_sequence.py

The script reuses the Stage 16 CM/ideal-class engine and writes a documented
finite visual gallery:

    final_proof_sequence/

The sequence is not a proof by itself. It is a faithful finite sample of the
construction pattern: split primes -> conjugate ideal choices -> class fiber ->
principal ratios -> norm-one translations -> centered polydisc -> projection.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stage16_class_fiber_cm_final_plot_v3_1 as s16


OUTDIR = Path("final_proof_sequence")
M = 24
SPLIT_PRIME_COUNT = 3
POLYDISC_RADIUS = 4.0
TRANSLATION_COUNTS = [4, 6, 8, 10, 12, 14]
MAX_IDEAL_CHOICES = 300000
MAX_PLOT_EDGES = 26000


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


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_value(value):
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


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


def plot_sequence_item(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict, step_index: int) -> None:
    width, height = 1800, 1500
    image = Image.new("RGBA", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    title = f"{step_index:02d}. Stage 16 CM - {summary['selected_translations']} translacoes de norma 1"
    subtitle = (
        f"K=Q(zeta_{summary['m']}), primos split={summary['split_primes']}, "
        f"pontos={summary['distinct_points']}, pares unitarios={summary['unit_distance_pairs']}"
    )
    draw.text((80, 54), title, fill="#111827", font=font(38, True))
    draw.text((80, 108), subtitle, fill="#475569", font=font(23))

    arr = point_array(point_rows)
    project = mapper(arr, (95, 180, 1705, 1190))

    edge_sample = sampled_edges(edge_rows, MAX_PLOT_EDGES)
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    edge_draw = ImageDraw.Draw(overlay)
    for edge in edge_sample:
        edge_draw.line(
            [
                project(float(edge["x1"]), float(edge["y1"])),
                project(float(edge["x2"]), float(edge["y2"])),
            ],
            fill=(37, 99, 235, 42),
            width=2,
        )
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)

    # Draw every point. Use a smaller radius for the dense final panels.
    n = int(summary["distinct_points"])
    radius = 5 if n <= 300 else 3 if n <= 5000 else 2
    for x, y in arr:
        px, py = project(float(x), float(y))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill="#111827")

    if len(edge_sample) < len(edge_rows):
        edge_note = f"arestas desenhadas: amostra visual de {len(edge_sample):,} / {len(edge_rows):,}"
    else:
        edge_note = f"arestas desenhadas: todas as {len(edge_rows):,}"
    draw.text((80, 1245), edge_note.replace(",", "."), fill="#64748b", font=font(22))

    facts = [
        f"fibra de classe: {summary['bucket_size']} escolhas de ideais",
        f"candidatas u/c(u): {summary['candidate_norm_one_translations']}",
        f"corte: polidisco max_sigma |x_sigma| <= {summary['polydisc_radius']}",
        f"grade comparavel: {summary['grid_unit_distance_pairs']} pares unitarios",
        f"razao contra grade: {float(summary['ratio_vs_grid']):.3f}x",
        f"erro numerico maximo nas arestas: {summary['numeric_max_edge_error']}",
    ]
    y = 1284
    for item in facts:
        draw.text((80, y), item, fill="#334155", font=font(21))
        y += 34

    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, quality=95)


def write_svg(path: Path, point_rows: list[dict], edge_rows: list[dict], summary: dict) -> None:
    arr = point_array(point_rows)
    width, height = 1200, 900
    project = mapper(arr, (40, 70, width - 40, height - 55))
    edge_sample = sampled_edges(edge_rows, 12000)
    meta = {
        "scheme": "stage16-cm-proof-sequence",
        "m": summary["m"],
        "split_primes": summary["split_primes"],
        "selected_translations": summary["selected_translations"],
        "points": summary["distinct_points"],
        "unit_distance_pairs": summary["unit_distance_pairs"],
        "edges_in_svg": len(edge_sample),
        "edge_sampling": len(edge_sample) < len(edge_rows),
    }
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-scheme="stage16-cm-proof-sequence">',
        "  <title>Stage 16 CM proof-aligned unit-distance graph</title>",
        "  <metadata>" + escape(json.dumps(meta, ensure_ascii=False)) + "</metadata>",
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        '  <text x="40" y="38" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">'
        + escape(f"Stage 16 CM: tc={summary['selected_translations']}, n={summary['distinct_points']}, e={summary['unit_distance_pairs']}")
        + "</text>",
        '  <g id="edges" stroke="#2563eb" stroke-opacity="0.22" stroke-width="0.8" stroke-linecap="round">',
    ]
    for edge in edge_sample:
        x1, y1 = project(float(edge["x1"]), float(edge["y1"]))
        x2, y2 = project(float(edge["x2"]), float(edge["y2"]))
        parts.append(
            f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'data-from="{edge["from_id"]}" data-to="{edge["to_id"]}" '
            f'data-generator="{edge.get("changed_generator", "")}" '
            f'data-distance="{float(edge.get("numeric_distance", 1.0)):.12f}"/>'
        )
    parts.extend(['  </g>', '  <g id="points" fill="#111827">'])
    radius = 2.6 if len(point_rows) <= 2000 else 1.6
    for row in point_rows:
        x, y = project(float(row["x"]), float(row["y"]))
        parts.append(
            f'    <circle id="p{row["id"]}" cx="{x}" cy="{y}" r="{radius}" '
            f'data-mask="{row["mask"]}" data-x="{float(row["x"]):.12f}" data-y="{float(row["y"]):.12f}"/>'
        )
    parts.extend(["  </g>", "</svg>", ""])
    path.write_text("\n".join(parts), encoding="utf-8")


def write_readme(path: Path, sequence_rows: list[dict], global_meta: dict) -> None:
    table_lines = [
        "| Arquivo | Translacoes | Pontos | Pares unitarios | Razao vs grade |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in sequence_rows:
        table_lines.append(
            f"| `{row['stem']}.png` | {row['selected_translations']} | "
            f"{row['distinct_points']} | {row['unit_distance_pairs']} | {float(row['ratio_vs_grid']):.3f}x |"
        )

    text = f"""# Sequencia final: amostra finita alinhada a prova

Esta pasta contem a melhor reproducao visual finita, dentro dos limites
computacionais locais, da construcao de muitos pares a distancia 1 inspirada
pela prova de 2026.

## Parametros aritmeticos

- Campo CM: `K = Q(zeta_{global_meta['m']})`
- Grau de `K`: `{global_meta['degree']}`
- Primos racionais que splitam completamente em `K`: `{global_meta['split_primes']}`
- Pares de ideais conjugados: `{global_meta['conjugate_pair_count']}`
- Escolhas de produto de ideais: `{global_meta['ideal_choices']}`
- Maior fibra de classe encontrada: `{global_meta['largest_bucket_size']}`
- Testes de razao principal bem-sucedidos: `{global_meta['principal_ratio_successes']}`
- Falhas de razao principal: `{global_meta['principal_ratio_failures']}`

## Tecnica

1. Trabalhamos em `K = Q(zeta_24)`, um campo CM.
2. Escolhemos primos `p == 1 mod 24`; por isso eles splitam completamente em
   `K`.
3. Para cada primo, os ideais primos acima dele sao pareados pela conjugacao
   CM.
4. Enumeramos escolhas de um ideal em cada par conjugado.
5. Agrupamos os produtos de ideais por fibra de classe usando testes de
   principialidade de razoes `I/I0`.
6. Para cada razao principal `(alpha) = I/I0`, construimos
   `u = alpha / c(alpha)`.
7. Cada `u` satisfaz exatamente `u*c(u)=1`; suas imagens complexas funcionam
   como translacoes unitarias.
8. A nuvem finita vem das somas centradas
   `sum_j (epsilon_j - 1/2) u_j`, cortadas pelo polidisco
   `max_sigma |x_sigma| <= 4`.
9. Projetamos para uma coordenada complexa e desenhamos as arestas obtidas por
   trocar um bit, isto e, por somar uma das translacoes unitarias.

Esta e uma amostra finita fiel ao mecanismo. Ela nao demonstra sozinha o
expoente assintotico; o papel da prova e mostrar que esse mecanismo pode ser
feito em uma familia infinita de campos com controle aritmetico.

## Sequencia crescente

{chr(10).join(table_lines)}

## Arquivos

Para cada passo existem:

- `.png`: figura de apresentacao;
- `.svg`: SVG estruturado com metadados em nos e arestas;
- `_points.csv`: pontos projetados;
- `_edges.csv`: arestas unitarias geradas pelas translacoes;
- `_selected_u.csv`: translacoes selecionadas, com angulo e norma nas imersoes;
- `_summary.json`: resumo da configuracao.

`manifest.csv` resume todos os passos.

## Observacao visual

As figuras densas amostram as arestas no PNG/SVG para manter legibilidade e
tamanho de arquivo. Os CSVs de arestas guardam a lista completa de pares
unitarios gerados para cada passo.
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

    sequence_rows: list[dict] = []
    for index, tc in enumerate(TRANSLATION_COUNTS, start=1):
        selected = s16.select_spread_by_angle(translations, tc)
        summary, data = s16.evaluate_selected(
            selected=selected,
            bucket_id=int(bucket["bucket_id"]),
            bucket_size=len(bucket["members"]),
            candidate_translation_count=len(translations),
            selection_method="angle",
            selection_attempt=0,
            polydisc_radius=POLYDISC_RADIUS,
            principal_radius=None,
            save_details=True,
        )
        if summary is None or data is None:
            continue
        summary.update(metadata)
        summary.update(cluster_stats)
        stem = f"{index:02d}_m{M}_spc{SPLIT_PRIME_COUNT}_tc{tc}_polyR4"
        summary["stem"] = stem

        points = data["point_rows"]
        edges = data["edge_rows"]
        selected_rows = []
        for j, row in enumerate(data["selected"]):
            selected_rows.append(
                {
                    "index": j,
                    "mask": row["mask"],
                    "angle": row["angle"],
                    "principal_abs": row["principal_abs"],
                    "max_abs_all_embeddings": row["max_abs_all_embeddings"],
                    "u_key": row["u_key"],
                }
            )

        plot_sequence_item(OUTDIR / f"{stem}.png", points, edges, summary, index)
        write_svg(OUTDIR / f"{stem}.svg", points, edges, summary)
        write_csv(OUTDIR / f"{stem}_points.csv", points, list(points[0].keys()))
        write_csv(OUTDIR / f"{stem}_edges.csv", edges, list(edges[0].keys()) if edges else ["from_id", "to_id"])
        write_csv(OUTDIR / f"{stem}_selected_u.csv", selected_rows, list(selected_rows[0].keys()))
        (OUTDIR / f"{stem}_summary.json").write_text(
            json.dumps({k: safe_value(v) for k, v in summary.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        sequence_rows.append({k: safe_value(v) for k, v in summary.items()})
        print(f"Wrote {stem}: n={summary['distinct_points']} edges={summary['unit_distance_pairs']}")

    manifest_fields = [
        "stem",
        "m",
        "split_primes",
        "selected_translations",
        "distinct_points",
        "unit_distance_pairs",
        "grid_unit_distance_pairs",
        "ratio_vs_grid",
        "avg_unit_neighbors_per_point",
        "polydisc_radius",
        "candidate_norm_one_translations",
        "bucket_size",
        "largest_bucket_size",
    ]
    write_csv(OUTDIR / "manifest.csv", sequence_rows, manifest_fields)
    write_readme(OUTDIR / "README.md", sequence_rows, global_meta)
    print(f"Final sequence written to {OUTDIR}")


if __name__ == "__main__":
    main()
