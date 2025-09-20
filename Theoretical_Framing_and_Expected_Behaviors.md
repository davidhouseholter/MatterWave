Theoretical Framing and Expected Behaviors
=========================================

This document expands the Theoretical Framing and Expected Behaviors (Section 4 in `Research_Model_Ideas.md`) into a self-contained, detailed reference. It formalizes definitions, states hypotheses precisely, describes operationalization steps, gives concrete metrics and statistical tests, and provides example analysis code you can run locally to reproduce the core evaluation experiments.

1. Definitions and notation (precise)
-----------------------------------

- Knowledge graph: G = (V, E) with nodes v ∈ V and edges e ∈ E. Each node v has a canonical URI u_v.
- Input space: X is the set of possible concatenated inputs x = text || RDF where text is natural language and RDF is the Turtle/TTL string for context.
- Encoder: f_θ : X → R^d, embedding function parameterized by θ. We denote z_x := f_θ(x).
- Classifier: g_φ : R^d → Δ^{|V|} produces a probability distribution over canonical URIs; ĝ_u(x) := g_φ(f_θ(x))[u].
- Prototype: p_u := E_{x: subject(x)=u}[ f_θ(x) ] (estimated via sample mean or EMA during training).
- Distance metric: d(·,·) typically Euclidean or cosine-derived distance; where required, denote Euclidean as ||·||_2 and cosine distance as 1 - cos(·,·).

Additional notation and shorthand
- Let Z_u = { f_θ(x) : subject(x)=u } denote the empirical set of embeddings for entity u. Let n_u = |Z_u|.
- Let P = { p_u : u ∈ V } denote the set of prototypes.

When reporting, always include n_u and the sample variance S_u = 1/(n_u-1) ∑_{z∈Z_u} || z - p_u ||^2.

2. Formal hypotheses (exact testable statements)
-----------------------------------------------

H1 — Geometry-as-Factuality
  For anchor texts x_u with canonical subject u and prototypes p_v for v ∈ V, define μ_h := E_{(u,v): h_G(u,v)=h}[ d( f_θ(x_u), p_v ) ]. Then μ_h should be monotone non-decreasing in h for h = 0..H. Operational test: compute μ_h for h=0..H and test monotonicity using Spearman's rank correlation between h and μ_h.

H2 — Prototype Separability
  Let D_inter = { d(p_u, p_v) : u ≠ v } and D_intra(u) = { d( f_θ(x), p_u ) : subject(x)=u }. Prototypes are separated by margin τ_sep if P_{(u,v)∼V×V}[ d(p_u,p_v) > τ_sep ] ≥ 1 - ε for small ε (e.g., 0.05). Operational test: compute empirical CDF of inter-prototype distances and report fraction above τ_sep; compare to random baselines.

H3 — Calibration-Geometry Consistency
  For samples x and their ground-truth u, correlation Corr( ĝ_u(x), -d( f_θ(x), p_u ) ) should be significantly positive. Evaluate Pearson r and Spearman ρ, and compute calibration metrics (Brier, ECE).

H4 — Tightness vs Recall Trade-off
  Define intra_u = E_{x:subject=u}[ || f_θ(x) - p_u ||^2 ]. Reducing intra_u (via regularizer) should increase precision@k but may reduce recall@k for ambiguous mentions. Operational test: sweep λ_var and measure precision/recall curves.

3. Operationalization recipes (step-by-step)
------------------------------------------

3.1 Prototype estimation
- Option A (offline): Collect held-out validation set S_val with labels subject(x). Compute p_u = mean_{x∈S_val,subject(x)=u} f_θ(x).
- Option B (EMA during training): Maintain p_u^{t+1} = m * p_u^t + (1-m) * mean_{x in batch,subject=u} f_θ(x) with momentum m (e.g., 0.99).

3.2 Computing hop neighborhoods
- Precompute h_G(u,v) via BFS for each u up to H (H=3 recommended). Store Adj_h(u) for h=0..H.

3.3 μ_h computation (distance-vs-hop curve)
- For each anchor u, sample anchors x_u. For each h, compute d( p_u, p_v ) for v ∈ Adj_h(u). Aggregate μ_h = mean_{u}[ mean_{v∈Adj_h(u)} d(p_u, p_v) ].

