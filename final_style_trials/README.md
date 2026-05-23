# Style Trials

These images reuse the same dataset:

```text
final_geometric_variations\05_random_representative_points.csv
final_geometric_variations\05_random_representative_edges.csv
```

Only the rendering changes: color palette, line width, edge alpha, point radius
and point alpha. The underlying points and unit-distance edges are identical.

## Contact Sheet

`contact_sheet.png` compares all variants at once.

## Variants

| File | Lines | Points | Note |
| --- | --- | --- | --- |
| `01_balanced_light.png` | `generator`, 1px, alpha 34 | `ink`, 4px, alpha 235; density 4.8, threshold 0.09 | Baseline: colored generators, compact dark points. |
| `02_fine_blueprint.png` | `blueprint`, 1px, alpha 24 | `steel`, 3px, alpha 220; density 8, threshold 0.08 | Thin low-alpha lines to emphasize the point cloud. |
| `03_high_contrast.png` | `charcoal`, 1px, alpha 30 | `black`, 5px, alpha 255; density 5.5, threshold 0.1 | Almost monochrome, intended for printed documentation. |
| `04_generator_ribbons.png` | `generator`, 2px, alpha 42 | `small_ink`, 3px, alpha 230; density 3.6, threshold 0.14 | Thicker colored edges expose the ten translation directions. |
| `05_soft_topographic.png` | `sage`, 1px, alpha 28 | `topographic`, 4px, alpha 235; density 7, threshold 0.09 | Point color follows max embedding radius; edges stay restrained. |
| `06_warm_cool.png` | `warm_cool`, 1px, alpha 36 | `cool_warm`, 4px, alpha 238; density 5.8, threshold 0.1 | Contrasts local directions with a cool-to-warm point scale. |
| `07_dark_neon.png` | `neon_generator`, 1px, alpha 54 | `neon`, 4px, alpha 245; density 5, threshold 0.13 | Presentation mode: high visibility on dark background. |
| `08_large_points_low_edges.png` | `mist`, 1px, alpha 16 | `large_gradient`, 6px, alpha 232; density 9, threshold 0.08 | Prioritizes point organization while retaining faint unit edges. |
