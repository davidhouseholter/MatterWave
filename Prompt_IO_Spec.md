# Prompt I/O Specification — KG-CAE

This document inventories every place the system uses LLM prompts (data pipeline augmentation, agent synthesis, UI prompt builder, orchestrator condition prompts, and other spots across the workspace). For each location I list:

- Purpose / location
- When it's called (synchronous/async, batch/stream)
- Prompt input template (fields that must be populated)
- Expected LLM output shape and parsing rules
- Quality checks and post-processing
- Failure modes and mitigation

This file is intended as the canonical prompt contract for engineering and research reproducibility.

---

## 1 — Data Pipeline: LLM Augmentation (LLMAugmenter.generate_augmented_texts)

- Purpose: Generate diverse textual variants for an entity to increase training data diversity (historical context, simple explanations, analogies, domain connections).
- Location: `Research/DataGenerationPipeline_Detailed.md` (Text Augmentation Module) and `KGCAEPipeline.llm_augmenter`.
- When called: Per-entity during pipeline run, synchronous API call to external LLM (OpenAI-style chat completion), usually small batch (3 variants).

Prompt input template (string interpolation):
- entity_name: e.g., "Albert_Einstein" (human-readable: "Albert Einstein")
- base_text: first 500 characters of the anchor text (DBpedia/Wikipedia abstract)
- num_variants: integer (default 3)
- strategies: optional list (e.g., ["historical", "simple-explain", "analogy"]) — used to steer generation

Example prompt (raw):
"Given the entity \"Albert Einstein\" with description: \"[base_text shortened]\"\n\nGenerate 3 diverse text descriptions that capture different aspects:\n1. Historical/chronological context\n2. Simple explanation for beginners\n3. Connection to related concepts or fields\nEach description should be 2-3 sentences and factually accurate." 

Expected LLM output shape:
- Plain text containing enumerated descriptions or newline-separated variants.
- Parsing rule: split on newlines, remove leading numbering, collect variants >= 40 chars.

Post-processing / quality checks:
- Language detection: ensure English if required.
- Factuality heuristics: cross-check extracted named entities against DBpedia facts; flag high-variance claims for manual review.
- Length limits: trim to 500 chars.

Failure modes & mitigation:
- Hallucination: run entity-linking or simple SPARQL checks for critical facts; if mismatch, drop the variant or mark as low-quality.
- Rate limits: backoff + retry with exponential backoff; fallback to paraphrase generator.

---

## 2 — Data Pipeline: Agent-Augmented Scenario Generation (Phase 1.5 agent prompts)

- Purpose: Combine multiple entities into multi-entity narratives/scenarios for richer context (Entity Navigator, Temporal Context, Narrative Weaver agents).
- Location: `Research/DataGenerationPipeline_Detailed.md` (Agent-Augmented Data Synthesis section)
- When called: Orchestrated per-seed-entity; may run multiple agent steps with chaining; typically asynchronous and batched.

Prompt input template:
- seed_entities: list of entity names/URIs and short descriptions
- desired_scenario_type: e.g., "historical narrative", "cross-domain analogy"
- constraints: factual-only / allow analogies / max_entities

Example prompt (raw):
"Combine the following entities and facts into a coherent historical scenario involving Albert Einstein, ETH Zurich, and Hendrik Lorentz. Keep statements factual and cite the primary entity relationships. Output a 3-paragraph narrative." 

Expected LLM output shape:
- Structured sections: (1) scenario text, (2) explicit provenance lines mapping sentences to entity URIs, (3) optional bullet list of inferred relationships.
- Parsing rule: find provenance block; map sentences or clauses to URIs using regex patterns.

Post-processing / quality checks:
- Provenance verification: run SPARQL queries for asserted facts; mark or remove unverifiable claims.
- Entity alignment: ensure referenced entities map to canonical DBpedia URIs.

Failure modes & mitigation:
- Overly creative analogies: if constraints require factual accuracy, re-run with stricter temperature and instruction.
- Mixed languages: detect and re-run with language enforcement.

---

## 3 — Data Pipeline: Paraphrase Generation (ParaphraseGenerator.generate_paraphrase)

- Purpose: Produce semantically equivalent but textually distinct positive examples.
- Location: `DataGenerationPipeline_Detailed.md` (ParaphraseGenerator, T5-based)
- When called: Per-text during triplet generation; offline model (T5) used instead of external LLM.

Prompt input template (for T5):
- input_text: raw anchor text; model prompt: "paraphrase: {input_text}"
- decoding params: beams=5, temperature=0.8

Expected output shape:
- A single paraphrased text string; ensure it retains core facts.
- Parsing rule: decode tokens to string, remove special tokens; enforce sentence count.

Post-processing:
- Named entity consistency: ensure named entities preserved or mapped to canonical form.
- Semantic similarity threshold: compute embedding similarity; require similarity > 0.7 to accept.

Failure modes & mitigation:
- Loss of factual content: discard paraphrase if critical entity tokens are missing; or generate additional paraphrases.

