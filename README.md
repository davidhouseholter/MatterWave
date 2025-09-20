
### **Draft: Factually-Grounded Semantic Identifiers: A Contrastive Autoencoder for Bridging Language and Knowledge Graphs**

### **Abstract**
Current methodologies for generating semantic identifiers, such as Residual Quantized Variational Autoencoders (RQ-VAEs), produce latent representations that are effective for similarity-based retrieval but lack explicit, verifiable meaning. Concurrently, large language models exhibit high linguistic fluency but are prone to factual inaccuracies and hallucinations due to their detachment from structured knowledge bases. This paper introduces the Knowledge-Grounded Contrastive Autoencoder (KG-CAE), a novel architecture designed to address these limitations. The KG-CAE redefines the semantic identifier as a canonical Uniform Resource Identifier (URI) from a formal knowledge graph. We employ a multi-task, contrastive training objective that forces a shared-weight Transformer encoder to learn the relationship between unstructured natural language and its corresponding structured RDF representation. The training objective combines a Triplet Margin Loss to sculpt a latent space where vector distance corresponds to factual consistency, and a classification loss to explicitly link text to its subject URI. The final output is a dual-component identifier: 1) a verifiable URI for direct knowledge graph integration and 2) a contextual embedding within a factually-aligned vector space. This architecture serves as a robust bridge between statistical language models and symbolic knowledge, producing an encoder that is more reliable, interpretable, and factually grounded.

### **1. Introduction**
The generation of meaningful representations for complex data is a central problem in machine learning. In the domain of language, two distinct paradigms have emerged. The first, exemplified by RQ-VAEs, focuses on learning compressed, discrete latent codes (semantic IDs) from high-dimensional embeddings. While successful in creating a hierarchical structure for efficient retrieval, these IDs are implicit and model-specific, with no grounding in external, verifiable facts. The second paradigm, large language models (LLMs), has achieved unprecedented success in generating fluent text but operates without an explicit connection to a factual world model, leading to well-documented issues of factual unreliability.

This work posits that a truly robust semantic identifier must be both semantically rich and factually verifiable. We propose to bridge the gap between these paradigms by redefining the semantic ID as a canonical URI from a public knowledge graph like DBpedia. To achieve this, we introduce the KG-CAE, an architecture designed to learn a direct mapping from unstructured text to the formal, symbolic representation of its factual content. Our primary contributions are:
1.  A novel data generation pipeline that creates a multi-modal, contrastive training set from text and RDF graph traversals.
2.  A multi-task training objective combining contrastive metric learning for factual consistency and a classification task for explicit entity linking.
3.  A final encoder model that outputs a dual-component identifier, enabling both direct knowledge graph querying and nuanced, factually-aware semantic search.

### Executive summary

The Knowledge-Grounded Contrastive Autoencoder (KG-CAE) is a dual-output encoder that tightly couples natural language inputs with symbolic facts from public knowledge graphs. KG-CAE uses a single Transformer encoder (shared weights) together with two learning objectives: a contrastive Triplet Margin Loss that shapes the embedding space so distances reflect factual consistency, and a classification loss that predicts a canonical subject URI (for example, a DBpedia URI). Training data is produced by an automated pipeline that enriches each target entity with a two-hop RDF subgraph, aggregates multilingual text, and generates triplets (anchor, paraphrase positive, hard negative via entity swaps). The result is a verifiable semantic identifier consisting of (1) an explicit URI for direct KG lookup and (2) a contextual embedding for retrieval and similarity-based reasoning.

This design improves entity linking and robustness to factual corruption, enables embedding distances to serve as factual-consistency scores, and supports reproducible evaluations of multi-hop retrieval and calibration diagnostics. The project includes a scalable data-generation pipeline (versioned Apache Iceberg tables on S3), knowledge-aware regularizers (KACR, MHSC), and a curriculum for dynamic negative mining (DNH) to progressively increase negative difficulty during training.

Key expected outcomes:

- Reliable entity linking to canonical URIs and improved robustness to factual corruption.
- Embeddings whose geometry correlates with knowledge-graph structure (e.g., hop-distance relationships).
- A reproducible, scalable data-generation pipeline and an evaluation suite for probe-based metrics and calibration diagnostics.

For a formal, reproducible expansion of the theoretical framing summarized above — including precise definitions, operationalization recipes, example analysis snippets, and metric definitions to reproduce Section 4 experiments — see `Theoretical_Framing_and_Expected_Behaviors.md`.

