# n=25 / 70 Unit-Distance Investigation

This folder tests the conjecture:

> Among 25 points in the Euclidean plane, the maximum possible number of
> unit-distance pairs is 70.

## Current Status

The repository now has a rigorous **lower-bound certificate**:

- `n25_e70_exact_certificate.json` verifies, in `Q(sqrt(3))`, that the current
  25-point UCCS configuration has exactly 70 unit-distance pairs.
- `finite_uccs_upper_bound_top180.json` proves, inside the finite graph formed
  by the top 180 UCCS candidates, that no 25-point subset has more than 70
  unit-distance pairs.
- `counterexample_search_results.csv` records a parallel search across 15
  independent UCCS runs. It tested top-candidate universes
  `180, 220, 260, 320, 400`, with three seeds each, and found no `71+`
  example.

This proves:

```text
U(25) >= 70
```

It does **not** prove the global upper bound `U(25) <= 70`.

According to OEIS A186705 and the Alexeev-Mixon-Parshall small-point-set work,
the public exact table currently reaches `n=21`; `n=25` is therefore outside
the listed exact range. See: https://oeis.org/A186705

## What The Scripts Can Prove

`finite_uccs_upper_bound_top*.json` is a finite-universe certificate. If the
MILP solver reports success with zero MIP gap and optimum 70, it proves:

```text
No 25-point subset of that finite UCCS candidate graph has 71+ edges.
```

That is useful, but narrower than the global Euclidean problem.

## Latest Local Results

The latest local run used the machine's 16 logical processors via 15 worker
processes for the counterexample search:

| Test | Scope | Result |
| --- | --- | --- |
| Exact lower bound | `Q(sqrt(3))` certificate for the known 25-point set | `70` exact unit edges |
| Finite UCCS MILP | Top 180 UCCS candidates, solved by SciPy/HiGHS | optimum `70`, MIP gap `0.0` |
| Parallel search | 15 runs over top `180/220/260/320/400` candidates | best found `70`, no `71+` |

This is strong computational evidence that `70` is a natural barrier for this
UCCS family. It is not yet a proof that every possible planar 25-point
configuration has at most `70` unit distances.

## How To Re-run

```powershell
python .\n25_max70_investigation\investigate_n25_max70.py --all
```

Faster lower-bound-only check:

```powershell
python .\n25_max70_investigation\investigate_n25_max70.py --exact-lower-bound
```

Finite UCCS upper-bound check:

```powershell
python .\n25_max70_investigation\investigate_n25_max70.py --finite-uccs-upper-bound --top-candidates 180
```

Counterexample search:

```powershell
python .\n25_max70_investigation\investigate_n25_max70.py --counterexample-search --top-candidates-list 180,220,260
```

## Local Compute Policy

The script defaults to `os.cpu_count() - 1` workers. On the current machine that
means `15` workers out of `16` logical processors, leaving one logical processor
for Windows/Codex. Independent counterexample searches run in parallel worker
processes.

For the MILP finite-upper-bound check, the same worker count is forwarded to
HiGHS as a thread request. SciPy/HiGHS is CPU/RAM-bound here; the RTX GPU is not
used unless a future CUDA-capable solver backend is added.

## Global Proof Path

To prove `U(25)=70` globally, the next step is not another plot. It is a
computer-assisted extremal proof:

1. enumerate candidate 25-vertex graphs with at least 71 edges;
2. eliminate graphs that are not unit-distance embeddable;
3. prove that every remaining embeddable case is impossible.

The present folder prepares the lower-bound certificate and finite-family
upper-bound checks needed before attempting that larger enumeration.
