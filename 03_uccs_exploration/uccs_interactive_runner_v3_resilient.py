#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UCCS — Unit-Circle Closure Search
Busca por Fecho Unitário para configurações densas de distância unitária.

Objetivo:
- Para cada n escolhido, gerar uma nuvem candidata por fecho de interseções de círculos unitários.
- Selecionar um subconjunto de n pontos maximizando pares a distância 1.
- Salvar incrementalmente:
  - PNG da melhor configuração
  - CSV das coordenadas
  - CSV das arestas unitárias
  - JSON de metadados
  - CSV-resumo acumulado para plotagem posterior

Requisitos:
    pip install matplotlib pandas

Uso:
    python uccs_interactive_runner.py

Observação:
- Threading aqui usa ThreadPoolExecutor. Como o trabalho é parcialmente CPU-bound, em CPython o ganho pode ser limitado.
- Para rodadas realmente pesadas, você pode trocar ThreadPoolExecutor por ProcessPoolExecutor.
- Mantive threads porque foi explicitamente solicitado, e porque o script também faz I/O e pode se beneficiar moderadamente.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


Point = Tuple[float, float]
Edge = Tuple[int, int]

TOL = 1e-7
SQRT3 = math.sqrt(3.0)

# Constantes geométricas recorrentes na família encontrada.
A = 1.0 - SQRT3 / 2.0          # 0.1339745962
B = 1.0 + SQRT3 / 2.0          # 1.8660254038
C = 1.0 + A                    # 1.1339745962

BLUEPRINT_BG = "#f8fafc"
BLUEPRINT_LINE = "#2563eb"
BLUEPRINT_POINT = "#0f172a"
BLUEPRINT_TEXT = "#111827"
BLUEPRINT_MUTED = "#64748b"


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


@dataclass
class RunParams:
    n: int
    closure_rounds: int
    top_candidates: int
    restarts: int
    steps: int
    seed: int
    bounds_padding: float
    output_dir: str


@dataclass
class RunResult:
    n: int
    best_edges: int
    mean_restart_edges: float
    std_restart_edges: float
    min_restart_edges: int
    max_restart_edges: int
    square_grid_edges: int
    erdos_lattice_edges: int
    ratio_vs_square: float
    ratio_vs_erdos: float
    candidate_count_raw: int
    candidate_count_filtered: int
    runtime_seconds: float
    closure_rounds: int
    top_candidates: int
    restarts: int
    steps: int
    seed: int
    points_csv: str
    edges_csv: str
    metadata_json: str
    png: str


@dataclass
class RunSampleSummary:
    n: int
    sample_count: int
    best_edges: int
    mean_edges: float
    std_edges: float
    min_edges: int
    max_edges: int
    square_grid_edges: int
    erdos_lattice_edges: int
    ratio_vs_square_best: float
    ratio_vs_erdos_best: float
    total_runtime_seconds: float
    output_dir: str


def dist(p: Point, q: Point) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def is_unit(p: Point, q: Point, tol: float = TOL) -> bool:
    return abs(dist(p, q) - 1.0) < tol


def same_point(p: Point, q: Point, tol: float = TOL) -> bool:
    return dist(p, q) < tol


def dedupe(points: Iterable[Point], tol: float = TOL) -> List[Point]:
    out: List[Point] = []
    for p in points:
        if not any(same_point(p, q, tol=tol) for q in out):
            out.append((float(p[0]), float(p[1])))
    return out


def unit_edges(points: Sequence[Point]) -> List[Edge]:
    return [
        (i, j)
        for i, j in itertools.combinations(range(len(points)), 2)
        if is_unit(points[i], points[j])
    ]


