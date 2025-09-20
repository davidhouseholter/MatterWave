# Subject IDs and Multi-Domain URI Strategy

This document defines how subject identifiers (semantic IDs) are handled in KG-CAE, the current DBpedia-focused default, and how the system can support multi-domain URIs (Wikidata, local ontologies, custom resources). It covers canonicalization, schema changes, mapping and reconciliation strategies, impact on model training, indexing, and dataset release considerations.

## 1. Current Default: DBpedia-Based IDs

- Canonical form: `http://dbpedia.org/resource/<LocalName>` (e.g., `http://dbpedia.org/resource/Albert_Einstein`).
- Rationale: DBpedia provides a stable, widely-used URI space that maps directly to Wikipedia pages and contains structured ontological properties useful for neighbor-based sampling and entity swapping.
- Implementation in the pipeline: `subject_uri` stored as a string column and `subject_uri_id` as an integer mapping in the Iceberg table.

## 2. Why Multi-Domain URIs Matter

- Coverage gaps: Some entities or domains may be better represented in other knowledge sources (Wikidata, domain-specific ontologies, private KBs).
- Provenance & licensing: Wikidata offers better provenance metadata and cross-language coverage; local ontologies may contain domain-specific types and relations.
- Migration/resilience: Relying on a single namespace risks brittleness if datasets shift; multi-domain support increases robustness.

## 3. Canonicalization Strategy

Goal: Ensure that each semantic identifier used in training and inference is canonical, persistent, and unambiguous.

Approach:
1. Preferred-URI policy: define an ordering of preferred sources (e.g., DBpedia -> Wikidata -> LocalKB). When an entity has multiple URIs, choose the preferred one for `subject_uri` and record all aliases in `subject_uri_aliases`.
2. Alias table: maintain `subject_uri_aliases` mapping table (JSON column or separate Iceberg table) with fields:
   - `canonical_uri` (string)
   - `aliases` (list of strings)
   - `preferred_source` (enum: dbpedia, wikidata, local)
   - `mapping_timestamp` (ISO)
   - `provenance_score` (float)
3. Canonicalization procedure: use Wikidata sitelinks and `owl:sameAs` links in DBpedia to find equivalences, and fall back to label matching and contextual heuristics when necessary.

Example alias record (JSON):
```
{
  "canonical_uri": "http://dbpedia.org/resource/Albert_Einstein",
  "aliases": ["http://www.wikidata.org/entity/Q937", "http://example.org/localkb/ent-12345"],
  "preferred_source": "dbpedia",
  "mapping_timestamp": "2025-09-20T12:00:00Z",
  "provenance_score": 0.92
}
```

## 4. Multi-Domain Schema Changes

Proposed Iceberg table schema additions:
- `subject_uri` (string) — canonical chosen URI
- `subject_uri_id` (int64) — stable integer ID assigned to canonical URI
- `subject_uri_source` (string) — e.g., `dbpedia`, `wikidata`, `local`
- `subject_uri_aliases` (json) — alias list with provenance
- `subject_uri_provenance_score` (float)

Why this helps:
- Keeps training pipeline changes minimal (main `subject_uri` preserved)
- Tracks provenance and supports per-source ablation studies
- Makes dataset releases more transparent about source mix

## 5. Mapping & Reconciliation Strategies

1. Use structured equivalence links:
   - Prefer `owl:sameAs` links in DBpedia to find Wikidata/other URIs.
   - Use Wikidata API `wbgetentities` to obtain sitelinks and labels.
2. Label-based fuzzy matching as fallback:
   - Use normalized labels, language-aware token matching, and context windows to resolve to likely candidates.
3. Human-in-the-loop reconciliation:
   - For ambiguous mappings, record candidates and a confidence score; expose these for manual review.
4. Batch remapping:
   - Support remapping rules and periodic refreshes to incorporate KB updates.

## 6. Assigning `subject_uri_id` (stable integer IDs)

Requirements:
- Deterministic: given the same canonical URI list and seed, mapping should be stable across runs.
- Extendable: allow adding new URIs without remapping entire ID space.

Approach:
- Use a monotonic ID allocator that reserves ranges per source or time-window.
- Maintain a central mapping table (`uri_to_id` Iceberg table) and a simple API for lookups and allocations.

Implementation sketch:
- At dataset generation time, consult `uri_to_id` to lookup or allocate IDs. Persist allocations atomically to avoid races.
- Record `mapping_timestamp` for each allocation and support idempotent replays.

## 7. Training & Model Impacts

- Classification head dimension: number of unique `subject_uri_id` entries. Multi-domain support may increase the vocabulary size; consider hierarchical softmax or sampled softmax for scalability.
- Calibration and confusion: mixing sources can cause duplicate semantic labels (aliases) to compete; use canonicalization and alias aggregation so the classifier learns canonical IDs.
- Data imbalance: different sources will have different coverage; track per-source counts and consider reweighting or balanced sampling.
- Negative sampling: when generating hard negatives, respect source boundaries if desired (e.g., prefer swapping with same-source entities or same ontology type).

## 8. Dataset Release & Licensing

- When releasing data, provide a `source_manifest.csv` listing the distribution of sources (dbpedia/wikidata/local) and a `aliases.json` mapping.
- Include provenance scores and the canonicalization rules used in the release.
- Licensing: ensure all sources' licenses are compatible (Wikidata: CC0; Wikipedia: CC BY-SA) and document any derived-work obligations.

## 9. Migration & Backwards Compatibility

- When switching preferred source (e.g., from DBpedia to Wikidata canonical URIs), provide a migration map and re-generate `subject_uri_id` allocations or use stable alias mapping to reassign ids.
- Provide a `uri_redirects` mapping and a small migration script to update existing Iceberg tables without breaking older models.

## 10. Operational Tools & Utilities

- `uri_resolver.py`: resolve labels/aliases to canonical URI
- `uri_to_id_manager.py`: atomic allocator and lookup API for `subject_uri_id`
- `alias_auditor.py`: sample ambiguous records for human review and produce audit reports

## 11. Example Workflows

1. Ingest DBpedia entity -> enrich RDF -> resolve canonical URI via alias table -> record `subject_uri_id` -> write to Iceberg.
2. If DBpedia lacks a canonical URI for an entity but Wikidata has a richer entry: resolve, set `subject_uri_source=wikidata`, and proceed.
3. For local KB entity: assign `local` source and ensure aliasing to external KBs when possible.

---

Next steps I can take:
- A) Add `uri_resolver.py` and `uri_to_id_manager.py` skeletons to `data/` with unit tests. 
- B) Add schema migration scripts and example `pipeline_config` changes to enable multi-domain ingestion. 
- C) Update `ResearchSummary.md` to link to this doc and mark the todo as completed.

Which one should I do next?