Research artifacts

- `Theoretical_Framing_and_Expected_Behaviors.md` — formalized definitions, operationalization recipes, metrics, and analysis snippets for reproducing Section 4 experiments.


### **2. Methodology: Data Foundation and Preprocessing**

The foundation of the KG-CAE is a high-quality, structured dataset designed to teach the model the explicit relationship between language and facts.

**2.1. Data Sources**
The primary data sources are English Wikipedia, for its comprehensive corpus of unstructured text, and DBpedia, for its structured RDF knowledge graph.

**2.2. Data Generation Pipeline**
A modular, cloud-native pipeline is employed to generate the training data, which is stored in a versioned Apache Iceberg table on an S3 data lake for scalability and reproducibility.

*Detailed implementation specifications, code examples, and configuration options are available in [`DataGenerationPipeline_Detailed.md`](DataGenerationPipeline_Detailed.md).*

*   **Step A: Entity Scoping and Discovery:** A preliminary script discovers a set of target entity URIs by performing a category-based crawl of DBpedia to a specified depth. This produces a reviewable list of entities (e.g., `discovered_entities.json`) that serves as the input for the main generation process.
*   **Step B: Contextual RDF Enrichment:** For each entity URI, a **2-hop graph traversal** is executed via SPARQL CONSTRUCT queries. This retrieves not only the direct (1-hop) `subject-predicate-object` triples for the entity but also the key ontological properties of its object entities. This creates a richer, more contextually complete RDF representation than a simple 1-hop query.
*   **Step C: Multi-Source Text Aggregation:** To foster a robust and multilingual understanding, all available language abstracts (`rdfs:comment`) are retrieved for each entity. Furthermore, placeholders for LLM-based augmentation are included to generate diverse, associative text variants from the primary English abstract, significantly increasing the training data's conceptual breadth.
*   **Step D: Contrastive Sample Generation:** For each text variant, a triplet of samples is generated:
    1.  **Anchor:** The original text paired with its enriched, factually correct RDF graph.
    2.  **Positive:** A paraphrased version of the anchor text paired with the same correct RDF graph.
    3.  **Negative:** A hard negative sample generated via **entity swapping**. A random object URI in the anchor's RDF graph is replaced with another URI of the same ontological type. This change is propagated to both the RDF string and the corresponding natural language text.

**2.3. Final Data Schema**
The resulting Apache Iceberg table maintains a decoupled schema for queryability and clarity.
| Column Name | Data Type | Description |
|---|---|---|
| `anchor_text` | `STRING` | The clean, natural language anchor text (in one of multiple languages). |
| `anchor_rdf` | `STRING` | The enriched Turtle RDF string for the anchor. |
| `positive_text`| `STRING` | The paraphrased version of the anchor text. |
| `negative_text`| `STRING` | The factually corrupted version of the anchor text. |
| `negative_rdf` | `STRING` | The factually corrupted RDF string. |
| `subject_uri` | `STRING` | The canonical DBpedia URI for the anchor's subject. |
| `subject_uri_id` | `INTEGER` | A unique integer ID corresponding to the `subject_uri`. |

### **3. Methodology: Model and Training**

**3.1. Graph-Aware Tokenization**
A custom tokenizer is trained from scratch using the Hugging Face `tokenizers` library on a corpus sampled from the generated dataset. A `WordPiece` model is used, with two critical configurations: `lowercase=False` is set to preserve the case-sensitivity of RDF URIs, and custom boundary tokens (`<RDF>`, `</RDF>`) are added to the vocabulary to allow the model to distinguish between the text and RDF modalities in the concatenated input.

**3.2. Model Architecture**
The system is a **Dual Encoder** architecture, specifically implemented as a **Triplet Network**, designed for multi-task learning.
*   **Shared-Weight Transformer Encoder:** The core of the model is a Transformer encoder. A single set of weights is used for this component. During training, the Anchor, Positive, and Negative samples are all processed by this same encoder, ensuring their output embeddings exist within a single, consistent latent space, which is a prerequisite for metric learning.
*   **Classification Head:** A linear layer is placed on top of the Transformer Encoder's output. It takes the final hidden state of the `[CLS]` token from the Anchor sample as its input and produces a logit distribution across the entire vocabulary of known Subject URIs.

Additional focused specifications:

- Knowledge-Aware Contrastive Regularizer (KACR): detailed spec, loss variants, PyTorch snippets, and experiment protocol are in [`KACR.md`](KACR.md).
- Subject ID & Multi-Domain URI strategy: canonicalization, alias mapping, schema changes, and migration notes are in [`Subject_IDs_MultiDomain.md`](Subject_IDs_MultiDomain.md).
- Dynamic Negative Hardening (DNH): curriculum and sampler for increasing negative difficulty during training are in [`DNH.md`](DNH.md).
- Multi-Hop Semantic Consistency (MHSC): loss variants, sampling strategies, and experiments are in [`MHSC.md`](MHSC.md).

**3.3. Multi-Task Training Objective**
The model's weights are optimized by minimizing a composite loss function derived from two simultaneous tasks.
*   **Task A: Contrastive Learning (Triplet Margin Loss):** This objective structures the embedding space based on factual consistency. Given an Anchor embedding `A`, a Positive `P`, and a Negative `N` from the shared-weight encoder, the loss is `L_triplet = max(d(A, P) - d(A, N) + m, 0)`, where `d(x, y)` is the Euclidean distance and `m` is a scalar margin. This forces the model to learn a representation where factually inconsistent samples are geometrically distant from consistent ones.
*   **Task B: Subject URI Classification (Cross-Entropy Loss):** This objective trains the model to explicitly link text to its canonical entity. The loss is calculated between the logits from the classification head and the ground-truth `subject_uri_id` of the anchor sample.
*   **Composite Loss:** The total loss is a weighted sum: `L_total = α * L_classification + (1 - α) * L_triplet`, where `α` is a balancing hyperparameter.

**3.4. Training Procedure**
The model is trained using a custom Hugging Face `Trainer`. Data is streamed efficiently from the S3 Iceberg table using a custom dataset loading script. In each step, the data loader concatenates the RDF and text fields for each sample before tokenization. The composite loss is calculated from the model's outputs and a single backpropagation step updates the weights of both the shared encoder and the classification head.

### **4. Expected Outcomes and Capabilities**
The fully trained KG-CAE model produces two distinct and powerful outputs from a single input text:

1.  **Predicted Subject URI:** The classification head outputs the most probable canonical URI for the main entity discussed in the text. This provides a direct, unambiguous, and verifiable semantic identifier that serves as an entry point into a global knowledge graph.
2.  **Contextual Embedding:** The encoder outputs a high-dimensional vector whose position in the latent space is determined by the factual content of the input.

This dual-output mechanism enables the following capabilities:
*   **Factual Consistency Assessment:** The Euclidean distance between the embedding of a new statement and the embedding of a known-good anchor for the same subject serves as a score for factual consistency. A larger distance indicates a higher probability of factual deviation.
*   **High-Fidelity Entity Linking:** The model directly resolves ambiguous natural language mentions to their canonical identifiers in a knowledge base.
*   **Semantically and Factually-Aware Retrieval:** Vector-based searches within the embedding space will retrieve documents based not just on topical similarity, but also on their alignment with the factual structure of the knowledge graph.

For a research-focused evaluation protocol, datasets, metrics, and reproducibility checklist, see the companion document: [Research_Evaluation.md](Research_Evaluation.md).

Next steps (quick summary)

- Short-term: add analysis scripts (`prototype_analysis.py`, `hop_precompute.py`, `calibration_analysis.py`) to compute prototypes, hop distances, and calibration diagnostics.
- Medium-term: implement PyTorch loss snippets and ablation runners for KACR, MHSC, UCLR, and DNH; create reproducible experiment configs (`example_experiment.yaml`).
- Bibliography: compile `references.bib` and optionally resolve DOIs/arXiv links (requires permission).
- Publication plan: follow the experiments, figures, and timelines in `RESEARCH_PUBLICATION_PLAN.md` for a paper-oriented execution path.

See `NEXT_STEPS.md` for a detailed, prioritized roadmap and actionable tasks.

### **5. Conclusion**
The Knowledge-Grounded Contrastive Autoencoder presents a significant step toward creating more reliable and interpretable language models. By redefining the semantic ID as a verifiable link to a symbolic knowledge graph and training the model with a fact-driven, multi-task objective, we create an encoder that is natively grounded in a factual reality. This architecture provides a robust and scalable framework for bridging the gap between statistical and symbolic AI, paving the way for downstream applications in fact-checking, knowledge base augmentation, and trustworthy question-answering systems.