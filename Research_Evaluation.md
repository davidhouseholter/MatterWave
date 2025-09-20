# KG-CAE: Evaluation & Experimental Protocol (Research-Focused)

This document describes the experimental design, evaluation methodology, and reproducibility checklist for the KG-CAE project. It focuses on scientific rigor, measurable hypotheses, and fair comparisons with baselines. Code-level implementation details are minimized; the emphasis is on research methodology, metrics, and statistical validity.

## 1. Research Objectives and Hypotheses

Primary research objective:
- Demonstrate that a multi-task contrastive autoencoder (KG-CAE) that jointly learns entity linking and contrastive factual embeddings yields superior factual grounding and entity disambiguation compared to standard entity linkers and contrastive sentence encoders.

Hypotheses:
- H1: KG-CAE achieves higher entity linking accuracy (Precision@1) on standard benchmarks (AIDA-CoNLL, MSNBC) than baseline entity linking systems.
- H2: KG-CAE embeddings better separate factually correct vs. incorrect statements (higher AUC-ROC) than unguided sentence embeddings (Sentence-BERT, SimCSE).
- H3: Joint training (classification + contrastive) produces embeddings that improve retrieval-based fact-checking more than either objective alone (ablation study).

## 2. Datasets and Benchmark Selection

Primary datasets:
- AIDA-CoNLL (entity linking)
- MSNBC (entity linking)
- ACE2004 (entity mentions and relation context)

Auxiliary evaluation datasets for factuality and retrieval:
- FEVER (fact verification)
- TruthfulQA (subset for factuality detection)

Custom KG-CAE evaluation split:
- A held-out set of DBpedia entities not used during training (20% of discovered entities), ensuring no overlap in subject URIs between train/val/test.
- Synthetic negative sets generated via controlled entity-swapping to measure sensitivity to hard negatives.

Data preparation notes:
- Ensure canonicalization of entity URIs and normalization of text (Unicode normalization, whitespace trimming).
- Release a fixed split with random seed for reproducibility and auditing.

## 3. Baselines and Comparative Models

Selected baselines:
- Traditional entity linkers: TAGME, DBpedia-Spotlight
- Neural entity linkers: BLINK, GENRE (if available)
- Contrastive sentence encoders: Sentence-BERT (all-mpnet-base-v2), SimCSE
- Knowledge-enhanced models: KnowBERT, ERNIE (representative variants)

Evaluation mode:
- Evaluate each baseline using the same tokenization and input concatenation strategies where applicable.
- For entity linking baselines that output candidate URIs, use top-1 prediction for Precision@1.

## 4. Metrics and Statistical Testing

Primary metrics:
- Entity Linking: Precision@1, Precision@5, Recall, F1
- Embedding-based factuality: AUC-ROC, Precision-Recall, Average Precision
- Retrieval: MRR, MAP, nDCG@k

Secondary metrics:
- Calibration: Expected Calibration Error (ECE) on classification probabilities
- Robustness: Performance under paraphrase and adversarial noise (drop tokens, entity aliasing)
- Efficiency: Throughput (samples/sec), inference latency (ms)

Statistical testing:
- Use paired bootstrap resampling to compare means and compute 95% confidence intervals for primary metrics.
- Report p-values from paired t-tests where assumptions hold; otherwise report Wilcoxon signed-rank tests.
- Multiple comparisons: apply Benjamini–Hochberg correction to control false discovery rate.

## 5. Experimental Protocols

Training protocols:
- Repeat each training condition (full model and ablations) 5 times with different random seeds.
- Use early stopping based on validation Precision@1 with patience of 10 evaluation steps.
- Save checkpoints and record best validation metrics for reproducibility.

Evaluation protocols:
- Evaluate on held-out DBpedia test set and public benchmarks.
- For fact-checking tasks, use embedding distance thresholds calibrated on validation set.
- Report median and interquartile range (IQR) across seeds for all reported metrics.

Ablations:
- Remove classification head (contrastive-only)
- Remove contrastive objective (classification-only)
- Vary negative sampling hardness (easy vs. hard negatives)

Sensitivity analyses:
- Vary training data size (10%, 25%, 50%, 100%) to assess data efficiency
- Test cross-domain generalization by training on one domain (e.g., science) and testing on another (e.g., history)

## 6. Reproducibility Checklist

To ensure experiments can be reproduced and audited, provide the following:
- Fixed random seeds and exact environment configuration (Python version, package versions, GPU drivers)
- Dataset release: entity URIs, text variants, RDF snapshots, and negative examples with checksums
- Training logs and hyperparameter files for each seed/run
- Evaluation scripts and metric calculation code
- A Docker image or conda environment specification for consistent runtime

## 7. Compute and Resource Estimates

Prototype training:
- Single GPU (A100 or equivalent): expected 2–3 days for 1M triplets with mixed precision
- Multi-GPU (8xA100): training time reduced to 6–12 hours with distributed data parallel

Inference:
- CPU-only deployment: 50–200 ms per query depending on model size and optimizations
- GPU-accelerated inference: 5–20 ms per query

Cost estimates (indicative):
- Single A100 spot instance: $2–3/hour
- Full experimental sweep (5 seeds × ablations × baselines): plan for 2–4k GPU hours depending on dataset size and hyperparameter grid

## 8. Ethical Considerations and Data Governance

Privacy and license checks:
- Ensure that all data sources (Wikipedia, DBpedia) are used respecting their licenses (CC BY-SA for Wikipedia derivatives)
- Remove or flag sensitive entities and personally identifiable information where required

Bias and fairness:
- Measure performance across demographic axes where applicable (geography, language)
- Report any systematic failures and create mitigation plans (data augmentation, rebalancing)

Responsible disclosure:
- If the model demonstrates strong retrieval of sensitive information, consider controlled access or redaction

## 9. Reporting Format

For publication and internal reporting, include:
- Overview table of experimental settings and primary results
- Confidence intervals and statistical test results
- Ablation table showing contribution of each component
- Representative qualitative examples (successes and failures)
- Link to reproducible artifact (dataset + code) and Docker image

---

This research-focused evaluation document complements the main `ResearchSummary.md`. Next step: add a short pointer in the summary linking to this evaluation doc and mark that todo as in-progress.