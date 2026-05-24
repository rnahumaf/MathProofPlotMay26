# n=25 Global Proof Search

This folder starts the upper-bound side of the conjecture:

```text
U(25) = 70
```

At this stage we still treat `70` as a conjectural universal maximum and a
confirmed computational record.

## Current Status

This README is currently tracking a proof-search route toward the upper-bound
side of the conjecture:

```text
U(25) <= 70
```

The global statement is not proved yet. The active work is focused on a hard
non-trilaterable obstruction extracted from the current frontier.

### Active target

The current active target is the reduced 18-edge core extracted from
`subcore_021`:

```text
1-2 1-4 1-6 1-10
2-3 2-11
3-9 3-11
4-8 4-9 4-10 4-11
6-7 6-8
7-8 7-9
8-11
9-10
```

The current target edge is:

```text
3-11
```

Removing `3-11` gives a 17-edge core with exact numerical realizations. The
observed exact branches force:

```text
|3-11|^2 = 0
or
|3-11|^2 = 3
```

No observed exact branch realizes `|3-11|^2 = 1`.

### Current proof gap

The latest collision-partition enumeration of the 17-edge core confirmed that
the two observed branches are present in the exhaustive partition list. The
remaining local gaps are:

```text
1. eliminate or certify the 620 unresolved collision partitions;
2. classify already_unit_edge_in_quotient branches as degenerate;
3. exclude the fully distinct/singleton realization case.
```

### Estimated progress

```text
Local certificate for the reduced 18-edge core:        ~70-80%
Local certificate for subcore_021:                     ~60-75%
Reusable elimination pipeline for hard subcores:       ~45-55%
Global proof over the full n25 search frontier:        ~25-35%
Formal/publication-grade proof with no computational gaps: ~15-25%
```

These percentages are qualitative working estimates, not mathematical
probabilities.

### Next planned command

Apply triangle filtering to the `620` unresolved quotient partitions from the
final 17-edge core enumeration. If any survive, apply distance-label and
trilateration filters only to those survivors.

## Progress Timeline

This section is the compact operational timeline. Detailed evidence remains in
Layers 1-17 below.

### Current high-level estimate

```text
Local certificate for the reduced 18-edge core:        ~70-80%
Local certificate for subcore_021:                     ~60-75%
Reusable elimination pipeline for hard subcores:       ~45-55%
Global proof over the full n25 search frontier:        ~25-35%
Formal/publication-grade proof with no computational gaps: ~15-25%
```

These percentages are qualitative working estimates, not mathematical
probabilities.

### Completed milestones

```text
Layers 1-9:
  Built the abstract, numerical, triangle-lattice, and finite-trilateration
  filters. The finitely trilaterable frontier is well covered by certificates.

Layers 10-14:
  Identified the non-trilaterable frontier as the hard remaining regime.
  Corrected the old forced-edge route after discovering collapsed witnesses.
  Switched to collision-aware subcore targets.

Layer 15:
  Found subcore_021 as the strongest hard local target.
  Found critical edge 3-12.
  Removing 3-12 gives exact degenerate branches.
  Observed branches force |3-12|^2 = 0 or 3, never 1.
  Certified the observed d2_0 and d2_3 quotient branches.

Layer 16:
  Enumerated collision quotients for subcore_021 - {3-12}.
  Closed the unresolved qV<=8 quotient class by triangle filtering.
  Extended to qV=9..11 and reduced the last survivor to a smaller core.

Layer 17:
  Reduced the last survivor from 23 edges to an 18-edge core.
  Found that the 18-edge core is numerically edge-critical.
  Removing target edge 3-11 gives exact degenerate branches.
  Observed branches force |3-11|^2 = 0 or 3, never 1.
  Certified the observed d2_0 and d2_3 quotient branches.
  Confirmed both observed branches in the active-vertex collision-partition
  enumeration of the 17-edge core.
```

### Remaining gaps