---

## 4 — Data Pipeline: Negative Sample Generation via Entity Swapping (NegativeSampleGenerator.generate_hard_negative)

- Purpose: Create hard negatives by swapping type-compatible entities in RDF and text.
- Location: `DataGenerationPipeline_Detailed.md` (NegativeSampleGenerator)
- When called: Per-anchor during triplet generation; mixes SPARQL queries and deterministic replacements.

Prompt input template:
- anchor_rdf: Turtle string
- anchor_text: raw text
- entity_index: mapping of types to candidate URIs

LLM use: None primarily; however, an optional LLM step could be used to smooth text after replacement (e.g., ensure grammatical correctness). If used, prompt would be: "Rewrite this sentence after replacing [OldEntity] with [NewEntity] to make it grammatical and natural-sounding." 

Expected LLM output shape (optional smoothing):
- Single cleaned sentence or paragraph; parsing: accept output as new negative_text if mention replaced and length similar.

Post-processing:
- Verify replacement entity type compatibility via SPARQL.
- Ensure negative_text != anchor_text and factual mismatch exists.

Failure modes & mitigation:
- Accidental identity: replacement same as original; ensure uniqueness check.
- Grammar errors: fallback to rule-based capitalization and simple grammar fixes.

---

## 5 — UI: Research Notebook Prompt Builder (`app_knowledge_base/src/components/research-notebooks-list.js`)

- Purpose: Let users construct LLM prompts with contextual metadata (topics, dataset, instructions) and preview the final prompt.
- Location: `app_knowledge_base/src/components/research-notebooks-list.js` (renderLLMPromptTemplate, renderFinalPrompt)
- When called: On user action (button click); synchronous via browser -> backend LLM API.

Prompt input template (renderLLMPromptTemplate):
- currentQuery: user topic string
- context: selected topics, dataset descriptions, recent notes
- instructions: free-text user instructions

Example final prompt:
"You are a research assistant. Help the user explore \"quantum computing\" based on the following context: [context text] USER: [user prompt]"

Expected LLM output shape:
- Free-form assistant response (analysis, bullet lists, references)
- Parsing: none required; display raw to user; optionally extract suggested search queries.

Post-processing / quality checks:
- Sanitize outputs for PII and unsafe content before display.
- Limit output length and allow user to request expansions.

Failure modes & mitigation:
- Prompt injection: escape user-provided content and limit privileged instructions.
- Rate limits: implement client-side retry/backoff and cached responses.

---

## 6 — Orchestrator Condition Prompts (Agent routing)

- Purpose: Small discrete prompts used by the pipeline orchestrator to make routing decisions (e.g., "Should we clean the data?")
- Location: `pipeline_orchestrator_documentation.md` and `ia_modules/pipeline/condition_functions.py` (AGENT_PROMPT_TEMPLATES)
- When called: Synchronous control-flow decisions; often low-cost.

Prompt template example:
"Based on the data quality assessment results: {context.step_results.quality_assessment.result}, should we proceed with basic feature extraction? Respond with 'yes' to proceed or 'no' to route to data cleaning."

Expected LLM output shape:
- Single-token response 'yes' or 'no' (or short explanation)

Post-processing:
- Parse first token; accept case-insensitive yes/no; fall back to rule-based decision on ambiguous responses.

Failure modes & mitigation:
- Ambiguous answer: require strict matching to 'yes'/'no' and default to safe route (data cleaning) if not clear.
- Drift: periodically validate the LLM's decisions against human labels and convert to deterministic heuristics if unreliable.

---

## 7 — Miscellaneous: Business Forecast & Other App Prompts

- Location: `app_business_forecast/*` and other application modules show similar patterns: build prompt templates with structured JSON-like fields and then call `_call_ai_api(prompt)`.
- Input fields: domain-specific (business_profile, templates)
- Output shape: JSON-like structured suggestions; parsing rules are provided in the respective module using regex or JSON detection.

Quality controls:
- Validate JSON-like outputs with a strict parser; if invalid, ask the model to "Output valid JSON only" and retry.

---

## Cross-Cutting Standards for All Prompts

1. Deterministic metadata fields: always include `source_uri` when generating or augmenting text for traceability.
2. Temperature & randomness: use temperature 0.0-0.7 depending on whether factuality (lower) or creativity (higher) is desired.
3. Max tokens: set conservative ceilings (e.g., 500 tokens) and paginate long responses.
4. Provenance: request the model to output provenance lines when synthesizing multi-entity scenarios.
5. Safety: run generated text through PII checks and license compliance heuristics.

---

## Next steps

- I can expand this into a set of unit tests and small wrapper functions that enforce prompt contracts (input validation, parsing, LLM call wrapper with retries and verification). Would you like me to:
  - A) Implement the wrapper + tests for `LLMAugmenter.generate_augmented_texts` now? 
  - B) Generate a catalog of example prompts/outputs for manual review? 
  - C) Add schema definitions (JSON Schema) for each prompt output to support strict validation?

Pick one and I'll proceed.