# Knowledge-Aware Contrastive Regularizer (KACR)

This document defines the Knowledge-Aware Contrastive Regularizer (KACR) proposed in `Research_Model_Ideas.md` (section 3.1). It provides formal loss variants, a concrete PyTorch-compatible implementation sketch, suggested datasets and splits, an experimental protocol, diagnostic plots, and ablation studies to evaluate the contribution of KACR.

## 1. Motivation & High-level Description

KACR supplements standard contrastive/triplet losses by explicitly encouraging embeddings of texts describing nearby entities in the knowledge graph to be close in the embedding space. The underlying intuition is that graph proximity (k-hop adjacency) encodes semantic relatedness that the model should respect even when textual descriptions vary.

Benefits to test:
- Improved clustering of semantically related entities
- Better generalization for entities with limited textual data (cold-start)
- Improved retrieval recall when queries require knowledge-contextual similarity

Risks to monitor:
- Over-clustering across distinct entities leading to lower disambiguation accuracy
- Overweighting noisy graph links (DBpedia errors) causing drift

## 2. Formal Loss Variants

Notation:
- z_i: embedding vector for anchor text describing entity i
- d(u, v): distance metric, e.g., cosine distance (1 - cos(u,v)) or Euclidean
- Adj_k: set of entity pairs (i, j) such that graph distance hop(i, j) ≤ k
- τ_k: margin (scalar) for hop-distance k. Can be fixed or learned.
- λ_k: scalar weight for KACR term at hop k

Base contrastive loss (triplet margin example):
L_ctr = E_{(a,p,n)~D} [ max(0, d(z_a, z_p) - d(z_a, z_n) + m) ]

KACR (simple form):
L_kacr = Σ_{k=1}^K λ_k * E_{(i,j)∼Adj_k} [ max(0, d(z_i, z_j) - τ_k) ]

Alternative formulations:
- Weighted pairwise hinge (symmetric):
  L_kacr_sym = Σ_k λ_k * E_{(i,j)∼Adj_k} [ max(0, (d(z_i,z_j) - τ_k)) + max(0, (d(z_j,z_i) - τ_k)) ]

- Soft margin (log-sum-exp for stability):
  L_kacr_smooth = Σ_k λ_k * E_{(i,j)∼Adj_k} [ log(1 + exp(α*(d(z_i,z_j) - τ_k))) ]

- Relative margin tying to random pairs (contrast-to-background):
  L_kacr_rel = Σ_k λ_k * E_{(i,j)∼Adj_k} [ max(0, d(z_i,z_j) - E_{r∼Rand}[d(z_i,z_r)] + τ_k) ]
  where Rand samples random entities from the training pool.

Full training objective (multi-task):
L_total = L_ctr + γ * L_cls + L_kacr
where L_cls is the classification cross-entropy for subject URI prediction and γ controls its weight.

## 3. Practical Implementation Notes

- Choice of distance: cosine distance (1 - cosine similarity) is numerically stable for normalized embeddings and aligns with retrieval metrics (cosine similarity). Euclidean distance is fine if embeddings are not normalized.
- Margins τ_k: sensible initialization is τ_1 < τ_2 < ... (1-hop pairs should be closer than 2-hop). They can be:
  - Fixed hyperparameters (grid search)
  - Learned scalars with gradient updates (constrained to be positive)
  - Parameterized via a small MLP on hop distance to produce margins
- λ_k weights: control strength per hop. Start with λ_1 = 1.0 and exponentially decay for higher hops.
- Sampling Adj_k: uniformly sampling all k-hop pairs is expensive. Use negative sampling-style mini-batching:
  - Precompute adjacency lists for each entity up to K hops (or sample dynamically using BFS)
  - During a training batch, for each anchor entity sample 1-3 neighbors at each desired hop distance
- Efficiency: compute KACR on minibatch embeddings only. To get 2-hop neighbors not present in the batch, maintain a lightweight neighbor cache or sample negative-background embeddings from an embedding memory bank.

## 4. PyTorch Loss Snippet (sketch)

