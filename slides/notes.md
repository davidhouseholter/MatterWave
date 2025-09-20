Slide-by-slide speaker notes for the MatterWave deck


Slide 1 — Title
- Quick greeting and one-liner about the problem of hallucination in LLMs. State the project name: MatterWave / KG-CAE.

Executive Summary
- Emphasize the two main outputs: (1) a verifiable URI and (2) a contextual embedding. Explain why this matters: verifiability for downstream fact-checking and interpretable prototypes for human inspection.

Problem & Motivation
- Present a short concrete example: an ambiguous mention like "Mercury" where LLMs may hallucinate planetary facts or conflate the element. Show how a URI-based identifier disambiguates.

Model Overview
- Explain the shared encoder and why joint training with classification helps align embeddings with canonical URIs. Mention losses: Triplet margin (contrastive) + Cross-Entropy for URI classification. Briefly mention KACR and MHSC as regularizers (details in `Theoretical_Framing_and_Expected_Behaviors.md`).

Data Pipeline
- Walk through SPARQL entity discovery, 2-hop RDF enrichment, paraphrase augmentation, and negative generation strategies (entity swap and graph-based negatives). Call out Iceberg (versioning) and the recommended sample snapshot (50k anchors) for reproducibility.

Experimental Protocol
- Describe selected benchmarks and what each metric captures (Precision@1 is strict linking; MRR captures rank quality; ECE/Brier capture calibration of the URI classifier). Reference `RESEARCH_PUBLICATION_PLAN.md` for the prioritized experiment schedule and acceptance criteria.

Key Results
- If presenting pre-results, show what the final slide will contain: a table with baseline vs KACR/DNH/MHSC rows and columns for MRR, nDCG, AUC, Brier, and ECE. Use `results_templates/` to format these consistently.

Ablations & Interpretability
- Explain the ablation axes (classification head on/off, quantization on/off, negative hardness schedules). For interpretability, outline the prototype analysis workflow: compute per-URI centroid, retrieve nearest anchors, compute token and RDF attributions (integrated gradients), and produce minimal counterfactual edits. Link to the theoretical doc for code snippets and plotting examples.

Limitations & Ethics
- Highlight licensing for Wikipedia/DBpedia content and the need for redaction heuristics for PII. Also discuss representational bias risks when using ontological type-based negative sampling.

Next steps
- Summarize the immediate asks: approve the dataset sample and thresholds, pick KACR or DNH as the first ablation, and assign compute owner for baseline runs. Invite collaborators and point them to `RESEARCH_PUBLICATION_PLAN.md` for the full experiment list and timeline.

Closing / Q&A
- Offer to share the reproducibility checklist and the small dataset snapshot. Invite questions about evaluation choices or interpretability case studies.

References & Links
- `Theoretical_Framing_and_Expected_Behaviors.md` — formal math, loss definitions, and analysis snippets.
- `RESEARCH_PUBLICATION_PLAN.md` — prioritized experiments, figures, and timeline for the paper.