3.4 Calibration and correlation analyses
- Compute ĝ_u(x) and d(f_θ(x), p_u) for x in an evaluation set. Compute Pearson r and Spearman ρ between ĝ_u(x) and -d(...). Compute Brier and ECE.

3.5 Losses and regularizers (precise forms)

Below are recommended, testable mathematical forms for the regularizers referenced in the research notes. Use these as starting points during ablation studies.

- Triplet margin loss (standard):

  L_triplet = E_{(A,P,N)} [ max(0, d(z_A, z_P) - d(z_A, z_N) + m) ]

  where (A,P,N) are Anchor/Positive/Negative embeddings and m is margin.

- Knowledge-Aware Contrastive Regularizer (KACR) — per-hop variant:

  For a chosen hop radius K and per-hop margins τ_k:

  L_kacr = E_{(u,v) ∈ Adj_{≤K}} [ max(0, d(p_u, p_v) - τ_{h_G(u,v)}) ]

  Intuition: penalize prototype distances that exceed a small hop-dependent threshold.

- Multi-Hop Semantic Consistency (MHSC): radial ordering loss

  Encourage monotone radial ordering around p_u for prototypes at increasing hop distances:

  L_mhsc = E_u [ ∑_{h=0}^{H-1} max(0, d(p_u, p_{h}) - d(p_u, p_{h+1}) + δ_h ) ]

  where p_{h} denotes a sample prototype at hop h from u (randomly sampled or averaged over Adj_h(u)), and δ_h ≥ 0 is a slack term.

- Intra-class variance regularizer (avoid collapse):

  L_var = E_u [ Var_{z∈Z_u} || z - p_u ||^2 ]

  Combine into full objective:

  L_total = α * L_classif + β * L_triplet + γ_kacr * L_kacr + γ_mhsc * L_mhsc + λ_var * L_var

  where α, β, γ_*, λ_var are tunable weights; ablation studies vary these to observe trade-offs.

4. Metrics and statistical tests (detailed)
-----------------------------------------

- Embedding-factuality AUC: label pairs (anchor, candidate) as positive if candidate is 1-hop neighbor, negative otherwise; score by -d(anchor, candidate prototype); report ROC AUC and 95% CI via bootstrapping.
- Prototype separation: compute mean μ_inter and std σ_inter of inter-prototype distances; compute fraction below τ_sep; perform KS test vs baseline (random shuffles of assignments).
- Calibration: Brier = mean( (ĝ_u(x) - 1_{u=truth})^2 ); ECE (10-bin) computed via standard reliability binning; optionally perform temperature scaling and report post-temp ECE.
- Significance: use paired bootstrap for MRR/accuracy comparisons; use Benjamini–Hochberg correction for multiple hypotheses.

5. Example analysis code (Python, runnable locally)
--------------------------------------------------

Below is a compact analysis snippet demonstrating prototype computation, μ_h curve, Spearman test, and calibration correlation. Run inside the project environment after exporting embeddings and metadata to a pickled file.

