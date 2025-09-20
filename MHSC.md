# Multi-Hop Semantic Consistency (MHSC)

This document specifies the Multi-Hop Semantic Consistency (MHSC) loss: a constraint that encourages embedding geometry to reflect multi-hop graph relationships. MHSC enforces monotonic distance growth along hop length for traversals within a knowledge graph.

## 1. Intuition

If entity A is described by text T_A and there exists a path A -> B -> C in the knowledge graph, then embeddings from texts describing B and C should be progressively farther from z_A than z_B is: d(z_A, z_B) < d(z_A, z_C). This enforces a path-like geometry that can help the model reason about indirect relationships.

MHSC is not a hard rule; it is enforced as a soft penalty added to the training objective so the model can trade off local disambiguation vs global path consistency.

## 2. Loss Variants

1. Pairwise hop-margin loss (soft):

   L_mhsc = E_{(A,B,C) ~ hops(2)} [ max(0, d(z_A, z_B) + m1 - d(z_A, z_C)) ]

   where (A,B,C) are sampled such that B is a 1-hop neighbor of A and C is a 2-hop neighbor following A->B->C. m1 is a small margin.

2. Weighted hop decay loss:

   L_mhsc = E_{A} [ sum_{h=1..H} w_h * ReLU( d(z_A, z_{h}) - τ_h ) ]

   where z_h is an aggregated embedding of nodes at hop distance h (mean or prototype), τ_h is a target radius per hop, and w_h is a weight (increasing with hop length).

3. Path-ordering softmax:

   For a set of nodes at multiple hop-distances S = {z_1, z_2, ..., z_H}, impose a soft ordering by minimizing cross-entropy between a ground-truth ranking distribution (preferring nearer hops) and a softmax over negative distances.

## 3. Sampling Multi-Hop Chains

Sampling strategies determine which multi-hop chains to include:
- Short-path sampling: sample 1- and 2-hop chains uniformly from KG.
- Importance sampling: bias towards chains that cross ontological types of interest or that connect high-degree nodes.
- Context-conditioned sampling: prefer chains where the text contexts for B and C are available and linguistically informative.

## 4. Integration with Other Losses

MHSC complements KACR and contrastive losses. Practical integration patterns:
- Weighted sum: L_total = L_task + λ_kacr L_kacr + λ_mhsc L_mhsc + λ_contrastive L_contrastive.
- Curriculum: only enable MHSC after baseline contrastive loss has stabilized (e.g., after E_enable epochs).

Tune λ_mhsc to avoid overpowering fine-grained distinctions between close 1-hop neighbors.

## 5. Diagnostics and Metrics

Track:
- Hop monotonicity score: fraction of sampled chains where d(z_A,z_B) < d(z_A,z_C) holds.
- Distance growth curve: average d(z_A,z_h) vs hop h.
- Downstream impact: multi-hop retrieval accuracy (retrieve C given A through embedding path) and entity linking.

Visualization:
- Plot distance vs hop length curves, with error bars.
- Show example chains where MHSC increased/decreased ranking for 2-hop neighbors.

## 6. Experiments and Ablations

Suggested experiments:
- Baseline vs. MHSC: measure multi-hop retrieval and entity linking.
- Ablate hop depth H and weight schedules w_h.
- Test with noisy KG edges and measure robustness.

## 7. PyTorch Sketch (conceptual)

def compute_mhsc_loss(z_anchor, z_hop_dict, weights, margins):
    # z_hop_dict: {h: [embeddings at hop h]}
    # compute mean embedding per hop and apply weighted ReLU constraints
    # ...existing code...
    return loss

## 8. Practical Considerations

- Aggregation: use prototypes (mean or robust mean) to summarize embeddings at each hop to reduce variance.
- Sampling cost: enumerating many chains can be expensive; sample a modest number per batch and reuse prototypes.
- Conflicting neighbors: when 1-hop neighbors are semantically divergent, MHSC may hurt — tune λ_mhsc or mask those chains.

## 9. Next steps / Implementation Checklist

- Implement multi-hop sampler and prototype aggregator.
- Add MHSC loss module with configurable variants.
- Add unit tests on synthetic graphs to verify monotonicity enforcement.
- Run ablations and produce distance-vs-hop plots.

---
