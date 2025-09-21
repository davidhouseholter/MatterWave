
import os
import random
import time
import re
import json
import argparse
import pandas as pd
from tqdm import tqdm
from SPARQLWrapper import SPARQLWrapper, JSON

# Cloud and Iceberg specific imports
import pyarrow as pa
from pyiceberg.catalog import load_catalog

# --- Configuration ---
CONFIG = {
    # --- Input and Output ---
    "s3_warehouse": "s3://your-unique-bucket-name/iceberg-data", # IMPORTANT: Change to your S3 bucket URI.
    "iceberg_table_name": "dbpedia.physics_triplets_multilingual",

    # --- API & Networking ---
    "sparql_endpoint": "https://dbpedia.org/sparql",
    "user_agent": "KGFoundationalModelBuilder/1.0 (YourEmail@YourDomain.com)",
    
    # --- Data Generation ---
    "primary_language": "en",
}


def generate_paraphrase(text: str) -> str:
    """(Placeholder) Generates a paraphrased version of the text."""
    return "From a different perspective, " + text.lower()

def generate_llm_associations(title: str, description: str, num_rows=5) -> list[str]:
    """(Placeholder) Generates multiple associative text rows from a single resource."""
    return [
        f"Considering the historical context, {title} emerged as a significant concept following...",
        f"For a beginner, the most important thing to understand about {title} is that it relates to...",
        f"A deep technical dive into {title} reveals its dependency on the principles of...",
        f"The societal impact of {title} can be seen in its influence on...",
        f"An interesting and often debated aspect of {title} is...",
    ]