```python
import pickle
import numpy as np
from collections import defaultdict
from scipy.stats import spearmanr, pearsonr
from sklearn.metrics import brier_score_loss, roc_auc_score
import matplotlib.pyplot as plt

# Load precomputed embeddings and metadata
data = pickle.load(open('eval_embeddings.pkl','rb'))
# data: list of dicts with keys: 'text_id','subject_uri','embedding'(np.array)

# Compute prototypes (mean per subject)
by_sub = defaultdict(list)
for item in data:
    by_sub[item['subject_uri']].append(item['embedding'])
prototypes = {u: np.mean(np.stack(v), axis=0) for u,v in by_sub.items()}

# Example: compute inter-prototype distances per hop
# Precomputed hop mapping: hops[(u,v)] = hop_count
hops = pickle.load(open('hop_counts.pkl','rb'))

def euclid(a,b):
    return np.linalg.norm(a-b)

max_h = 3
mu_h = []
for h in range(max_h+1):
    vals = []
    for u in prototypes:
        for v in prototypes:
            if u==v: continue
            if hops.get((u,v),999)==h:
                vals.append(euclid(prototypes[u], prototypes[v]))
    mu_h.append(np.mean(vals))

rho, p = spearmanr(list(range(max_h+1)), mu_h)
print('mu_h:', mu_h, 'spearman rho=', rho, 'p=', p)

# Calibration correlation
probs = []
dists = []
for item in data:
    u = item['subject_uri']
    emb = item['embedding']
    prob = 0.0 # load or compute classifier prob for u (placeholder)
    # here, assume data includes 'prob' key
    prob = item.get('prob', 0.0)
    probs.append(prob)
    d = euclid(emb, prototypes[u])
    dists.append(d)

pearson_r, pval = pearsonr(probs, [-x for x in dists])
spearman_rho, sp_p = spearmanr(probs, [-x for x in dists])
print('pearson r=', pearson_r, 'p=', pval)
print('spearman rho=', spearman_rho, 'p=', sp_p)

# plot mu_h vs hop
plt.figure()
plt.plot(range(max_h+1), mu_h, marker='o')
plt.xlabel('hop h')
plt.ylabel('mean prototype distance mu_h')
plt.title('Distance vs hop')
plt.grid(True)
plt.savefig('distance_vs_hop.png')

# reliability diagram / ECE (10-bin)
def compute_ece(probs, labels, n_bins=10):
  bins = np.linspace(0,1,n_bins+1)
  ece = 0.0
  for i in range(n_bins):
    l = bins[i]; r = bins[i+1]
    mask = (np.array(probs) >= l) & (np.array(probs) < r)
    if np.sum(mask)==0: continue
    acc = np.mean(np.array(labels)[mask])
    conf = np.mean(np.array(probs)[mask])
    ece += (np.sum(mask)/len(probs)) * abs(acc-conf)
  return ece

# If we have ground-truth labels for top-predicted URI
labels = [1.0 if item.get('subject_uri')==item.get('pred_uri') else 0.0 for item in data]
ece_val = compute_ece(probs, labels)
print('ECE (10-bin):', ece_val)

```

6. Example experiment templates (scripts & config)
-------------------------------------------------

- prototype_analysis.py — computes prototypes, μ_h curves, and prototype separation reports.
- calibration_analysis.py — computes Brier/ECE and plots reliability diagrams.
- hop_precompute.py — given a KG dump or SPARQL access, computes hop distances up to H and serializes to `hop_counts.pkl`.

Additions: recommended config (YAML) for reproducible experiments

example_experiment.yaml
-----------------------
```
dataset: dbpedia_sample_v1
eval_split: validation
max_h: 3
model: transformer-base
batch_size: 64
optimizer:
  name: adamw
  lr: 5e-5
loss_weights:
  alpha: 1.0
  beta: 1.0
  gamma_kacr: 0.1
  gamma_mhsc: 0.05
  lambda_var: 1e-3
```

7. Practical notes and pitfalls
-----------------------------

- Prototype bias: prototypes estimated from small support sizes are noisy; report n_u for each prototype and filter prototypes with n_u < N_min (e.g., 5).
- Hop measures depend on KG completeness and chosen ontology; consider multiple KG sources (DBpedia + Wikidata) to validate robustness.
- Distance metric choice matters: Euclidean works when embeddings are l2-normalized; cosine is often more stable across pretraining regimes.

8. Reproducibility checklist
---------------------------

- Save random seeds and environment (Python, library versions).
- Log prototype support sizes, per-prototype example lists, and filter thresholds.
- Release scripts to compute `eval_embeddings.pkl` and `hop_counts.pkl` from raw model checkpoints and KG snapshots.

9. FAQs
-------

Q: What if prototypes shift during fine-tuning?
A: Recompute prototypes on held-out evaluation examples after each checkpoint; track prototype drift and report its magnitude relative to inter-prototype distances.

Q: How to set τ_sep?
A: Use a held-out calibration set and choose τ_sep to achieve a desired false-positive rate on inter-prototype overlap, or treat τ_sep as a hyperparameter for reporting.

10. References & related work
----------------------------

Include references to contrastive representation learning, prototype-based classifiers, and knowledge graph embeddings. (Populate `references.bib` as a follow-up.)

---
Generated from `Research_Model_Ideas.md` Section 4.
