#!/usr/bin/env python3
"""Build the square-n comparison table and Blueprint chart."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTDIR = Path("square_method_comparison")

BLUEPRINT_BG = "#f8fafc"
BLUEPRINT_GRID = "#dbeafe"
BLUEPRINT_TEXT = "#111827"
BLUEPRINT_MUTED = "#64748b"
BLUEPRINT_BLUE = "#2563eb"
BLUEPRINT_RED = "#dc2626"
BLUEPRINT_GREEN = "#16a34a"
BLUEPRINT_PURPLE = "#7c3aed"
BLUEPRINT_GOLD = "#b45309"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


UCCS_RESULTS = [
    {"n": 16, "uccs": 40, "grid": 24, "erdos": 24, "runtime_seconds": 22.0},
    {"n": 25, "uccs": 70, "grid": 40, "erdos": 48, "runtime_seconds": 22.3},
    {"n": 36, "uccs": 111, "grid": 60, "erdos": 80, "runtime_seconds": 22.6},
    {"n": 49, "uccs": 161, "grid": 84, "erdos": 120, "runtime_seconds": 44.6},
    {"n": 64, "uccs": 217, "grid": 112, "erdos": 168, "runtime_seconds": 43.7},
    {"n": 81, "uccs": 285, "grid": 144, "erdos": 224, "runtime_seconds": 43.8},
    {"n": 100, "uccs": 359, "grid": 180, "erdos": 288, "runtime_seconds": 63.6},
    {"n": 121, "uccs": 441, "grid": 220, "erdos": 360, "runtime_seconds": 72.0},
    {"n": 144, "uccs": 530, "grid": 264, "erdos": 456, "runtime_seconds": 72.0},
    {"n": 169, "uccs": 617, "grid": 312, "erdos": 568, "runtime_seconds": 114.2},
    {"n": 196, "uccs": 702, "grid": 364, "erdos": 692, "runtime_seconds": 113.9},
    {"n": 225, "uccs": 810, "grid": 420, "erdos": 828, "runtime_seconds": 115.4},
    {"n": 256, "uccs": 954, "grid": 480, "erdos": 976, "runtime_seconds": 180.6},
    {"n": 289, "uccs": 1089, "grid": 544, "erdos": 1136, "runtime_seconds": 177.5},
    {"n": 324, "uccs": 1232, "grid": 612, "erdos": 1308, "runtime_seconds": 178.9},
    {"n": 361, "uccs": 1363, "grid": 684, "erdos": 1512, "runtime_seconds": 240.1},
    {"n": 400, "uccs": 1527, "grid": 760, "erdos": 1744, "runtime_seconds": 228.2},
]

# Optional fallback values if exact-n extraction has not been run yet.
OPENAI_LOCAL = {
}

# Current exact maximum values relevant to square n in this table.
# A186705/Alexeev-Mixon-Parshall list exact values through n=21, so n=16 is the
# only square in this comparison with a confirmed exact maximum.
PROVEN_MAX = {
    16: 41,
}


def fmt_optional(value: int | float | None, digits: int = 0) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and digits:
        return f"{value:.{digits}f}"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.3f}"
    return str(int(value))


def ratio(numerator: int | float | None, denominator: int | float) -> float | None:
    if numerator is None:
        return None
    return round(float(numerator) / float(denominator), 6)


def fmt_best_std(best: int | float | None, std: float | None) -> str:
    if best is None:
        return ""
    if std is None or std == 0:
        return fmt_optional(best)
    return f"{fmt_optional(best)} ± {std:.1f}"


def read_uccs_stats() -> dict[int, dict]:
    values = {
        item["n"]: {
            "best": item["uccs"],
            "mean": item["uccs"],
            "std": 0.0,
            "min": item["uccs"],
            "max": item["uccs"],
            "runtime_seconds": item["runtime_seconds"],
            "source": "provided_single_best",
        }
        for item in UCCS_RESULTS
    }
    path = Path("uccs_square_stat_runs") / "restart_summary_results.csv"
    if not path.exists():
        return values
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            n = int(row["n"])
            previous = values.get(n, {})
            previous_best = int(previous.get("best", 0))
            restart_best = int(row["best_edges"])
            values[n] = {
                "best": max(previous_best, restart_best),
                "mean": float(row["mean_restart_edges"]),
                "std": float(row["std_restart_edges"]),
                "min": int(row["min_restart_edges"]),
                "max": max(previous_best, int(row["max_restart_edges"])),
                "runtime_seconds": float(row["runtime_seconds"]),
                "source": "restart_distribution",
            }
    return values


def read_openai_exact_runs() -> dict[int, dict]:
    values = dict(OPENAI_LOCAL)
    path = Path("openai_square_exact_runs") / "summary_results.csv"
    if not path.exists():
        return values
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            n = int(row["n"])
            values[n] = {
                "best": int(row["best_edges"]),
                "mean": float(row.get("mean_edges") or row["best_edges"]),
                "std": float(row.get("std_edges") or 0.0),
                "min": int(row.get("min_edges") or row["best_edges"]),
                "max": int(row.get("max_edges") or row["best_edges"]),
                "source": "exact_n_induced_subgraph",
            }
    return values


def build_rows() -> list[dict]:
    openai_values = read_openai_exact_runs()
    uccs_values = read_uccs_stats()
    rows = []
    for item in UCCS_RESULTS:
        n = item["n"]
        grid = item["grid"]
        erdos = item["erdos"]
        uccs = uccs_values.get(n, {})
        openai = openai_values.get(n, {})
        proven = PROVEN_MAX.get(n)
        rows.append(
            {
                "n": n,
                "side": int(n**0.5),
                "simple_grid": grid,
                "simple_grid_std": 0.0,
                "openai_stage16_exact_best": openai.get("best"),
                "openai_stage16_exact_mean": openai.get("mean"),
                "openai_stage16_exact_std": openai.get("std", 0.0),
                "openai_stage16_exact_min": openai.get("min"),
                "openai_stage16_exact_max": openai.get("max"),
                "erdos_classic_lattice": erdos,
                "erdos_classic_lattice_std": 0.0,
                "uccs_best": uccs.get("best"),
                "uccs_mean": uccs.get("mean"),
                "uccs_std": uccs.get("std", 0.0),
                "uccs_min": uccs.get("min"),
                "uccs_max": uccs.get("max"),
                "proven_max": proven,
                "uccs_vs_grid": ratio(uccs.get("best"), grid),
                "uccs_vs_erdos": ratio(uccs.get("best"), erdos),
                "runtime_seconds": item["runtime_seconds"],
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "n",
        "side",
        "simple_grid",
        "openai_stage16_exact_best",
        "openai_stage16_exact_mean",
        "openai_stage16_exact_std",
        "openai_stage16_exact_min",
        "openai_stage16_exact_max",
        "erdos_classic_lattice",
        "uccs_best",
        "uccs_mean",
        "uccs_std",
        "uccs_min",
        "uccs_max",
        "proven_max",
        "uccs_vs_grid",
        "uccs_vs_erdos",
        "runtime_seconds",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt_optional(row[key], 3) if key != "n" and key != "side" else row[key] for key in fields})


def plot_chart(path: Path, rows: list[dict]) -> None:
    width, height = 1800, 1050
    image = Image.new("RGB", (width, height), BLUEPRINT_BG)
    draw = ImageDraw.Draw(image, "RGBA")
    left, top, right, bottom = 150, 145, 1660, 850
    xs_all = [row["n"] for row in rows]
    ys_all = []
    for row in rows:
        for key in ["simple_grid", "openai_stage16_exact_mean", "erdos_classic_lattice", "uccs_mean", "proven_max"]:
            if row[key] is not None:
                ys_all.append(row[key])
    min_x, max_x = min(xs_all), max(xs_all)
    min_y, max_y = 0, max(ys_all)
    max_y = int((max_y * 1.08 + 99) // 100 * 100)

    def project(x: float, y: float) -> tuple[int, int]:
        px = left + int(round((x - min_x) / (max_x - min_x) * (right - left)))
        py = bottom - int(round((y - min_y) / (max_y - min_y) * (bottom - top)))
        return px, py

    grid_color = (*hex_to_rgb(BLUEPRINT_GRID), 255)
    muted = (*hex_to_rgb(BLUEPRINT_MUTED), 255)
    text = (*hex_to_rgb(BLUEPRINT_TEXT), 255)
    for tick in range(0, max_y + 1, 250):
        _, y = project(min_x, tick)
        draw.line((left, y, right, y), fill=grid_color, width=1)
        draw.text((60, y - 11), str(tick), fill=muted, font=font(20))
    for row in rows:
        x, _ = project(row["n"], 0)
        draw.line((x, top, x, bottom), fill=(*hex_to_rgb(BLUEPRINT_GRID), 120), width=1)
        draw.text((x - 22, bottom + 20), str(row["n"]), fill=muted, font=font(17))

    draw.line((left, bottom, right, bottom), fill=muted, width=2)
    draw.line((left, top, left, bottom), fill=muted, width=2)
    draw.text((left, 48), "Comparacao de pares a distancia 1 em n = m^2 pontos", fill=text, font=font(36, True))
    draw.text((left, 94), "Linhas sem marcadores; sombras mostram 1 desvio padrao quando ha amostragem de runs/restarts.", fill=muted, font=font(22))
    draw.text((780, height - 78), "numero de pontos (n = m^2)", fill=muted, font=font(22))
    draw.text((32, 470), "pares", fill=muted, font=font(22))

    series = [
        ("Grade simples", "simple_grid", "simple_grid_std", BLUEPRINT_MUTED, "-"),
        ("OpenAI exact-n", "openai_stage16_exact_mean", "openai_stage16_exact_std", BLUEPRINT_PURPLE, "-"),
        ("Erdos classico", "erdos_classic_lattice", "erdos_classic_lattice_std", BLUEPRINT_GREEN, "-"),
        ("UCCS", "uccs_mean", "uccs_std", BLUEPRINT_BLUE, "-"),
    ]
    for label, key, std_key, color, _linestyle in series:
        data_rows = [row for row in rows if row[key] is not None]
        pts = [project(row["n"], row[key]) for row in data_rows]
        if not pts:
            continue
        rgb = hex_to_rgb(color)
        upper = []
        lower = []
        for row in data_rows:
            std = float(row.get(std_key) or 0.0)
            upper.append(project(row["n"], row[key] + std))
            lower.append(project(row["n"], max(0, row[key] - std)))
        if any(float(row.get(std_key) or 0.0) > 0 for row in data_rows):
            draw.polygon(upper + list(reversed(lower)), fill=(*rgb, 34))
        for a, b in zip(pts, pts[1:]):
            draw.line((*a, *b), fill=(*rgb, 225), width=4)

    proven_pts = [project(row["n"], row["proven_max"]) for row in rows if row["proven_max"] is not None]
    if len(proven_pts) >= 2:
        rgb = hex_to_rgb(BLUEPRINT_GOLD)
        for a, b in zip(proven_pts, proven_pts[1:]):
            draw.line((*a, *b), fill=(*rgb, 230), width=4)

    legend_x, legend_y = 1140, 170
    for label, _key, _std_key, color, _linestyle in series:
        rgb = hex_to_rgb(color)
        draw.line((legend_x, legend_y + 10, legend_x + 44, legend_y + 10), fill=(*rgb, 220), width=4)
        draw.text((legend_x + 58, legend_y - 2), label, fill=text, font=font(21))
        legend_y += 34

    image.save(path, quality=96)


def markdown_table(rows: list[dict]) -> str:
    lines = [
        "| n | Grade simples | OpenAI best | OpenAI media ± σ | Erdos classico | UCCS best | UCCS media ± σ | Maximo provado |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['n']} | {row['simple_grid']} | "
            f"{fmt_optional(row['openai_stage16_exact_best'])} | "
            f"{fmt_best_std(row['openai_stage16_exact_mean'], row['openai_stage16_exact_std'])} | "
            f"{row['erdos_classic_lattice']} | {fmt_optional(row['uccs_best'])} | "
            f"{fmt_best_std(row['uccs_mean'], row['uccs_std'])} | {fmt_optional(row['proven_max'])} |"
        )
    return "\n".join(lines)


def write_readme(path: Path, rows: list[dict]) -> None:
    text = f"""# Square Method Comparison