class DbpediaProcessor:
    """Handles fetching details and generating negative samples for a given list of entities."""
    def __init__(self, config, verbose: bool = False):
        self.config = config
        self.sparql = SPARQLWrapper(config["sparql_endpoint"], agent=config["user_agent"])
        self.sparql.setTimeout(30)
        self.verbose = verbose

    def get_entity_details(self, entity_uri: str) -> dict | None:
        entity_name = entity_uri.split("/")[-1].replace("_", " ")
        self.sparql.setReturnFormat(JSON)
        lang_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?comment WHERE {{ <{entity_uri}> rdfs:comment ?comment . }}
        """
        if self.verbose:
            print(f"  [DEBUG] Fetching comments for {entity_uri}", flush=True)
        self.sparql.setQuery(lang_query)
        try:
            results = self.sparql.query().convert()
            if self.verbose:
                print(f'  [DEBUG] Comment query returned {len(results["results"]["bindings"])} results.', flush=True)
        except Exception as e:
            if self.verbose:
                print(f"  [DEBUG] SPARQL comment query failed for {entity_uri}: {e}", flush=True)
            return None
        
        multilingual_texts = {}
        for r in results["results"]["bindings"]:
            comment_node = r["comment"]
            if "xml:lang" in comment_node and len(comment_node["value"]) > 150:
                multilingual_texts[comment_node["xml:lang"]] = comment_node["value"]
        
        if not multilingual_texts:
            if self.verbose:
                print(f"  [DEBUG] No suitable comments found for {entity_uri}", flush=True)
            return None

        if self.verbose:
            print(f"  [DEBUG] Found {len(multilingual_texts)} comments. Fetching RDF...", flush=True)
        self.sparql.setReturnFormat('turtle')
        rdf_query = f"""
        CONSTRUCT {{ <{entity_uri}> ?p1 ?o1 . ?o1 ?p2 ?o2 . }}
        WHERE {{
            <{entity_uri}> ?p1 ?o1 . FILTER(STRSTARTS(STR(?p1), "http://dbpedia.org/ontology/"))
            OPTIONAL {{ FILTER(ISURI(?o1) && STRSTARTS(STR(?o1), "http://dbpedia.org/resource/")) ?o1 ?p2 ?o2 . FILTER(STRSTARTS(STR(?p2), "http://dbpedia.org/ontology/")) }}
        }}"""
        self.sparql.setQuery(rdf_query)
        try:
            anchor_rdf = self.sparql.query().convert().decode('utf-8')
            if not anchor_rdf:
                if self.verbose:
                    print(f"  [DEBUG] RDF CONSTRUCT query returned no data for {entity_uri}", flush=True)
                return None
        except Exception as e:
            if self.verbose:
                print(f"[WARN] RDF CONSTRUCT query failed for {entity_uri}: {e}", flush=True)
            return None
        if self.verbose:
            print(f"  [DEBUG] Successfully fetched RDF for {entity_uri}", flush=True)
        return {"uri": entity_uri, "title": entity_name, "multilingual_texts": multilingual_texts, "rdf": anchor_rdf}

    def generate_negative_sample(self, anchor_text, anchor_rdf) -> dict | None:
        candidate_triples = re.findall(r"(dbo:\w+\s+dbr:[\w,-]+)", anchor_rdf)
        if not candidate_triples:
            return None

        # Filter for entities that are actually mentioned in the anchor text
        mentioned_candidate_triples = []
        for triple in candidate_triples:
            original_object_short = triple.split()[1]
            original_text_obj = original_object_short.split(':')[1].replace('_', ' ')
            if re.search(re.escape(original_text_obj), anchor_text, flags=re.IGNORECASE):
                mentioned_candidate_triples.append(triple)

        if not mentioned_candidate_triples:
            if self.verbose:
                print(f"    [DEBUG-NEG] No RDF entities were found mentioned in the text. Cannot create negative sample.", flush=True)
            return None
        
        for triple_to_corrupt in mentioned_candidate_triples:
            original_object_short = triple_to_corrupt.split()[1]
            original_object_uri = f"http://dbpedia.org/resource/{original_object_short.split(':')[1]}"
            self.sparql.setReturnFormat(JSON)
            
            type_query = f"SELECT ?type WHERE {{ <{original_object_uri}> a ?type . }}"
            if self.verbose:
                print(f"    [DEBUG-NEG] Attempting to replace: {original_object_uri}", flush=True)
            self.sparql.setQuery(type_query)
            try:
                results = self.sparql.query().convert()
            except Exception as e:
                if self.verbose:
                    print(f"    [DEBUG-NEG] Type query failed: {e}", flush=True)
                continue # Try next candidate triple

            types = [r["type"]["value"] for r in results["results"]["bindings"] if "ontology" in r["type"]["value"]]
            if not types:
                if self.verbose:
                    print(f"    [DEBUG-NEG] No ontology types found for {original_object_uri}", flush=True)
                continue # Try next candidate triple
            
            target_type = random.choice(types)
            replacement_query = f"""SELECT ?replacement WHERE {{ ?replacement a <{target_type}> . FILTER(?replacement != <{original_object_uri}>) }} LIMIT 10"""
            if self.verbose:
                print(f"    [DEBUG-NEG] Finding replacement of type {target_type}", flush=True)
            self.sparql.setQuery(replacement_query)
            try:
                results = self.sparql.query().convert()
            except Exception as e:
                if self.verbose:
                    print(f"    [DEBUG-NEG] Replacement query failed: {e}", flush=True)
                continue # Try next candidate triple

            if not results["results"]["bindings"]:
                if self.verbose:
                    print(f"    [DEBUG-NEG] No replacement entities found.", flush=True)
                continue # Try next candidate triple
                
            replacement_uri = random.choice(results["results"]["bindings"])["replacement"]["value"]
            replacement_short = f"dbr:{replacement_uri.split('/')[-1]}"
            negative_rdf = anchor_rdf.replace(original_object_short, replacement_short)
            
            original_text_obj = original_object_short.split(':')[1].replace('_', ' ')
            replacement_text_obj = replacement_short.split(':')[1].replace('_', ' ')
            
            # Use case-insensitive regex replacement with word boundaries and check if substitution happened
            negative_text, count = re.subn(r'\b' + re.escape(original_text_obj) + r'\b', replacement_text_obj, anchor_text, flags=re.IGNORECASE)
            
            if count > 0:
                if self.verbose:
                    print(f"    [DEBUG-NEG] Successfully replaced '{original_text_obj}' with '{replacement_text_obj}'", flush=True)
                return {"text": negative_text, "rdf": negative_rdf}
            else:
                if self.verbose:
                    print(f"    [DEBUG-NEG] Text replacement failed for '{original_text_obj}'. Trying next candidate.", flush=True)

        # If loop finishes without success
        return None


def save_to_iceberg(data: list, table_name: str, s3_warehouse_path: str):
    """Saves the processed data to an Iceberg table in S3 using the AWS Glue catalog."""
    if not data:
        print("[ERROR] No data generated. Aborting Iceberg write.")
        return
    
    print(f"\n[INFO] Saving {len(data)} rows to Iceberg table '{table_name}' at '{s3_warehouse_path}'...")
    df = pd.DataFrame(data)
    schema = pa.schema([ pa.field("anchor_text", pa.string()), pa.field("anchor_rdf", pa.string()), pa.field("positive_text", pa.string()), pa.field("negative_text", pa.string()), pa.field("negative_rdf", pa.string()), pa.field("subject_uri", pa.string()), pa.field("subject_uri_id", pa.int64()) ])
    arrow_table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    
    catalog_properties = {
        "type": "glue",
        "warehouse": s3_warehouse_path,
    }
    # Assumes AWS credentials are configured in the environment (e.g., via `aws configure`)
    catalog = load_catalog("aws", **catalog_properties)

    if '.' in table_name:
        namespace = table_name.rsplit('.', 1)[0]
        # In Glue, namespaces are databases.
        databases = [db['Name'] for db in catalog.list_namespaces()]
        if namespace not in databases:
            print(f"[INFO] Creating Glue database (namespace): {namespace}")
            catalog.create_namespace(namespace)

    if catalog.table_exists(table_name):
        print(f"[WARN] Table {table_name} already exists. Dropping and recreating.")
        catalog.drop_table(table_name)
    iceberg_table = catalog.create_table(table_name, schema)
    iceberg_table.append(arrow_table)
    print("[SUCCESS] Data successfully written to Iceberg table in S3 with AWS Glue catalog.")


def main():
    """Main execution function to run the data generation pipeline from a file."""
    parser = argparse.ArgumentParser(description="Generate a dataset from a list of DBpedia entity URIs.")
    parser.add_argument("--input", type=str, default="physics_entities.json", help="The input JSON file containing the list of URIs.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging.")
    args = parser.parse_args()

    print("--- Starting Dataset Generation from URI List ---")
    
    # --- PHASE 1: Load Entity URIs from File ---
    if not os.path.exists(args.input):
        print(f"[FATAL] Input file not found: {args.input}")
        print("Please run 'discover_entities.py' first to generate this file.")
        return
    
    with open(args.input, 'r', encoding='utf-8') as f:
        all_entities = json.load(f)
    print(f"[PHASE 1] Loaded {len(all_entities)} unique entities from '{args.input}'.")

    # --- PHASE 2: Generate multilingual triplet data for each entity ---
    print("\n[PHASE 2] Processing entities to generate triplet data...")
    processor = DbpediaProcessor(CONFIG, verbose=args.verbose)
    final_data = []
    uri_to_id = {uri: i for i, uri in enumerate(all_entities)}

    for entity_uri in tqdm(all_entities, desc="Processing Entities"):
        if args.verbose:
            print(f"\n[DEBUG] Processing URI: {entity_uri}", flush=True)
        details = processor.get_entity_details(entity_uri)
        if not details:
            if args.verbose:
                print(f"  [DEBUG] Skipping URI: No details found.", flush=True)
            continue

        texts_to_process = list(details["multilingual_texts"].items())
        primary_text = details["multilingual_texts"].get(CONFIG["primary_language"])
        if primary_text:
            llm_texts = generate_llm_associations(details["title"], primary_text)
            for text in llm_texts:
                texts_to_process.append((f"{CONFIG['primary_language']}_llm_assoc", text))

        for lang_code, anchor_text in texts_to_process:
            positive_text = generate_paraphrase(anchor_text)
            if args.verbose:
                print(f"  [DEBUG] Generating negative sample for lang '{lang_code}'...", flush=True)
            negative_data = processor.generate_negative_sample(anchor_text, details["rdf"])
            
            if negative_data:
                if args.verbose:
                    print(f"  [DEBUG] Negative sample generated.", flush=True)
                final_data.append({
                    "anchor_text": anchor_text, "anchor_rdf": details["rdf"], "positive_text": positive_text,
                    "negative_text": negative_data["text"], "negative_rdf": negative_data["rdf"],
                    "subject_uri": details["uri"], "subject_uri_id": uri_to_id[details["uri"]]
                })
            else:
                if args.verbose:
                    print(f"  [DEBUG] Failed to generate negative sample.", flush=True)
        
        time.sleep(0.1) # Be kind to the public SPARQL endpoint

    # --- PHASE 3: Write data to Iceberg/S3 ---
    print(f"\n[PHASE 3] Writing {len(final_data)} total rows to S3 Iceberg warehouse...")
    save_to_iceberg(final_data, CONFIG["iceberg_table_name"], CONFIG["s3_warehouse"])
    
    print("\n--- Dataset Generation Complete ---")


if __name__ == "__main__":
    main()
