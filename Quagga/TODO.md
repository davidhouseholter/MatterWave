Excellent. This is the perfect first step. Focusing on a specific, rich domain like Social Sciences and Humanities (SSH) makes the project tangible and allows us to create a high-quality, targeted dataset. Building a dataset of (Natural Language Question, SPARQL Query) pairs is a classic and powerful approach for training text-to-SPARQL models, which is a core part of your larger KG-CAE vision.

Let's design a structured plan to build this dataset.

### Project Phase 1: SSH Question-Answering Dataset Generation

The goal is to create a high-quality dataset where each entry links a natural language question about an SSH topic to a SPARQL query that can answer it using DBpedia.

---

### Step 1: Define the Scope and Seed Entities

We need to start with a curated list of entities from the SSH domain. This ensures our dataset has both breadth (covering different fields) and depth (exploring relationships). We can use our Mermaid Diagram as a guide.

**Action Plan:**

1.  **Identify Core DBpedia Categories:** We'll map the fields from our diagram to DBpedia categories.
    *   **Philosophy:** `dbc:Philosophers`, `dbc:Schools_of_philosophy`, `dbc:Philosophical_concepts`
    *   **Sociology:** `dbc:Sociologists`, `dbc:Sociological_theories`
    *   **Political Science:** `dbc:Political_scientists`, `dbc:Political_ideologies`, `dbc:Treaties`
    *   **History:** `dbc:Historians`, `dbc:Historical_events`, `dbc:Empires`
    *   **Literature:** `dbc:Writers`, `dbc:Literary_movements`, `dbc:Fictional_characters`
    *   **Art History:** `dbc:Artists`, `dbc:Art_movements`, `dbc:Museums`

2.  **Script for Entity Harvesting:**
    *   Write a Python script using `SPARQLWrapper` to query the DBpedia endpoint.
    *   The script will iterate through the list of seed categories and pull, for example, the top 500 entities from each (ranked by the number of incoming Wikipedia links, a good proxy for notability).
    *   **Output:** A set of JSON files, one for each category (e.g., `philosophers.json`, `artists.json`), containing entity URIs and their English labels.

---

### Step 2: Design Question-SPARQL Templates

This is the core of the data generation. We'll create parameterized templates that can be filled in with the entities we harvested. We should categorize these templates by the *type* of question they ask.

**A. "Simple" Templates (Fact Retrieval - 1-hop):**

*   **Template Type:** **Property Value Question**
    *   **NL Template:** `When was [ENTITY_LABEL] born?` | `What is the birth date of [ENTITY_LABEL]?`
    *   **SPARQL Template:**
        ```sparql
        SELECT ?birthDate WHERE {
          dbr:[ENTITY_URI] dbo:birthDate ?birthDate .
        }
        ```
*   **Template Type:** **Existence Question (ASK)**
    *   **NL Template:** `Was [ENTITY_LABEL_1] influenced by [ENTITY_LABEL_2]?`
    *   **SPARQL Template:**
        ```sparql
        ASK WHERE {
          dbr:[ENTITY_URI_1] dbo:influencedBy dbr:[ENTITY_URI_2] .
        }
        ```
*   **Template Type:** **List Property Values**
    *   **NL Template:** `What are the notable works of [ENTITY_LABEL]?` | `List the books written by [ENTITY_LABEL].`
    *   **SPARQL Template:**
        ```sparql
        SELECT ?work ?workLabel WHERE {
          dbr:[ENTITY_URI] dbo:notableWork ?work .
          ?work rdfs:label ?workLabel .
          FILTER(lang(?workLabel) = 'en')
        }
        ```

**B. "Complex" Templates (Relational & Multi-hop):**

*   **Template Type:** **Intersection / Shared Property (2-hop)**
    *   **NL Template:** `Which philosophers were influenced by both [ENTITY_LABEL_1] and [ENTITY_LABEL_2]?`
    *   **SPARQL Template:**
        ```sparql
        SELECT ?thinker ?name WHERE {
          ?thinker dbo:influencedBy dbr:[ENTITY_URI_1] .
          ?thinker dbo:influencedBy dbr:[ENTITY_URI_2] .
          ?thinker rdfs:label ?name .
          FILTER(lang(?name) = 'en')
        }
        ```
