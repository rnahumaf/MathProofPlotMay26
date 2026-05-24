# Stage 5 — SageMath exact cyclotomic/CM unit-distance lab

This package advances the previous Python exploration toward exact algebraic verification.

It works with cyclotomic CM fields:

\[
K=\mathbb Q(\zeta_m)
\]

and points

\[
z=\sum_{j=0}^{\varphi(m)-1}a_j\zeta_m^j.
\]

The point set is selected by a hidden-embedding polydisc:

\[
\max_{k\ne1}|\sigma_k(z)|\le H
\]

and projected to the plane through the principal embedding:

\[
\sigma_1(z)\in\mathbb C\simeq\mathbb R^2.
\]

The important change is exact verification of unit-distance witnesses. A difference vector \(\Delta\) is accepted only if Sage verifies in `QQbar`:

\[
\alpha=\sum_j\Delta_j\zeta_m^j,\qquad \alpha\overline{\alpha}=1.
\]

So the exported edges are not merely numerical coincidences.

## Requirements

Run with SageMath:

```bash
sage -python stage5_sage_exact_cyclotomic.py --help
```

On Windows, the simplest path is usually WSL + SageMath.

## First run: reproduce the current best small case

```bash
sage -python stage5_sage_exact_cyclotomic.py \
  --m-values 24 \
  --coeff-bound 1 \
  --hidden-radii 3 3.5 4 4.5 5 \
  --principal-radii none \
  --outdir stage5_out_m24
```

Expected ballpark from the earlier non-Sage pipeline:

- best near `m=24`, `H=5`
- about `6389` points
- about `45120` unit-distance pairs
- ratio vs grid about `3.58x`

The exact Sage run should confirm the unit-delta witnesses algebraically.

## Try a focused search

```bash
sage -python stage5_sage_exact_cyclotomic.py \
  --m-values 15 24 30 \
  --coeff-bound 1 \
  --hidden-radii 3 3.5 4 4.5 5 \
  --principal-radii none \
  --outdir stage5_out_search
```

## Try principal-radius cuts

```bash
sage -python stage5_sage_exact_cyclotomic.py \
  --m-values 24 \
  --coeff-bound 1 \
  --hidden-radii 4 4.5 5 \
  --principal-radii none 3 4 5 \
  --outdir stage5_out_principal_cuts
```

## Larger experiments

Be careful with `--coeff-bound 2`.

The delta search grows as:

\[
(4C+1)^{\varphi(m)}.
\]

For example, `C=2`, `phi(m)=8` gives \(9^8=43,046,721\) possible deltas, which is large. The script skips cases above `--max-delta-box`.

You can override this if you are prepared for a long run:

```bash
sage -python stage5_sage_exact_cyclotomic.py \
  --m-values 24 \
  --coeff-bound 2 \
  --hidden-radii 5 6 7 \
  --max-delta-box 50000000 \
  --outdir stage5_out_big
```

## Files produced

Inside `--outdir`:

- `stage5_summary.csv`
- `best_..._points.csv`
- `best_..._exact_unit_deltas.csv`
- `best_..._unit_edges.csv`
- `best_..._comparison.png`

## What to send back

Please send back either:

1. the console output, especially the `Top configurations` block; or
2. `stage5_summary.csv`; or
3. the entire output folder zipped.

The next step after this is to move from cyclotomic fields to a more general Sage/PARI implementation with CM fields, ideals, and relative norm conditions.
