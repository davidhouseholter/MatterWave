# Graph-Aware Foundational Model - Data Generation Pipeline

This project contains the complete data generation pipeline for creating a training dataset for a foundational model. The goal is to create a dataset that bridges the gap between unstructured natural language and the structured knowledge of a graph (DBpedia).

The pipeline discovers entities from DBpedia, fetches their details, generates positive and negative training samples, and stores the final dataset in a local Apache Iceberg warehouse. A simple web application is included to visualize the generated data.

## Project Structure

- `discover_entities.py`: A script to crawl DBpedia categories and discover relevant entity URIs.
- `generate_dataset_from_uris.py`: The main script to process a list of URIs, generate training triplets (anchor, positive, negative), and save them to an Iceberg table.
- `app.py`: A FastAPI web application to inspect and visualize the data stored in the Iceberg table.
- `templates/index.html`: The HTML template for the web application.
- `iceberg-data/`: The default directory for the local Iceberg warehouse and data cache.

## Getting Started

### Prerequisites

- Python 3.8+
- An internet connection to query the DBpedia SPARQL endpoint.

### Installation

1.  Clone the repository.
2.  It is recommended to create a virtual environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3.  Install the required Python packages:
    ```bash
    pip install pandas tqdm SPARQLWrapper "pyiceberg[pyarrow]" fastapi uvicorn jinja2 rdflib
    ```

## Usage

The data generation process is a two-step command-line workflow, followed by an optional visualization step.

### Step 1: Discover DBpedia Entities

First, run `discover_entities.py` to generate a list of entity URIs from a root category in DBpedia.

```bash
# Example: Crawl the "Physics" category, 1 level deep
python discover_entities.py --category "Physics" --depth 1 --output physics_entities.json
```

This will create a `physics_entities.json` file containing the discovered URIs. For a quick test, you can use the provided `test_uri.json`.

### Step 2: Generate the Dataset

Next, run `generate_dataset_from_uris.py` to process the URI list and build the Iceberg table. This script reads the JSON file from the previous step, fetches data for each URI, generates negative samples, and writes the results to `./iceberg-data`.

```bash
# Use the file generated in the previous step
python generate_dataset_from_uris.py --input physics_entities.json --verbose

# Or run with the small test file
python generate_dataset_from_uris.py --input test_uri.json --verbose
```
The `--verbose` flag is optional but recommended to see the process in detail.

### Step 3: Visualize the Data

Once the dataset is generated, you can launch the web application to inspect it.

```bash
uvicorn app:app --reload
```

Navigate to `http://127.0.0.1:8000` in your web browser to see the data dashboard. The application loads the data from the Iceberg table and provides summary statistics and a browsable view of the records.

## How It Works

The core of the project is the dataset generation script, which performs the following for each entity URI:

1.  **Data Fetching**: It queries the DBpedia SPARQL endpoint to get a multi-lingual abstract (`anchor_text`) and a 2-hop RDF graph context (`anchor_rdf`).
2.  **Positive Sample Generation**: A paraphrased version of the anchor text is created as a `positive_text` (currently a placeholder).
3.  **Negative Sample Generation**: A "hard negative" is created by finding an entity in the `anchor_rdf`, replacing it with another entity of the same type, and reflecting this change in both the RDF (`negative_rdf`) and the text (`negative_text`).
4.  **LLM Augmentation**: Placeholder functions demonstrate how Large Language Models could be used to generate additional associative texts, increasing the dataset's richness.
5.  **Storage**: All generated data is written to an Apache Iceberg table in a local directory, providing a structured and scalable storage solution.
