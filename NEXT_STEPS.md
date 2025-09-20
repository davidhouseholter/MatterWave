NEXT STEPS: Roadmap and Actionable Tasks
=======================================

This document lists prioritized, actionable next steps to move the KG-CAE research from specification to reproducible experiments and publication-ready artifacts. Each item includes a short description, inputs, outputs, estimated effort, and acceptance criteria.

High-level goals
- Reproducible evaluation scripts and datasets (prototype computation, hop precomputation, calibration analyses).
- Baseline training and ablation scripts for KACR, MHSC, UCLR, and DNH.
- Bibliography and references: stable DOI/arXiv links and a `references.bib` file.
- Publication artifacts: figures, reproducibility checklists, and short README for experiments.

Priority tasks (short horizon)
1) Add analysis scripts (prototype_analysis.py, calibration_analysis.py, hop_precompute.py)
   - Inputs: model checkpoint, evaluation split, KG dump or SPARQL endpoint
   - Outputs: `eval_embeddings.pkl`, `hop_counts.pkl`, `prototypes.pkl`, `distance_vs_hop.png`, `ece_report.json`
   - Effort: 1-2 days
   - Acceptance: scripts run on small sample and produce the expected pickles and plots.

2) Create `requirements.txt` and small runner `run_analysis.sh` (or `run_analysis.ps1` for Windows)
   - Inputs: project environment
   - Outputs: reproducible environment manifest and a runnable command
   - Effort: 1-2 hours

3) Add training-loss snippets and unit tests
   - Files: `losses.py` with PyTorch implementations for L_triplet, L_kacr (prototype-based), L_mhsc, and L_var; unit tests in `tests/test_losses.py`
   - Inputs: small synthetic dataset
   - Outputs: test pass on synthetic tensors
   - Effort: 1-2 days

4) DOI resolution workflow
   - Option A (manual): compile candidate reference strings into `citation_candidates.csv` for review.
   - Option B (automated): perform web lookups (requires permission) and populate `references.bib` with DOIs/URLs.
   - Acceptance: `references.bib` created with at least X verified entries (you choose X).

Medium-horizon tasks
5) Ablation runner and experiment configuration
   - Implement `run_experiment.py` that reads YAML configs (see example_experiment.yaml) and runs a training or evaluation variant, logging metrics to a CSV or MLflow.
6) Visualization & interpretability notebooks
   - Jupyter notebooks for prototype visualizations, reliability diagrams, and attention attributions.

Longer-horizon tasks
7) Full-scale experiments and compute scheduling
   - Orchestrate runs on cloud GPUs, store Iceberg snapshots, produce final plots and tables.
8) Paper writing and artifact release
   - Prepare `figures/`, `results/`, and `references.bib` for submission; write reproducibility appendix.

Quick notes on DOI workflow and privacy
- I will not perform network lookups without explicit permission. If you want automated DOI resolution, confirm and I will run web lookups and populate `references.bib`.

Deliverables I can create for you now (pick any):
- `prototype_analysis.py`, `hop_precompute.py`, `calibration_analysis.py` (runnable scripts)
- `losses.py` with PyTorch snippets + tests
- `requirements.txt` and `run_analysis.ps1` (Windows)
- `references.bib` skeleton and `citation_candidates.csv`

How I will validate each script
- Minimal smoke test that runs on synthetic or tiny sample data (fast). If tests fail, I'll iterate up to 3 times to get green.

Open questions for you
- Permit automated web lookups for DOI/arXiv resolution? (yes/no)
- Priority of scripts: which should I deliver first? (prototype_analysis, hop_precompute, calibration_analysis, or losses)

---
Generated as a focused next-steps plan. Reply with which deliverables to add first and whether to allow DOI lookups.