def circle_intersections(c1: Point, c2: Point, r: float = 1.0) -> List[Point]:
    x0, y0 = c1
    x1, y1 = c2
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)

    if d < 1e-9 or d > 2 * r + 1e-9:
        return []

    h2 = r * r - (d / 2.0) ** 2
    if h2 < -1e-9:
        return []

    h = math.sqrt(max(0.0, h2))
    xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx, ry = -dy / d, dx / d

    return [
        (xm + h * rx, ym + h * ry),
        (xm - h * rx, ym - h * ry),
    ]


def square_grid_edges_for_n(n: int) -> int:
    """
    Melhor retângulo inteiro a*b=n para adjacências simples.
    Para n quadrado, isso dá a malha m*m.
    Para n não fatorável em retângulo bom, usa melhor retângulo divisor.
    """
    best = 0
    for a in range(1, int(math.sqrt(n)) + 1):
        if n % a == 0:
            b = n // a
            edges = a * (b - 1) + b * (a - 1)
            best = max(best, edges)
    return best


def erdos_lattice_edges_rectangle(rows: int, cols: int) -> int:
    """
    Conta a maior multiplicidade de uma distância dentro da grade rows x cols.
    Depois essa distância seria reescalada para 1.
    """
    pts = [(float(x), float(y)) for y in range(rows) for x in range(cols)]
    counts: dict[int, int] = {}
    for i, j in itertools.combinations(range(len(pts)), 2):
        dx = int(pts[i][0] - pts[j][0])
        dy = int(pts[i][1] - pts[j][1])
        d2 = dx * dx + dy * dy
        counts[d2] = counts.get(d2, 0) + 1
    return max(counts.values()) if counts else 0


def erdos_lattice_edges_for_n(n: int) -> int:
    """
    Melhor grade retangular a*b=n, escolhendo a distância mais frequente.
    Para uma varredura mais agressiva, adaptar para shapes não retangulares.
    """
    best = 0
    for a in range(1, int(math.sqrt(n)) + 1):
        if n % a == 0:
            b = n // a
            best = max(best, erdos_lattice_edges_rectangle(a, b))
    return best


