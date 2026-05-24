# n=25 Global Proof Search

This folder starts the upper-bound side of the conjecture:

```text
U(25) = 70
```

At this stage we still treat `70` as a conjectural universal maximum and a
confirmed computational record.

## Layer 1: Abstract Graph Filters

Any planar unit-distance graph must satisfy at least these graph conditions:

- no `K_{2,3}`, because two unit circles intersect in at most two points;
- no `K_4`, because four pairwise unit-distant points cannot exist in `R^2`;
- for every vertex `v`, the graph induced by `N(v)` must be a subgraph of
  unit chords on a circle, so every cycle component inside `N(v)` must be a
  hexagon.

The heuristic search shows that these necessary conditions are not enough:

| Filter | Best Abstract Graph Found |
| --- | ---: |
| `K_{2,3}`-free + `K_4`-free | 85 edges |
| plus local unit-circle neighborhood rule | 84 edges |

Files:

- `basic_relaxation_heuristic_best.json`
- `local_circle_relaxation_heuristic_best.json`
- `basic_relaxation_search.py`

Interpretation: a proof of `U(25) <= 70` needs stronger geometric elimination,
not just these local graph obstructions.

## Layer 2: Numerical Geometry Filter

`geometric_embedder.py` tries to solve the equations

```text
||p_i - p_j||^2 = 1
```

for every edge in a candidate graph. Nonedges are unconstrained, so a successful
near-zero, non-collapsed solution would be a genuine counterexample candidate.
Failure is numerical evidence only, not a proof.

Latest checks:

| Input Graph | Edge Count | Best Max Edge-Squared Error | Distinct? |
| --- | ---: | ---: | --- |
| known UCCS record | 70 | `2.22e-16` | no, edge-only solve collapsed vertices |
| local-circle abstract candidate | 84 | `6.61e-1` | yes, but far from unit-edge feasibility |

The exact non-collapsed certificate for the known 70-edge example remains
`../n25_max70_investigation/n25_e70_exact_certificate.json`.

## Layer 3: Candidate Pool

`collect_candidate_pool.py` generated a deduplicated pool of labelled abstract
candidates passing the local-circle filter:

```text
raw candidates: 600
isomorphism classes: 600
max edge count: 84
```

In this sample all candidates were non-isomorphic, so the search space is broad:
the final proof will need systematic generation, not just one obstruction.

Files:

- `candidate_pool/candidate_classes.csv`
- `candidate_pool/class_*.csv`
- `candidate_pool/candidate_pool_metadata.json`

## Layer 4: Batch Geometry Probe

`batch_geometric_probe.py` tested the top 20 candidate classes, with 30
least-squares starts per class:

```text
classes tested: 20
runs per class: 30
best class: 14
best edge count: 83
best max edge-squared error: 6.28e-1
```

No candidate in this batch came close to a real unit-distance embedding.

Files:

- `geometric_batch/batch_geometric_probe_summary.csv`
- `geometric_batch/batch_geometric_probe_metadata.json`

## Layer 5: Exact Triangle-Lattice Filter

Every unit-distance triangle is equilateral. When equilateral triangles share
an edge, their relative positions are forced on the triangular lattice. The
script `triangle_lattice_filter.py` checks this implication exactly on every
edge-connected triangle component.

Results:

| Input | Edge Count | Result |
| --- | ---: | --- |
| known UCCS record | 70 | passes |
| old local-circle candidate pool | 80-84 | 600/600 eliminated |

This is the first rigorous eliminator in the upper-bound direction: any class
eliminated here cannot be a planar unit-distance graph. It still does not close
the proof, because a new search constrained by this filter finds different
abstract candidates that survive it.

Files:

- `triangle_lattice_filter.py`
- `triangle_lattice_filter/triangle_lattice_filter_summary.csv`
- `triangle_lattice_filter/n25_e70_seed20270530_edges_triangle_lattice_result.json`

## Layer 6: Triangle-Filtered Frontier

