#!/usr/bin/env bash
set -euo pipefail

sage -python stage5_sage_exact_cyclotomic.py \
  --m-values 24 \
  --coeff-bound 1 \
  --hidden-radii 3 3.5 4 4.5 5 \
  --principal-radii none \
  --outdir stage5_out_m24
