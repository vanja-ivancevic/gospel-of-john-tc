# Genealogy validation

Witnesses: 169 | informative units: 1285 | labelled (ground truth): 67

**VERDICT: PASSED**

> **What this validates (and what it does not).** The f1/f13 ground-truth labels are the published IGNTP lists that we also use to *assign* those families, so silhouette/ARI test whether our distance metric *groups* the published families as real clusters — they do **not** independently validate the assignment (that is asserted from the lists). The Byzantine ground truth is independent (the IGNTP Byzantine bundle) and is gated via silhouette. ARI is reported at the **deployed** cut (k = genealogy.n_clusters), not the best-of-sweep, to avoid a multiple-comparisons artifact.

## 1. Silhouette of official families (>0 = real cluster in our distances)
- Alexandrian: +0.349
- Byz: +0.322
- f1: +0.227
- f13: +0.600
- overall: +0.341

## 2. Bootstrap clade support (fraction of resamples forming the clade)
- f1_core: 100%
- f13: 100%
- f1_full: 0%
- Byz: 0%

## 3. Known-pair nearest neighbours
- P75->nearest: [('03', 0.181), ('029', 0.206)]
- 1->nearest: [('1582', 0.027)]
- 13->nearest: [('826', 0.062)]

## 4. Cluster match vs official labels: ARI=0.0, V-measure=0.0 at deployed k=12 (descriptive best-of-sweep: ARI=0.683 at k=25)

## 5. Parameter sensitivity (f1/f13 recovered?)
| max_modal | min_overlap | n_units | f1 | f13 |
|--|--|--|--|--|
| 0.85 | 50 | 961 | True | True |
| 0.85 | 100 | 961 | True | True |
| 0.85 | 200 | 961 | True | True |
| 0.9 | 50 | 1285 | True | True |
| 0.9 | 100 | 1285 | True | True |
| 0.9 | 200 | 1285 | True | True |
| 0.95 | 50 | 1977 | True | True |
| 0.95 | 100 | 1977 | True | True |
| 0.95 | 200 | 1977 | True | True |

## 6. Independent-method comparison (Edmondson 2019)
Edmondson, *An Analysis of the CBGM Using Phylogenetics* (Birmingham PhD, 2019), ran an independent **Bayesian phylogenetic** analysis on the ECM of John. We cannot reproduce his exact tree (his John 18 input collation is not public), so this is a qualitative comparison of whether two unrelated methods recover the same structure:
- **Family 1** is a well-supported clade for him; here it recovers with 100% bootstrap support and a positive silhouette.
- **Family 13** likewise: he finds a strong f13 clade (his data even has an f13 sub-tree); here 100% bootstrap support.
- **P75 with the Alexandrian witnesses** (the classic P75–Vaticanus affinity): our nearest neighbours for P75 are [('03', 0.181), ('029', 0.206)].
An independent method recovering the same families is evidence the groupings are real and not an artifact of our coherence metric. Method and tooling: open-cbgm and teiphy (McCollum & Turnbull); our own NJ tree and NEXUS matrices are exported alongside this report for anyone wanting to rerun NeighborNet or a Bayesian analysis.