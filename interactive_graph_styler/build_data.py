#!/usr/bin/env python3
"""Build a browser-ready JS data snapshot for the interactive graph styler."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "graph_data.js"

SOURCES = [
    {
        "key": "final_blueprint_symmetric_variations",
        "label": "Final Blueprint symmetric variations",
        "path": ROOT / "final_blueprint_symmetric_variations",
    },
    {
        "key": "final_geometric_variations",
        "label": "Final geometric variations",
        "path": ROOT / "final_geometric_variations",
    },
    {
        "key": "symmetric_variation_search",
        "label": "Symmetric variation search",
        "path": ROOT / "symmetric_variation_search",
    },
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def compact_float(value: str) -> float:
    return round(float(value), 10)


def main() -> None:
    datasets = []
    sources = []

    for source in SOURCES:
        source_dir = source["path"]
        manifest_path = source_dir / "manifest.csv"
        if not manifest_path.exists():
            continue

        sources.append({"key": source["key"], "label": source["label"]})
        manifest = read_csv(manifest_path)

        for row in manifest:
            slug = row["slug"]
            points = read_csv(source_dir / f"{slug}_points.csv")
            edges = read_csv(source_dir / f"{slug}_edges.csv")
            point_payload = [
                [
                    int(point["id"]),
                    compact_float(point["x"]),
                    compact_float(point["y"]),
                    compact_float(point["max_embedding_abs"]),
                ]
                for point in points
            ]
            edge_payload = [
                [
                    int(edge["from_id"]),
                    int(edge["to_id"]),
                    int(edge["changed_generator"]),
                ]
                for edge in edges
            ]
            datasets.append(
                {
                    "slug": f"{source['key']}:{slug}",
                    "originalSlug": slug,
                    "source": source["key"],
                    "sourceLabel": source["label"],
                    "title": row["title"],
                    "selector": row.get("selector") or row.get("phase_mode") or "dataset",
                    "translations": int(row["selected_translations"]),
                    "polydiscRadius": float(row["polydisc_radius"]),
                    "points": len(points),
                    "edges": len(edges),
                    "ratioVsGrid": round(float(row["ratio_vs_grid"]), 6),
                    "notes": row.get("notes", ""),
                    "pointRows": point_payload,
                    "edgeRows": edge_payload,
                }
            )

    payload = {
        "source": "multiple",
        "sources": sources,
        "format": {
            "pointRows": ["id", "x", "y", "maxEmbeddingAbs"],
            "edgeRows": ["fromId", "toId", "generator"],
        },
        "datasets": datasets,
    }

    OUT.write_text(
        "window.GRAPH_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