*   **Template Type:** **Counting Question**
    *   **NL Template:** `How many students did [ENTITY_LABEL] teach?`
    *   **SPARQL Template:**
        ```sparql
        SELECT (COUNT(?student) as ?count) WHERE {
          ?student dbo:influencedBy dbr:[ENTITY_URI] .
        }
        ```
*   **Template Type:** **Comparative/Superlative Question**
    *   **NL Template:** `Who is the earliest known philosopher from the Milesian school?`
    *   **SPARQL Template:**
        ```sparql
        SELECT ?philosopher ?name WHERE {
          ?philosopher dbo:school dbr:Milesian_school ;
                       dbo:birthDate ?birthDate ;
                       rdfs:label ?name .
          FILTER(lang(?name) = 'en')
        } ORDER BY ASC(?birthDate) LIMIT 1
        ```

---

### Step 3: Automate the Generation Pipeline

Now we combine the entities and templates to generate the full dataset.

**Action Plan:**

1.  **Develop the Generation Script:**
    *   The script will load the harvested entities (`philosophers.json`, etc.).
    *   It will iterate through each template.
    *   For a given template, it will sample the required number of entities of the correct type (e.g., for `dbo:influencedBy`, it needs two philosophers).
    *   It will then instantiate both the NL and SPARQL templates by filling in the entity labels and URIs.
    *   **Crucial Step: Verification.** Before saving a pair, the script will execute the generated SPARQL query against the live DBpedia endpoint. If the query returns an empty or invalid result, the pair is discarded. This ensures our dataset only contains "answerable" questions.

2.  **Introduce Linguistic Diversity (Paraphrasing):**
    *   To make the model more robust, we need multiple versions of each question.
    *   **Option A (Simple):** Manually create several NL variants for each template (as shown in the examples).
    *   **Option B (Advanced):** Use a pre-trained paraphrasing model (like a T5 fine-tuned for paraphrasing) to automatically generate variants of the instantiated NL questions. This dramatically increases dataset size and diversity.

---

### Step 4: Structure and Store the Dataset

We'll store the final, verified dataset in a structured, queryable format, just as planned in the original proposal.

**Proposed Schema:**

| Column Name | Data Type | Description | Example |
|---|---|---|---|
| `id` | `STRING` | A unique identifier for the Q&A pair. | `SSH-QA-000001` |
| `question` | `STRING` | The natural language question. | `Who did Plato teach?` |
| `sparql_query` | `STRING` | The executable SPARQL query. | `SELECT ?student... WHERE { ?student dbo:influencedBy dbr:Plato . }` |
| `question_template_id` | `STRING` | ID of the template used to generate it. | `list-influenced-by` |
| `domain` | `STRING` | The primary SSH domain. | `Philosophy` |
| `seed_entities` | `ARRAY<STRING>` | The DBpedia URIs used in the question. | `["dbr:Plato"]` |
| `answer_cardinality` | `INTEGER` | Number of rows in the query result. | `1` (for Aristotle) |

**Storage:**
*   Start with a simple `JSONL` or `CSV` file.
*   For the full project, loading this into an **Apache Iceberg table on S3** is the right long-term goal for versioning and scalability.

### Next Steps & Deliverables

1.  **Deliverable 1: Entity Lists.** A set of `.json` files containing curated URIs for each SSH sub-domain.
2.  **Deliverable 2: Template Library.** A YAML or JSON file defining the question-SPARQL templates. This makes the system modular and easy to expand.
3.  **Deliverable 3: Generation & Verification Scripts.** The core Python code that builds the dataset.
4.  **Deliverable 4: Version 0.1 of the SSH-QA Dataset.** The first iteration of the dataset, perhaps 10,000+ verified Q&A pairs, stored as `ssh-qa-v0.1.jsonl`.
