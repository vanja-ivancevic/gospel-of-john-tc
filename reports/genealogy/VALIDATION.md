# Genealogy validation

Witnesses: 170 | informative units: 1303 | labelled (ground truth): 67

**VERDICT: PASSED**

## 1. Silhouette of official families (>0 = real cluster in our distances)
- Alexandrian: +0.352
- Byz: +0.322
- f1: +0.226
- f13: +0.598
- overall: +0.340

## 2. Bootstrap clade support (fraction of resamples forming the clade)
- f1_core: 100%
- f13: 100%
- f1_full: 0%
- Byz: 0%

## 3. Known-pair nearest neighbours
- P75->nearest: [('03', 0.181), ('basetext', 0.183)]
- 1->nearest: [('1582', 0.026)]
- 13->nearest: [('826', 0.062)]

## 4. Cluster match vs official labels: ARI=0.683, V-measure=0.774 (best cut k=24)

## 5. Parameter sensitivity (f1/f13 recovered?)
| max_modal | min_overlap | n_units | f1 | f13 |
|--|--|--|--|--|
| 0.85 | 50 | 969 | True | True |
| 0.85 | 100 | 969 | True | True |
| 0.85 | 200 | 969 | True | True |
| 0.9 | 50 | 1303 | True | True |
| 0.9 | 100 | 1303 | True | True |
| 0.9 | 200 | 1303 | True | True |
| 0.95 | 50 | 1981 | True | True |
| 0.95 | 100 | 1981 | True | True |
| 0.95 | 200 | 1981 | True | True |