```text
Reduced 18-edge core:
  1. Eliminate or certify the 620 unresolved collision partitions of the
     17-edge core after reinserting 3-11.
  2. Classify already_unit_edge_in_quotient branches as degenerate branches.
  3. Exclude the fully distinct/singleton realization case.

subcore_021:
  4. Lift the reduced-core obstruction back to the final high-block survivor.
  5. Lift the survivor obstruction back to subcore_021.

global frontier:
  6. Reuse the pipeline over remaining hard subcores.
  7. Produce reproducible certificates and a final audit table.
```

## Active Commands

These commands are the most relevant to the current Layer 17 frontier.
Historical commands from earlier layers are preserved in the next section.

Recheck the reduced 18-edge core with the existing exact filters:

```powershell
python .\n25_global_proof_search\subcore_021_final_greedy_core_exact_filters.py
```

Audit the distance forced by removing the current target edge `3-11`:

```powershell
python .\n25_global_proof_search\subcore_021_final_core_remove_3_11_distance_audit.py
```

Extract and certify the observed collision quotient branches of the final core:

```powershell
python .\n25_global_proof_search\subcore_021_final_core_collision_quotients.py
```

Enumerate collision partitions for the 17-edge core obtained by removing
`3-11`:

```powershell
python .\n25_global_proof_search\subcore_021_final_core_collision_partition_enumeration.py
```

Current next step:

```text
Apply triangle filtering to the 620 unresolved quotient partitions from:

n25_global_proof_search\subcore_021_final_core_collision_partition_enumeration\final_core_unique_quotient_graphs.csv
```

If survivors remain after triangle filtering, apply `distance_label_eliminator.py`
and `trilateration_eliminator.py` only to those survivors.

## Layer 1: Abstract Graph Filters

Any planar unit-distance graph must satisfy at least these graph conditions:

- no `K_{2,3}`, because two unit circles intersect in at most two points;
- no `K_4`, because four pairwise unit-distant points cannot exist in `R^2`;
- for every vertex `v`, the graph induced by `N(v)` must be a subgraph of
  unit chords on a circle, so every cycle component inside `N(v)` must be a
  hexagon.

The heuristic search shows that these necessary conditions are not enough:

| Filter                                   | Best Abstract Graph Found |
| ---------------------------------------- | ------------------------: |
| `K_{2,3}`-free + `K_4`-free              |                  85 edges |
| plus local unit-circle neighborhood rule |                  84 edges |

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

| Input Graph                     | Edge Count | Best Max Edge-Squared Error | Distinct?                               |
| ------------------------------- | ---------: | --------------------------: | --------------------------------------- |
| known UCCS record               |         70 |                  `2.22e-16` | no, edge-only solve collapsed vertices  |
| local-circle abstract candidate |         84 |                   `6.61e-1` | yes, but far from unit-edge feasibility |

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

| Input                           | Edge Count | Result             |
| ------------------------------- | ---------: | ------------------ |
| known UCCS record               |         70 | passes             |
| old local-circle candidate pool |      80-84 | 600/600 eliminated |

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

## Layer 15: Collision-Quotient Certificate for `subcore_021`

A stronger local obstruction was found inside the hard non-trilaterable
frontier.

The best hard target is `subcore_021`, a 12-vertex, 25-edge induced subcore.
A direct numerical probe remained bounded away from zero residual:

```text
best exact-probe residual: about 1.24e-1
triangle lattice filter: passed
distance-label filter: passed
finite trilateration: no order
```

Single-edge ablation showed that removing edge `3-12` makes the system exactly
solvable numerically:

```text
subcore_021 - {3-12}: exact numerical realizations found
subcore_021: no exact realization found
```

Auditing the removed pair over exact numerical realizations of the 24-edge core
showed only two observed branches:

```text
|3-12|^2 = 0
|3-12|^2 = 3
|3-12|^2 = 1 was never observed
```

Collision-quotient extraction gave two simple quotient branches.

### Branch `d2_0`

```text
Q1 = (1,5,8,9)
Q2 = (2,11)
Q3 = (3,6,10,12)
Q4 = (4,7)
```