Below is a compact PyTorch implementation sketch for L_kacr using cosine distance and learnable τ_k.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class KACRLoss(nn.Module):
    def __init__(self, max_hop=2, initial_tau=None, lambda_k=None, device='cpu'):
        super().__init__()
        self.max_hop = max_hop
        self.device = device

        # learnable margins per hop
        if initial_tau is None:
            initial_tau = [0.2 + 0.1*k for k in range(max_hop)]
        self.taus = nn.Parameter(torch.tensor(initial_tau, dtype=torch.float32, device=device))

        if lambda_k is None:
            lambda_k = [1.0] + [0.5]*(max_hop-1)
        self.lambda_k = torch.tensor(lambda_k, dtype=torch.float32, device=device)

    def forward(self, embeddings, hop_pairs):
        """
        embeddings: Tensor [N, D] (assume normalized)
        hop_pairs: dict {k: Tensor[num_pairs_k, 2]} each row is (i, j) indices into embeddings
        """
        loss = embeddings.new_zeros(1)

        for k, pairs in hop_pairs.items():
            if pairs is None or len(pairs) == 0:
                continue
            idx_i = pairs[:, 0]
            idx_j = pairs[:, 1]

            zi = embeddings[idx_i]  # [P, D]
            zj = embeddings[idx_j]

            # cosine distance
            cos_sim = (zi * zj).sum(dim=1)  # assume embeddings normalized
            dist = 1.0 - cos_sim

            margin = self.taus[k-1]
            hinge = F.relu(dist - margin)
            loss = loss + self.lambda_k[k-1] * hinge.mean()

        return loss
```

Notes:
- `hop_pairs` should be generated per-mini-batch using entity IDs for which embeddings are currently present. If the desired neighbor is not in the batch, sample from a memory bank or skip.
- Normalize embeddings before passing to KACRLoss for cosine-based distances.

## 5. Datasets and Splits

- Training source: DBpedia-derived triplets dataset produced by the pipeline. Use the Iceberg table to create splits.
- Suggested splits:
  - Train: 70% of entity URIs
  - Validation: 15% (monitor entity linking Precision@1 and KACR diagnostics)
  - Test: 15% held-out entities (no subject URI overlap with train)

- Benchmarks for external evaluation:
  - AIDA-CoNLL, MSNBC, ACE2004 for entity linking
  - FEVER for retrieval-based factuality checks

- Controlled subsets for KACR analysis:
  - Sparse-text entities: entities with < 300 characters of Wikipedia text
  - Dense-text entities: entities with > 1000 characters
  - Cross-domain pairs: sample neighbors across ontology types to test over-clustering

## 6. Experimental Protocols

Primary experiments:
1. Baseline: KG-CAE without KACR (contrastive + classification)
2. KACR added with fixed τ_k and λ_k hyperparameters
3. KACR with learned τ_k
4. KACR + memory-bank neighbor sampling (to increase adjacency coverage)

For each condition:
- Run 3-5 seeds; report median and IQR for metrics
- Track metrics: Entity Linking Precision@1, MRR, Embedding AUC-ROC for factual vs. corrupted statements, Retrieval nDCG@10
- Diagnostic metrics: average pairwise distance for 1-hop vs. random pairs, silhouette score for URI clusters, intra-class variance

Ablations:
- Vary λ_1 from 0.1 to 2.0 to test sensitivity
- Compare cosine vs. Euclidean distance
- Test K up to 3 hops and measure marginal benefit

## 7. Expected Plots and Analyses

- Training curves: total loss, contrastive loss, classification loss, KACR loss
- Validation metrics per epoch: Precision@1, MRR, AUC-ROC
- Boxplots across seeds for primary metrics
- Distance histograms: distribution of d(z_i,z_j) for 1-hop, 2-hop, random pairs (show separation)
- t-SNE/UMAP visualizations colored by URI and by ontology neighborhood
- Ablation sensitivity plots: metric vs. λ_1 and vs. τ_1

## 8. Failure Modes and Monitoring

- Over-clustering: monitor recall drop; use intra-class variance regularizer if needed
- Noisy graph edges: add provenance-weighted λ_k where λ_k = base * provenance_score(entity_pair)
- Computational cost: neighbor sampling and memory bank maintenance; profile and limit neighbor lookup per batch

## 9. Implementation Checklist

- [ ] Add `KACRLoss` module to `models/losses.py`
- [ ] Add neighbor sampler utility to `data/graph_utils.py`
- [ ] Add training config flags (`use_kacr`, `kacr_tau_learnable`, `kacr_lambda_k`)
- [ ] Add validation diagnostics to `evaluation/diagnostics.py`

## 10. Reproducibility

- Provide example `train_kacr.yaml` with hyperparameters and neighbor-sampling settings
- Save all random seeds, exact versions, and the Iceberg snapshot used for training

---

If you'd like, I can now:
- A) Add a PyTorch test harness and unit test for the `KACRLoss` (small synthetic embeddings) and commit it to the repo; or
- B) Update `ResearchSummary.md` to add a pointer to `Research/KACR.md` and mark the KACR todo completed; or
- C) Both A and B (I will create the test harness and update the summary). Which do you want next?