`triangle_filtered_search.py` searches directly under the strongest exact
filters currently implemented:

- `K_{2,3}`-free;
- `K_4`-free;
- local unit-circle neighborhoods;
- exact triangle-lattice consistency.

Latest wide run:

```text
runs: 1000
steps: 320
best edge count: 82
runs with 71+ edges: 1000
```

So the triangle filter is powerful, but not sufficient. It rules out the first
pool and then exposes a sharper frontier of abstract graphs with 80-82 edges.
Numerically, these are still far from geometric realization:

```text
best 82-edge candidate: max edge-squared error about 6.34e-1
top 30 triangle-filtered classes: best max edge-squared error about 5.94e-1
```

Files:

- `triangle_filtered_search.py`
- `collect_triangle_filtered_pool.py`
- `triangle_filtered_search/triangle_filtered_best_edges.csv`
- `triangle_filtered_pool/candidate_classes.csv`
- `triangle_filtered_geometric_batch/batch_geometric_probe_summary.csv`

## Layer 7: Finite Trilateration Certificates

`trilateration_eliminator.py` handles candidates that can be generated from one
seed edge by repeatedly placing a new vertex adjacent to two already placed
vertices. Such a graph has only finitely many embeddings for that seed edge:
each step is an intersection of two unit circles.

Results on the current triangle-filtered pool:

```text
classes tested: 500
classes eliminated: 500
max search-tree width: 2
```

The known 70-edge UCCS record is not incorrectly rejected: it reports
`no_trilateration_order`, so this eliminator does not apply to it.

Files:

- `trilateration_eliminator.py`
- `trilateration_eliminator/class_*_trilateration_certificate.json`
- `trilateration_eliminator/trilateration_batch_summary.csv`

## Layer 8: Independent Verification

Three independent replay modes now exist for a trilateration certificate:

- `verify_trilateration_certificate.py`: high-precision numeric replay;
- `verify_trilateration_exact.py`: symbolic replay with `sympy` radicals;
- `verify_trilateration_interval.py`: conservative interval replay.

Sample certificates were checked with all three modes. The interval replay can
eliminate later than the finite certificate because it keeps conservative
interval branches alive longer; that is acceptable when it still proves final
elimination.

Verified samples:

```text
class_0001_e82: numeric verified, exact verified, interval verified
class_0002_e82: numeric verified
class_0024_e81: numeric verified
class_0500_e78: numeric verified, exact verified, interval verified
```

## Layer 9: Search After Trilateration

`search_after_trilateration.py` searches specifically for a hard survivor:
a `71+` edge candidate passing the exact local and triangle filters, but not
eliminated by finite trilateration.

Latest run:

```text
runs: 1000
steps: 260
best edge count found: 82
survivors after trilateration: 0
```

This is strong computational evidence for the current search regime, but still
not a universal proof. A proof of `U(25) <= 70` still needs either exhaustive
generation of all relevant abstract graphs or a theorem showing that any `71+`
unit-distance graph on 25 vertices must fall into one of the certified
elimination regimes.

Files:

- `search_after_trilateration.py`
- `post_trilateration_search/post_trilateration_runs.csv`
- `post_trilateration_search/post_trilateration_metadata.json`

## Layer 10: Non-Trilaterable Frontier

The known UCCS record with 70 edges is not finitely trilaterable. To test
whether `70` is forced by this obstruction, `non_trilaterable_maximality.py`
checks every one-edge extension of the known 70-edge graph while preserving the
current exact filters and non-trilaterability.

Result:

```text
base graph edges: 70
nonedges tested: 230
blocked by local filters: 212
surviving non-trilaterable one-edge extensions: 18
```

So the 70-edge graph is not locally maximal under the current abstract filters.
This identifies the real remaining proof gap: dense non-trilaterable abstract
graphs can pass all current local/triangle filters and still need a stronger
continuous geometric obstruction.

A perturbative search from the UCCS graph found denser abstract candidates:

```text
runs: 500
best non-trilaterable candidate passing exact filters: 80 edges
geometric least-squares best max edge-squared error: about 5.78e-1
```

These candidates are far from numerical realization, but they are not yet
eliminated by the finite certificate machinery.

Files:

- `non_trilaterable_maximality.py`
- `non_trilaterable_maximality/uccs_e70_non_trilaterable_maximality.json`
- `non_trilaterable_maximality/non_trilaterable_search_best_edges.csv`

## Layer 11: Derived Distance Labels

`distance_label_eliminator.py` adds another exact algebraic filter. Whenever
two vertices have exactly two common unit-neighbors, the opposite squared
distances satisfy:

```text
|ab|^2 + |cd|^2 = 4
```

This propagates forced squared-distance labels `1` and `3`. Fully labelled
quadruples must satisfy the planar Cayley-Menger determinant.

Result on the 500-class triangle-filtered pool:

```text
eliminated by exact distance labels/Cayley-Menger: 350
passed: 150
```

The best 80-edge non-trilaterable candidate passes this filter, so the frontier
now requires stronger continuous elimination.

Files:

- `distance_label_eliminator.py`
- `distance_label_eliminator/distance_label_batch_metadata.json`

## Layer 12: Numerical Core Search

`numerical_unsat_core.py` tries to shrink a hard candidate to a smaller
numerically infeasible core. This is exploratory only.

Current result:

```text
source candidate: 80 edges
candidate core: 57 edges on 25 vertices
stronger recheck best max edge-squared error: about 1.61e-1
```

This is not a certificate. It is a target for future exact or interval
elimination.

## Layer 13: Collision-Aware Forced-Edge Audit

`rigid_forced_edge_discovery.py` searches dense induced subcores for nonedges
whose squared distance is numerically invariant across many sampled embeddings.
These are candidate forced unit edges. Each candidate is then added to the full
80-edge non-trilaterable graph and checked by the exact eliminators.

The first version of this layer appeared to find 51 forced unit edges. A later
audit showed that those witnesses were contaminated by collapsed embeddings:
the unit equations were satisfied, but some vertices coincided. Since the unit
distance problem requires distinct points, those candidates cannot be used as a
proof.

Current collision-aware run:

```text
dense subcores tested: 40
minimum pair distance required: 1e-6
collapsed embedding rejections: 472
candidate forced unit edges: 0
```

A stricter rerun with minimum pair distance `1e-4` gave the same conclusion:
no forced unit candidates in the sampled dense subcores.

The old audit example was the candidate forced edge `2-3`:

```text
witness subcore: 12 vertices, 25 unit edges
rigidity rank: 21 = 2*12 - 3
rank after adding 2-3: still 21
full graph + edge 2-3: eliminated
trilateration certificate: verified numerically, exactly, and by interval replay
```

This remains useful as a diagnostic example, but it is no longer evidence for
`U(25) <= 70` because its sampled exact embeddings collapse vertices.

Files:

- `rigid_forced_edge_discovery.py`
- `distinct_geometric_embedder.py`
- `rigidity_closure_analyzer.py`
- `rigid_forced_edge_discovery/forced_edge_candidates.csv`
- `rigidity_closure_analyzer/rigidity_closure_summary.csv`
- `rigid_forced_edge_discovery/audit_forced_2_3_witness_edges.csv`
- `rigid_forced_edge_discovery/audit_forced_2_3_augmented_edges.csv`

Important status: this layer corrected the proof route. The next certificate
must either prove that the hard non-trilaterable candidates have no distinct
point realization, or derive a forced relation using only non-collapsed
realizations.

## Layer 14: Collision-Only Subcore Targets

`collision_forced_subcore_audit.py` searches the hard 80-edge candidate for
dense induced subcores whose unit equations are numerically easy to solve only
when vertices collapse. This is again a proof-search layer, not a proof.

Current run:

```text
dense subcores tested: 24
subcore size range: 10-12
best target: 12 vertices, 25 unit edges
exact-looking collapsed samples: 26/40
median minimum pair distance in exact-looking samples: about 2.58e-17
best distinct-penalty residual: about 1.82e-3
stable collision pairs at 95% support: 0
```

The absence of stable collision pairs means the obstruction is probably not a
single obvious equality `p_i = p_j` inside a small subcore. The hard case now
looks like a global compatibility problem between several almost-realizable
subcores.

The best target subcore was also checked by the existing exact filters:

```text
distance labels: passed, with only two derived squared distances equal to 3
trilateration: no finite trilateration order
triangle lattice: passed
```

Files:

- `collision_forced_subcore_audit.py`
- `collision_forced_subcore_audit/subcore_collision_summary.csv`
- `collision_forced_subcore_audit/subcore_collision_details.json`
- `collision_forced_subcore_audit/target_subcore_015_edges.csv`

## Commands

Basic abstract search:

```powershell
python .\n25_global_proof_search\basic_relaxation_search.py --runs 240 --steps 350
```

Local-circle abstract search:

```powershell
python .\n25_global_proof_search\basic_relaxation_search.py --runs 240 --steps 350 --require-local-circle
```

Numerical embeddability probe:

```powershell
python .\n25_global_proof_search\geometric_embedder.py --runs 120 --max-nfev 20000
```

Candidate pool:

```powershell
python .\n25_global_proof_search\collect_candidate_pool.py --runs 600 --steps 350
```

Batch geometry probe:

```powershell
python .\n25_global_proof_search\batch_geometric_probe.py --classes 20 --runs-per-class 30 --max-nfev 16000
```

Exact triangle-lattice filter:

```powershell
python .\n25_global_proof_search\triangle_lattice_filter.py --classes 600 --max-nodes 200000
python .\n25_global_proof_search\triangle_lattice_filter.py --edges .\uccs_square_stat_runs\n25_e70_seed20270530_edges.csv
```

Triangle-filtered search:

```powershell
python .\n25_global_proof_search\triangle_filtered_search.py --runs 1000 --steps 320 --max-nodes 100000
python .\n25_global_proof_search\collect_triangle_filtered_pool.py --runs 500 --steps 260 --min-edges 71
python .\n25_global_proof_search\batch_geometric_probe.py --pool .\n25_global_proof_search\triangle_filtered_pool --outdir .\n25_global_proof_search\triangle_filtered_geometric_batch --classes 30 --runs-per-class 30 --max-nfev 18000
```

Finite trilateration:

```powershell
python .\n25_global_proof_search\trilateration_eliminator.py --pool .\n25_global_proof_search\triangle_filtered_pool --classes 500 --max-states 200000 --precision 100 --tolerance 1e-40
python .\n25_global_proof_search\trilateration_eliminator.py --edges .\uccs_square_stat_runs\n25_e70_seed20270530_edges.csv
```

Certificate verification:

```powershell
python .\n25_global_proof_search\verify_trilateration_certificate.py --edges .\n25_global_proof_search\triangle_filtered_pool\class_0001_e82_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\class_0001_e82_trilateration_certificate.json
python .\n25_global_proof_search\verify_trilateration_exact.py --edges .\n25_global_proof_search\triangle_filtered_pool\class_0001_e82_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\class_0001_e82_trilateration_certificate.json
python .\n25_global_proof_search\verify_trilateration_interval.py --edges .\n25_global_proof_search\triangle_filtered_pool\class_0001_e82_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\class_0001_e82_trilateration_certificate.json
```

Search after trilateration:

```powershell
python .\n25_global_proof_search\search_after_trilateration.py --runs 1000 --steps 260 --max-nodes 100000 --max-states 200000 --precision 100 --tolerance 1e-40
```

Non-trilaterable frontier:

```powershell
python .\n25_global_proof_search\non_trilaterable_maximality.py --max-nodes 100000
python .\n25_global_proof_search\non_trilaterable_maximality.py --search --runs 500 --steps 180 --max-nodes 100000
```