The target pair `3-12` maps to `Q3-Q3`, hence becomes a loop. Reinserting
`3-12` as a unit edge is impossible in this branch.

### Branch `d2_3`

```text
Q1 = (1,5)
Q2 = (2,4,7,11)
Q3 = (3)
Q4 = (6,10,12)
Q5 = (8,9)
```

The target pair `3-12` maps to `Q3-Q4`.

In the quotient graph, `Q3` and `Q4` have common unit-neighbors `Q2` and `Q5`,
and `Q2-Q5` is also a unit edge. Therefore the opposite-distance relation gives

```text
|Q3-Q4|^2 + |Q2-Q5|^2 = 4
```

Since `|Q2-Q5|^2 = 1`, this forces

```text
|Q3-Q4|^2 = 3
```

So reinserting `3-12` as a unit edge is also impossible in this branch.

Current status:

```text
all observed collision quotient branches certified: true
universal proof status: not complete
```

The remaining gap is to prove that every exact realization of the 24-edge core
falls into one of these collision quotients, or to produce an interval/algebraic
certificate excluding all distinct realizations directly.

Files:

- `subcore_021_collision_quotients/collision_quotients_summary.json`
- `subcore_021_collision_quotient_certificate/collision_quotient_certificate.json`
- `subcore_021_remove_3_12_distance_audit/remove_3_12_distance_summary.csv`
- `subcore_021_without_3_12_distinct_sweep/without_3_12_distinct_sweep_summary.csv`
- `subcore_021_without_3_12_best_distinct_audit/best_distinct_audit_summary.json`

## Layer 16: Exhaustion of Unresolved Collision Quotients

The collision-quotient enumeration for the 24-edge core
`subcore_021 - {3-12}` produced:

```text
independent-set partitions: 80100
loop: 12004
forced_sqrt3_by_opposite_relation: 56652
already_unit_edge_in_quotient: 7389
unresolved: 4055
```

The two numerically observed quotient branches from Layer 15 were recovered in
the enumeration.

The `unresolved` class was deduplicated to 3044 unique quotient graphs. After
reinserting the target quotient edge, all were eliminated by exact triangle
filtering:

```text
qV=6 unresolved unique quotient graphs: 50/50 triangle-eliminated
qV=7 unresolved unique quotient graphs: 762/762 triangle-eliminated
qV=8 unresolved unique quotient graphs: 2232/2232 triangle-eliminated
total unresolved unique quotient graphs: 3044/3044 triangle-eliminated
```

Thus the previous combinatorial gap for unresolved quotient branches is closed.

The remaining class is:

```text
already_unit_edge_in_quotient:
  partitions: 7389
  unique quotient graphs: 4471
```

These are not immediate contradictions after reinserting `3-12`, because the
target quotient pair is already a unit edge. However, they are still degenerate
collision branches: every such partition has at least one nontrivial collision
block. They therefore do not constitute distinct realizations of the original
12-vertex subcore.

Current proof frontier:

```text
closed:
  observed d2_0/d2_3 branches certified
  unresolved quotient branches eliminated by triangle filters

remaining:
  exclude the fully distinct/singleton realization case for subcore_021
  or produce an interval/algebraic certificate for the full 25-edge subcore
```

Files:

- `subcore_021_collision_quotient_enumeration/collision_quotient_partition_enumeration_summary.json`
- `subcore_021_unresolved_quotient_triage/unresolved_quotient_triage_summary.json`
- `subcore_021_unresolved_quotient_target_probe/qv6_unresolved_target_probe_metadata.json`
- `subcore_021_qv6_quotient_exact_filters/qv6_exact_filter_metadata.json`
- `subcore_021_unresolved_qv7_qv8_triangle_filter/qv7_qv8_triangle_filter_metadata.json`
- `subcore_021_already_unit_quotient_triage/already_unit_quotient_triage_summary.json`

## Layer 17: Reduced 18-Edge Core Certificate Candidate