Comparacao para `n = m^2`, usando os resultados UCCS e OpenAI/Stage 16
disponiveis localmente.

![Comparacao Blueprint](comparison_blueprint.png)

No grafico, as linhas OpenAI e UCCS mostram a media das tentativas, e a sombra
mostra `±1` desvio padrao. A tabela tambem preserva o melhor valor conhecido.

## Colunas

- **Grade simples**: malha quadrada `m x m`, contando vizinhos horizontais e
  verticais.
- **OpenAI exact-n**: melhor subgrafo induzido de tamanho exatamente `n`,
  extraido do dataset Stage 16 Blueprint `09_regular12_balanced`. A sombra usa
  o desvio padrao entre seeds independentes da busca exact-n.
- **Erdos classico**: melhor distancia repetida em uma grade retangular com
  `n` pontos, depois reescalada para distancia 1.
- **UCCS**: Unit-Circle Closure Search, a sua busca por fecho de intersecoes de
  circulos unitarios. Quando `uccs_square_stat_runs/restart_summary_results.csv`
  existe, a sombra usa o desvio padrao dos melhores resultados por restart
  interno. Isso e diferente da trilha monotona de mensagens `novo melhor`.
- **Maximo provado**: valor exato conhecido. Entre os quadrados desta tabela,
  apenas `n=16` esta preenchido; `n=25` e os demais ficam em branco ate haver
  uma fonte de maximo exato.

## Tabela

{markdown_table(rows)}

## Leitura

UCCS melhora bastante a grade simples em todos os casos desta rodada. Em
valores baixos, ele tambem fica acima da coluna Erdos classico; a partir de
`n=225`, a grade de Erdos classica desta implementacao passa a superar a rodada
UCCS atual. A coluna OpenAI exact-n mostra uma comparacao concreta da familia
CM/Stage 16 em todos os mesmos quadrados, sem misturar os tamanhos naturais
completos da construcao com os subgrafos exact-n. Isso remove o pico artificial
que aparecia em `n=256`.

O valor `41` em `n=16` mostra que o resultado UCCS `40` esta a uma aresta do
maximo provado. Para `n=25`, nao foi preenchido maximo provado nesta tabela:
a fonte de referencia usada aqui lista maximos exatos ate `n=21`, entao `25`
nao deve ser tratado como resolvido sem outra citacao.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(OUTDIR / "comparison.csv", rows)
    plot_chart(OUTDIR / "comparison_blueprint.png", rows)
    write_readme(OUTDIR / "README.md", rows)
    print(f"Wrote {OUTDIR}")


if __name__ == "__main__":
    main()
