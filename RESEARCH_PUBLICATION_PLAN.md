Research Publication Plan — KG-CAE
=================================

Purpose
- Convert the research notes (sections 5–8 in `Research_Model_Ideas.md`) into a publication-ready plan: required experiments, datasets, evaluation protocols, figures and tables to produce, timelines, acceptance criteria, and a suggested paper outline.

Scope
- Interpretability & explainability studies
- Ablation and controlled experiments for KACR, UCLR, DNH, MHSC
- Failure mode analysis and mitigations
- Broader extensions (temporal, multimodal) as future work

1. Required experiments (priority order)

1.1 Core reproducibility baseline
- Goal: reproduce baseline KG-CAE (contrastive+classification) on a mid-scale DBpedia-derived dataset.
- Dataset: sample of DBpedia entities across 10 domains, with multilingual abstracts and 2-hop RDF context. ~50k anchors.
- Protocol: train baseline and report entity linking accuracy, MRR, nDCG, embedding-factuality AUC, and calibration (Brier, ECE).
- Acceptance: baseline achieves non-trivial entity linking (e.g., > 40% top-1 on held-out anchors) and embedding-factuality AUC > 0.75 (example thresholds — tune based on pre-experiments).

1.2 KACR ablation
- Compare baseline vs baseline+KACR across same dataset.
- Metrics: Δ in embedding-factuality AUC, prototype separation statistics, per-domain improvements for low-resource entities.
- Acceptance: KACR improves AUC/MRR significantly (paired bootstrap p<0.05) and reduces prototype variance on low-support URIs.

1.3 DNH curriculum study
- Curriculum schedules: (a) static negatives, (b) random→graph-swap→latent-nearest (fast), (c) slower schedule.
- Metrics: convergence speed (validation loss vs epochs), embedding-factuality AUC at checkpoints, curriculum timelines.

1.4 MHSC trade-off study
- Compare with/without MHSC: measure 1-hop disambiguation and 2-hop retrieval accuracy.
- Acceptance: MHSC should increase 2-hop retrieval accuracy with modest changes to 1-hop MRR; report Pareto trade-off curves.

1.5 Interpretability study (prototype visualizations & counterfactuals)
- For a sample of 200 representative URIs, produce: prototype token highlights (n-gram importance), token/RDF attribution maps (integrated gradients or attention rollout), and minimal counterfactual edits that flip URI predictions.
- Produce example case studies (3-5) that illustrate successes and failures; include qualitative analysis.

1.6 Robustness and failure-mode probes
- Synthetic negatives: graph-swapped, paraphrase, masked facts. Measure performance deltas and report which methods are robust.

2. Datasets & preprocessing
- DBpedia sample (50k anchors), multilingual abstracts, and RDF 2-hop contexts.
- Validation: stratify by degree, support size, and domain; reserve a held-out set for final experiments.
- Provide scripts to convert Iceberg rows into training/eval TSV and to compute hop distances.

3. Evaluation protocols (detailed)
- Reproducibility checklist: seed, config, env, dataset snapshots (Iceberg), prototype support thresholds.
- Statistical tests: paired bootstrap for AUC/MRR; Spearman for hop monotonicity; Benjamini–Hochberg for multiple comparison correction.

4. Figures and tables to produce
- Figure: distance-vs-hop curves (mu_h), with CI bands across domains.
- Figure: prototype-distance histograms for baseline vs KACR.
- Figure: reliability diagrams pre/post temperature scaling.
- Table: ablation results (AUC, MRR, nDCG, Brier, ECE) with p-values.
- Appendix: per-prototype support sizes and example prototypes.

5. Timeline & milestones (suggested)
- Week 0-1: Prepare dataset sample & hop precompute; baseline training smoke runs.
- Week 2-3: Full baseline training & initial evaluations; produce mu_h curves and prototype stats.
- Week 4: KACR and DNH ablations; diagnostics and tests.
- Week 5: MHSC study and interpretability case studies.
- Week 6: Write up results, produce figures/tables, prepare reproducibility appendix.

6. Acceptance criteria for publication
- At least one strong quantitative improvement (AUC or MRR) from proposed components (e.g., KACR or DNH) with statistical significance and sensible ablation narrative.
- Clear interpretability evidence: prototypes and counterfactuals that show the model grounding behavior.
- Reproducible scripts and small dataset snapshot included in the artifact submission.

7. Paper outline (suggested)
- Abstract
- 1 Introduction
- 2 Related Work
- 3 KG-CAE model and training
- 4 Theoretical framing and hypotheses
- 5 Experiments (baseline, ablations)
- 6 Interpretability & case studies
- 7 Discussion, limitations, future work
- Appendix: reproducibility, configs, dataset snapshots

8. Next action items for authors (short)
- Approve dataset sampling and thresholds (n_min, max_h)
- Select priority ablation (KACR or DNH first)
- Assign compute resource and owner for baseline runs

9. Notes on presentation
- Emphasize the interpretability angle (prototypes as verifiable anchors) in the paper narrative; pair quantitative results with qualitative case studies.

---
If you want, I can now: (A) scaffold the paper with a filled-in intro and figure captions; (B) implement the dataset sampling script and baseline training runner next. Tell me which to prioritize.