def seed_16_40() -> List[Point]:
    """
    Configuração explícita de 16 pontos / 40 pares encontrada na conversa.
    """
    return [
        (1.0, 1.0),
        (2.0, 1.0),
        (1.0, 2.0),
        (2.0, 2.0),
        (1.5, A),
        (2.5, A),
        (1.5, C),
        (2.5, C),
        (A, 1.5),
        (B, 1.5),
        (C, 1.5),
        (2.0 + SQRT3 / 2.0, 1.5),
        (1.5 - SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
        (1.5 + SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
        (2.5 - SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
        (2.5 + SQRT3 / 2.0, 1.5 - SQRT3 / 2.0),
    ]


def base_seed_for_n(n: int) -> List[Point]:
    """
    Semente genérica:
    - Para n pequeno/médio, replica a configuração 16/40 em deslocamentos locais.
    - O fecho por círculos unitários cria a nuvem candidata.
    """
    core = seed_16_40()

    translations: List[Point] = [(0.0, 0.0)]

    # Expansão retangular aproximada conforme n cresce.
    # Para n=16/21/25, poucas cópias já bastam; para n maiores, cresce.
    radius = max(1, int(math.ceil(math.sqrt(n) / 3.0)))

    for dx in range(-radius, radius + 2):
        for dy in range(-radius, radius + 2):
            if abs(dx) + abs(dy) <= radius + 1:
                translations.append((float(dx), float(dy)))

    # deslocamentos triangulares/equiláteros que ajudaram nos casos 16/21/25
    tri_shifts = [
        (0.5, SQRT3 / 2.0),
        (-0.5, SQRT3 / 2.0),
        (0.5, -SQRT3 / 2.0),
        (-0.5, -SQRT3 / 2.0),
    ]
    translations.extend(tri_shifts)

    seed: List[Point] = []
    for dx, dy in translations:
        seed.extend([(x + dx, y + dy) for x, y in core])

    return dedupe(seed)


def crop_bounds_for_seed(seed: Sequence[Point], padding: float) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in seed]
    ys = [p[1] for p in seed]
    return min(xs) - padding, max(xs) + padding, min(ys) - padding, max(ys) + padding


def build_closure_candidates(
    seed: Sequence[Point],
    rounds: int,
    bounds: Tuple[float, float, float, float],
    max_raw: int = 8000,
) -> List[Point]:
    xmin, xmax, ymin, ymax = bounds
    points = dedupe(seed)

    for r in range(rounds):
        pair_count = len(points) * (len(points) - 1) // 2
        print(f"[fecho] rodada {r + 1}/{rounds}: {len(points)} pontos; {pair_count} pares a testar", flush=True)
        raw = list(points)
        for p, q in itertools.combinations(points, 2):
            for z in circle_intersections(p, q):
                if xmin <= z[0] <= xmax and ymin <= z[1] <= ymax:
                    raw.append(z)
        points = dedupe(raw)
        print(f"[fecho] rodada {r + 1}/{rounds}: {len(points)} candidatos após deduplicação", flush=True)

        if len(points) > max_raw:
            # mantém os pontos de maior grau local aproximado para evitar explosão
            points = degree_filter(points, top_k=max_raw)

    return points


def degree_filter(points: Sequence[Point], top_k: int) -> List[Point]:
    if len(points) <= top_k:
        return list(points)

    deg = [0] * len(points)
    for i, j in itertools.combinations(range(len(points)), 2):
        if is_unit(points[i], points[j]):
            deg[i] += 1
            deg[j] += 1

    idx = sorted(range(len(points)), key=lambda i: deg[i], reverse=True)[:top_k]
    return [points[i] for i in idx]


def build_adjacency(points: Sequence[Point]) -> List[set[int]]:
    adj = [set() for _ in range(len(points))]
    for i, j in itertools.combinations(range(len(points)), 2):
        if is_unit(points[i], points[j]):
            adj[i].add(j)
            adj[j].add(i)
    return adj


def count_edges_set(adj: Sequence[set[int]], S: set[int]) -> int:
    return sum(len(adj[i] & S) for i in S) // 2


def delta_swap(adj: Sequence[set[int]], S: set[int], out: int, inn: int) -> int:
    W = S - {out}
    return len(adj[inn] & W) - len(adj[out] & W)


def search_best_subset(
    candidates: Sequence[Point],
    n: int,
    restarts: int,
    steps: int,
    seed: int,
) -> Tuple[int, List[Point], dict]:
    rng = random.Random(seed)
    adj = build_adjacency(candidates)
    N = len(candidates)

    if N < n:
        raise ValueError(f"Poucos candidatos: {N} candidatos para n={n}")

    all_nodes = set(range(N))
    degree_order = sorted(range(N), key=lambda i: len(adj[i]), reverse=True)

    bestS = set(degree_order[:n])
    bestE = count_edges_set(adj, bestS)
    restart_best_values: List[int] = []
    improvement_trace: List[dict] = []

    for restart in range(restarts):
        mode = restart % 5

        if mode == 0:
            pool = degree_order[: min(N, max(2 * n, 120))]
            S = set(rng.sample(pool, n))
        elif mode == 1:
            S = set(rng.sample(range(N), n))
        elif mode == 2:
            S = set(degree_order[:n])
            for _ in range(rng.randint(3, max(4, n // 2))):
                out = rng.choice(tuple(S))
                inn = rng.choice(tuple(all_nodes - S))
                S.remove(out)
                S.add(inn)
        else:
            pool = degree_order[: min(N, max(2 * n, 80))]
            S = set(rng.sample(pool, n))

        E = count_edges_set(adj, S)
        restart_best = E
        T = 1.2

        for _step in range(steps):
            out = rng.choice(tuple(S))
            available = list(all_nodes - S)
            sample = rng.sample(available, min(len(available), 24))

            if rng.random() < 0.85:
                W = S - {out}
                inn = max(sample, key=lambda i: len(adj[i] & W))
            else:
                inn = rng.choice(sample)

            dE = delta_swap(adj, S, out, inn)

            if dE >= 0 or rng.random() < math.exp(dE / max(T, 1e-9)):
                S.remove(out)
                S.add(inn)
                E += dE
                if E > restart_best:
                    restart_best = E

            T *= 0.996

            if E > bestE:
                bestS = set(S)
                bestE = E
                improvement_trace.append({"restart": restart, "edges": bestE})
                print(f"[n={n}] novo melhor: {bestE}", flush=True)

        restart_best_values.append(restart_best)

    mean_restart = sum(restart_best_values) / len(restart_best_values)
    variance = sum((value - mean_restart) ** 2 for value in restart_best_values) / len(restart_best_values)
    stats = {
        "restart_best_values": restart_best_values,
        "mean_restart_edges": round(mean_restart, 3),
        "std_restart_edges": round(math.sqrt(variance), 3),
        "min_restart_edges": min(restart_best_values),
        "max_restart_edges": max(restart_best_values),
        "improvement_trace": improvement_trace,
    }
    return bestE, [candidates[i] for i in bestS], stats


def save_points_csv(path: Path, points: Sequence[Point]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "x", "y"])
        for i, (x, y) in enumerate(points, 1):
            writer.writerow([i, f"{x:.12f}", f"{y:.12f}"])


def save_edges_csv(path: Path, edges: Sequence[Edge]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["i", "j"])
        for i, j in edges:
            writer.writerow([i + 1, j + 1])


def save_png(path: Path, points: Sequence[Point], edges: Sequence[Edge], title: str) -> None:
    width, height = 1500, 1500
    image = Image.new("RGB", (width, height), BLUEPRINT_BG)
    draw = ImageDraw.Draw(image, "RGBA")
    plot = (95, 150, width - 95, height - 95)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    dx = max(max_x - min_x, 1e-9)
    dy = max(max_y - min_y, 1e-9)
    min_x -= 0.12 * dx
    max_x += 0.12 * dx
    min_y -= 0.12 * dy
    max_y += 0.12 * dy
    scale = min((plot[2] - plot[0]) / (max_x - min_x), (plot[3] - plot[1]) / (max_y - min_y))
    cx_data = (min_x + max_x) / 2.0
    cy_data = (min_y + max_y) / 2.0
    cx_pix = (plot[0] + plot[2]) / 2.0
    cy_pix = (plot[1] + plot[3]) / 2.0

    def project(point: Point) -> tuple[int, int]:
        return (
            int(round(cx_pix + (point[0] - cx_data) * scale)),
            int(round(cy_pix - (point[1] - cy_data) * scale)),
        )

    line_rgb = hex_to_rgb(BLUEPRINT_LINE)
    for i, j in edges:
        draw.line((*project(points[i]), *project(points[j])), fill=(*line_rgb, 22), width=5)
    for i, j in edges:
        draw.line((*project(points[i]), *project(points[j])), fill=(*line_rgb, 42), width=1)

    point_radius = 7 if len(points) <= 64 else 5 if len(points) <= 144 else 4
    point_rgb = hex_to_rgb(BLUEPRINT_POINT)
    for point in points:
        x, y = project(point)
        draw.ellipse((x - point_radius, y - point_radius, x + point_radius, y + point_radius), fill=(*point_rgb, 230))

    if len(points) <= 64:
        muted_rgb = hex_to_rgb(BLUEPRINT_MUTED)
        for k, point in enumerate(points):
            x, y = project(point)
            draw.text((x + 9, y - 2), str(k + 1), fill=(*muted_rgb, 220), font=font(16))

    draw.text((85, 54), title, fill=hex_to_rgb(BLUEPRINT_TEXT), font=font(34, True))
    draw.text((85, 98), f"{len(points)} points, {len(edges)} unit-distance pairs", fill=hex_to_rgb(BLUEPRINT_MUTED), font=font(22))
    image.save(path, quality=96)


def append_summary_csv(path: Path, result: RunResult) -> None:
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(result).keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(result))


def run_one(params: RunParams) -> RunResult:
    start = time.time()
    outdir = Path(params.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\n[n={params.n}] Iniciando UCCS", flush=True)
    print(f"[n={params.n}] fecho=1 fixo, top_candidates={params.top_candidates}, restarts={params.restarts}, steps={params.steps}", flush=True)

    seed_points = base_seed_for_n(params.n)
    bounds = crop_bounds_for_seed(seed_points, params.bounds_padding)

    raw_candidates = build_closure_candidates(
        seed_points,
        rounds=params.closure_rounds,
        bounds=bounds,
    )

    # Para n grande, top_candidates precisa ser maior que n.
    # Caso contrário o algoritmo não consegue escolher n pontos.
    effective_top_candidates = max(params.top_candidates, params.n + max(30, params.n // 5))
    if effective_top_candidates != params.top_candidates:
        print(
            f"[n={params.n}] top_candidates={params.top_candidates} é menor que o necessário; "
            f"usando {effective_top_candidates}",
            flush=True,
        )

    filtered_candidates = degree_filter(raw_candidates, effective_top_candidates)

    print(f"[n={params.n}] candidatos brutos={len(raw_candidates)}, filtrados={len(filtered_candidates)}", flush=True)

    best_edges_count, best_points, search_stats = search_best_subset(
        filtered_candidates,
        n=params.n,
        restarts=params.restarts,
        steps=params.steps,
        seed=params.seed,
    )

    edges = unit_edges(best_points)
    assert len(edges) == best_edges_count

    square_edges = square_grid_edges_for_n(params.n)
    erdos_edges = erdos_lattice_edges_for_n(params.n)

    ratio_square = best_edges_count / square_edges if square_edges else float("nan")
    ratio_erdos = best_edges_count / erdos_edges if erdos_edges else float("nan")

    stamp = f"n{params.n}_e{best_edges_count}_seed{params.seed}"
    points_csv = outdir / f"{stamp}_points.csv"
    edges_csv = outdir / f"{stamp}_edges.csv"
    metadata_json = outdir / f"{stamp}_metadata.json"
    png = outdir / f"{stamp}.png"

    save_points_csv(points_csv, best_points)
    save_edges_csv(edges_csv, edges)
    save_png(
        png,
        best_points,
        edges,
        title=f"UCCS — n={params.n}, unit-distance pairs={best_edges_count}",
    )

    runtime = time.time() - start

    result = RunResult(
        n=params.n,
        best_edges=best_edges_count,
        mean_restart_edges=float(search_stats["mean_restart_edges"]),
        std_restart_edges=float(search_stats["std_restart_edges"]),
        min_restart_edges=int(search_stats["min_restart_edges"]),
        max_restart_edges=int(search_stats["max_restart_edges"]),
        square_grid_edges=square_edges,
        erdos_lattice_edges=erdos_edges,
        ratio_vs_square=ratio_square,
        ratio_vs_erdos=ratio_erdos,
        candidate_count_raw=len(raw_candidates),
        candidate_count_filtered=len(filtered_candidates),
        runtime_seconds=runtime,
        closure_rounds=params.closure_rounds,
        top_candidates=effective_top_candidates,
        restarts=params.restarts,
        steps=params.steps,
        seed=params.seed,
        points_csv=str(points_csv),
        edges_csv=str(edges_csv),
        metadata_json=str(metadata_json),
        png=str(png),
    )

    metadata = {
        "result": asdict(result),
        "params": asdict(params),
        "points": [{"index": i + 1, "x": p[0], "y": p[1]} for i, p in enumerate(best_points)],
        "edges": [{"i": i + 1, "j": j + 1} for i, j in edges],
        "search_stats": search_stats,
        "bounds": bounds,
        "technique": "Unit-Circle Closure Search (UCCS) / Busca por Fecho Unitário",
        "formula": "S_{k+1} = S_k ∪ I(S_k), where I(S_k) are unit-circle intersections.",
    }

    metadata_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    append_summary_csv(outdir / "summary_results.csv", result)

    print(f"[n={params.n}] Concluído: {best_edges_count} pares em {runtime:.1f}s", flush=True)
    print(f"[n={params.n}] PNG: {png}", flush=True)

    return result


def run_samples_for_n(base_params: RunParams, sample_count: int) -> RunSampleSummary:
    sample_outdir = Path(base_params.output_dir) / f"n{base_params.n}"
    sample_outdir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    results = []
    for sample_index in range(sample_count):
        params = RunParams(
            n=base_params.n,
            closure_rounds=base_params.closure_rounds,
            top_candidates=base_params.top_candidates,
            restarts=base_params.restarts,
            steps=base_params.steps,
            seed=base_params.seed + sample_index * 1009,
            bounds_padding=base_params.bounds_padding,
            output_dir=str(sample_outdir / f"sample_{sample_index:02d}"),
        )
        results.append(run_one(params))

    values = [result.best_edges for result in results]
    mean_edges = sum(values) / len(values)
    variance = sum((value - mean_edges) ** 2 for value in values) / len(values)
    std_edges = math.sqrt(variance)
    best_result = max(results, key=lambda result: result.best_edges)
    summary = RunSampleSummary(
        n=base_params.n,
        sample_count=sample_count,
        best_edges=max(values),
        mean_edges=round(mean_edges, 3),
        std_edges=round(std_edges, 3),
        min_edges=min(values),
        max_edges=max(values),
        square_grid_edges=best_result.square_grid_edges,
        erdos_lattice_edges=best_result.erdos_lattice_edges,
        ratio_vs_square_best=round(best_result.best_edges / best_result.square_grid_edges, 6),
        ratio_vs_erdos_best=round(best_result.best_edges / best_result.erdos_lattice_edges, 6),
        total_runtime_seconds=round(time.time() - start, 3),
        output_dir=str(sample_outdir),
    )
    summary_path = sample_outdir / "sample_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "summary": asdict(summary),
                "samples": [asdict(result) for result in results],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary


def write_sample_summary_csv(path: Path, summaries: Sequence[RunSampleSummary]) -> None:
    if not summaries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(summaries[0]).keys()))
        writer.writeheader()
        for summary in summaries:
            writer.writerow(asdict(summary))


def parse_n_list(text: str) -> List[int]:
    """
    Aceita:
      16
      16,21,25
      16 21 25
      16-36
      squares:4-10  => 16,25,36,...,100
    """
    text = text.strip().lower()

    if text.startswith("squares:"):
        rest = text.split(":", 1)[1]
        a, b = rest.split("-", 1)
        return [m * m for m in range(int(a), int(b) + 1)]

    if "-" in text and "," not in text and " " not in text:
        a, b = text.split("-", 1)
        return list(range(int(a), int(b) + 1))

    parts = text.replace(",", " ").split()
    return [int(p) for p in parts]


def choose_int(prompt: str, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    requested = default if not raw else int(raw)
    value = requested
    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    if value != requested:
        print(f"Valor {requested} ajustado para {value}.", flush=True)
    return value


def interactive_main() -> None:
    print("=" * 72)
    print("UCCS — Unit-Circle Closure Search")
    print("Busca por Fecho Unitário para pares de distância unitária")
    print("=" * 72)
    print()
    print("Escolha n ou um grupo de n.")
    print("Exemplos:")
    print("  16")
    print("  16,21,25,36")
    print("  16 21 25 36")
    print("  16-30")
    print("  squares:4-10    # 16,25,36,...,100")
    print()

    ns = parse_n_list(input("n ou grupo de n: "))
    ns = sorted(set(ns))

    print(f"\nValores de n: {ns}")
    print()
    print("Sugestão de processos:")
    print("  1 = mais estável")
    print("  2 = bom equilíbrio")
    print("  3-4 = usa mais CPU, pode competir por memória")
    print()

    threads = choose_int("Número de processos", default=min(4, max(1, os.cpu_count() or 1)), min_value=1, max_value=4)

    print()
    print("Parâmetros úteis para mexer:")
    print("  Top candidatos por grau: 180-300 para n pequeno; para n grande será ajustado automaticamente para ser maior que n.")
    print("  Restarts: 100-300 para teste rápido; 1000+ para rodada séria.")
    print("  Steps: 300-700 para teste rápido; 700+ para rodada séria.")
    print("  Amostras externas: repete a busca completa com seeds diferentes para medir variação.")
    print()
    print("O fecho geométrico fica fixo em 1 rodada.")
    print("Isso evita explosão de memória e mantém o experimento comparável entre n.")
    print()

    closure_rounds = 1
    top_candidates = choose_int("Top candidatos por grau", default=180, min_value=30)
    restarts = choose_int("Restarts por n", default=500, min_value=1)
    steps = choose_int("Steps por restart", default=600, min_value=1)
    sample_count = choose_int("Amostras externas por n", default=1, min_value=1)
    base_seed = choose_int("Seed base", default=20260523)
    padding = float(input("Padding dos bounds [0.35]: ").strip() or "0.35")
    output_dir = input("Pasta de saída [uccs_runs]: ").strip() or "uccs_runs"

    params_list: List[RunParams] = []
    for idx, n in enumerate(ns):
        params_list.append(
            RunParams(
                n=n,
                closure_rounds=closure_rounds,
                top_candidates=top_candidates,
                restarts=restarts,
                steps=steps,
                seed=base_seed + idx,
                bounds_padding=padding,
                output_dir=output_dir,
            )
        )

    print("\nIniciando execuções...")
    print(f"Saída: {Path(output_dir).resolve()}")
    print()

    results: List[RunResult] = []
    sample_summaries: List[RunSampleSummary] = []

    if sample_count > 1:
        for params in params_list:
            sample_summaries.append(run_samples_for_n(params, sample_count))
    elif threads == 1:
        for params in params_list:
            results.append(run_one(params))
    else:
        with ProcessPoolExecutor(max_workers=threads) as executor:
            future_to_n = {executor.submit(run_one, params): params.n for params in params_list}
            for future in as_completed(future_to_n):
                n = future_to_n[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    print(f"[n={n}] ERRO: {exc}", flush=True)
                    print(f"[n={n}] A execução dos outros n continuará.", flush=True)

    print()
    print("=" * 72)
    print("Resumo final")
    print("=" * 72)
    if sample_summaries:
        write_sample_summary_csv(Path(output_dir) / "sample_summary_results.csv", sample_summaries)
        for r in sorted(sample_summaries, key=lambda x: x.n):
            print(
                f"n={r.n:>4} | UCCS best={r.best_edges:>5} | "
                f"mean={r.mean_edges:>7.2f} | std={r.std_edges:>6.2f} | "
                f"grade={r.square_grid_edges:>5} | erdos={r.erdos_lattice_edges:>5}"
            )
        print()
        print(f"Resumo CSV de amostras: {Path(output_dir) / 'sample_summary_results.csv'}")
    else:
        for r in sorted(results, key=lambda x: x.n):
            print(
                f"n={r.n:>4} | UCCS={r.best_edges:>5} | "
                f"grade={r.square_grid_edges:>5} | erdos={r.erdos_lattice_edges:>5} | "
                f"ratio grade={r.ratio_vs_square:.3f} | tempo={r.runtime_seconds:.1f}s"
            )
        print()
        print(f"Resumo CSV acumulado: {Path(output_dir) / 'summary_results.csv'}")
    print()


if __name__ == "__main__":
    interactive_main()