Derived distance labels:

```powershell
python .\n25_global_proof_search\distance_label_eliminator.py --pool .\n25_global_proof_search\triangle_filtered_pool --classes 500
python .\n25_global_proof_search\distance_label_eliminator.py --edges .\n25_global_proof_search\non_trilaterable_maximality\non_trilaterable_search_best_edges.csv
```

Numerical core search:

```powershell
python .\n25_global_proof_search\numerical_unsat_core.py --threshold 0.35 --passes 1 --runs-per-score 2 --max-nfev 3000
python .\n25_global_proof_search\geometric_embedder.py --edges .\n25_global_proof_search\numerical_unsat_core\unsat_core_edges.csv --runs 240 --max-nfev 30000 --scale 4.0
```

Rigid forced-edge reduction:

```powershell
python .\n25_global_proof_search\rigid_forced_edge_discovery.py --min-size 10 --max-size 12 --subset-limit 40 --runs-per-subcore 50 --max-nfev 25000 --stable-tolerance 1e-8 --unit-tolerance 1e-7 --min-pair-distance 1e-6
python .\n25_global_proof_search\rigidity_closure_analyzer.py --runs 30 --max-nfev 25000 --rank-tolerance 1e-7
python .\n25_global_proof_search\verify_trilateration_certificate.py --edges .\n25_global_proof_search\rigid_forced_edge_discovery\audit_forced_2_3_augmented_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\audit_forced_2_3_augmented_edges_trilateration_certificate.json
python .\n25_global_proof_search\verify_trilateration_exact.py --edges .\n25_global_proof_search\rigid_forced_edge_discovery\audit_forced_2_3_augmented_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\audit_forced_2_3_augmented_edges_trilateration_certificate.json
python .\n25_global_proof_search\verify_trilateration_interval.py --edges .\n25_global_proof_search\rigid_forced_edge_discovery\audit_forced_2_3_augmented_edges.csv --certificate .\n25_global_proof_search\trilateration_eliminator\audit_forced_2_3_augmented_edges_trilateration_certificate.json
```

Collision-only subcore targets:

```powershell
python .\n25_global_proof_search\distinct_geometric_embedder.py --edges .\n25_global_proof_search\non_trilaterable_maximality\non_trilaterable_search_best_edges.csv --runs 240 --max-nfev 30000 --scale 4.0 --min-separation 0.05 --collision-weight 20
python .\n25_global_proof_search\collision_forced_subcore_audit.py --min-size 10 --max-size 12 --subset-limit 24 --exact-runs 40 --distinct-runs 40 --max-nfev 25000 --min-separation 0.05 --collision-weight 20
python .\n25_global_proof_search\distance_label_eliminator.py --edges .\n25_global_proof_search\collision_forced_subcore_audit\target_subcore_015_edges.csv
python .\n25_global_proof_search\trilateration_eliminator.py --edges .\n25_global_proof_search\collision_forced_subcore_audit\target_subcore_015_edges.csv --max-states 200000
python .\n25_global_proof_search\triangle_lattice_filter.py --edges .\n25_global_proof_search\collision_forced_subcore_audit\target_subcore_015_edges.csv
```

## Next Proof Step

The next rigorous layer is no longer the finitely trilaterable frontier; that
part is well covered by certificates. The old forced-edge route also cannot be
used unless it is made collision-aware. The remaining hard case is the
non-trilaterable frontier. The practical route is:

1. collect and classify non-trilaterable `71+` candidates passing all exact
   filters;
2. audit all numerical witnesses for vertex collisions before using them;
3. derive a global distinctness obstruction for the 80-edge candidate, or for a
   smaller compatibility core extracted from it;
4. turn that obstruction into an interval or algebraic certificate independent
   of least-squares numerics;
5. repeat over all non-isomorphic frontier candidates above 70 edges.

Only after that can `U(25) <= 70` be claimed as a universal proof.