The last high-block quotient survivor was reduced by greedy edge ablation.

Initial survivor:

```text
qV = 11
edge count with target = 23
target quotient edge = 3-11
```

Greedy reduction removed:

```text
2-6
5-6
5-10
5-7
3-7
```

The resulting 18-edge core is:

```text
1-2 1-4 1-6 1-10
2-3 2-11
3-9 3-11
4-8 4-9 4-10 4-11
6-7 6-8
7-8 7-9
8-11
9-10
```

This core remained numerically obstructed:

```text
best residual: about 1.3e-1
solved <= 1e-4: 0
```

Single-edge ablation indicated that the 18-edge core is numerically edge-critical:
removing any remaining edge produced near-exact realizations.

Removing the target edge `3-11` gives a 17-edge graph with exact numerical
realizations. Auditing the removed distance showed only two observed branches:

```text
|3-11|^2 = 0
|3-11|^2 = 3
|3-11|^2 = 1 was never observed
```

Collision-quotient extraction certified both observed branches.

### Branch `d2_0`

```text
Q1 = (1,8,9)
Q2 = (2,4)
Q3 = (3,10,11)
Q4 = (5)
Q5 = (6)
Q6 = (7)
```

The target pair `3-11` maps to `Q3-Q3`, hence becomes a loop.

### Branch `d2_3`

```text
Q1 = (1,8,9)
Q2 = (2,4)
Q3 = (3)
Q4 = (5)
Q5 = (6)
Q6 = (7)
Q7 = (10,11)
```

The target pair `3-11` maps to `Q3-Q7`.

In the quotient graph, `Q3` and `Q7` have common unit-neighbors `Q1` and `Q2`,
and `Q1-Q2` is also a unit edge. Therefore:

```text
|Q3-Q7|^2 + |Q1-Q2|^2 = 4
```

Since `|Q1-Q2|^2 = 1`, this forces:

```text
|Q3-Q7|^2 = 3
```

So reinserting `3-11` as a unit edge is impossible in this branch.

Current status:

```text
observed final-core branches certified: true
remaining gap: prove these are the only exact branches of the 17-edge core
```

Files:

- `subcore_021_final_survivor_greedy_core/final_greedy_core_edges.csv`
- `subcore_021_final_core_remove_3_11_distance_audit/remove_3_11_distance_summary.json`
- `subcore_021_final_core_collision_quotients/final_core_collision_quotients_summary.json`

## Historical Commands

The commands below document earlier layers of the search. They are retained for
reproducibility, but they are not the current active next step.

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
python .\n25_global_proof_search\triangle_lattice_filter.py --edges ..\03_uccs_exploration\uccs_square_stat_runs\n25_e70_seed20270530_edges.csv
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
python .\n25_global_proof_search\trilateration_eliminator.py --edges ..\03_uccs_exploration\uccs_square_stat_runs\n25_e70_seed20270530_edges.csv
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

## Historical Note: Proof Route Before Layers 15-17

This section records the proof route before the `subcore_021` collision-quotient
work became the active frontier. It is kept as historical context, not as the
current next step.

The finitely trilaterable frontier was already well covered by certificates.
The old forced-edge route also could not be used unless it was made
collision-aware. At that stage, the remaining hard case was the
non-trilaterable frontier. The practical route was:

1. collect and classify non-trilaterable `71+` candidates passing all exact
   filters;
2. audit all numerical witnesses for vertex collisions before using them;
3. derive a global distinctness obstruction for the 80-edge candidate, or for a
   smaller compatibility core extracted from it;
4. turn that obstruction into an interval or algebraic certificate independent
   of least-squares numerics;
5. repeat over all non-isomorphic frontier candidates above 70 edges.

Only after that kind of global audit can `U(25) <= 70` be claimed as a
universal proof.

The current active route is now more specific: close the reduced 18-edge core
from Layer 17, then lift that obstruction back to `subcore_021` and finally to
the hard non-trilaterable frontier. See `Current Status` and `Progress Timeline`
for the active state.
