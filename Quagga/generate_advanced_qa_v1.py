import os
import json
import wikipedia
import google.generativeai as genai
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm
import logging
from typing import List, Dict, Any, Optional

# --- Configuration ---
# IMPORTANT: Set your Google API key as an environment variable
# export GEMINI_API_KEY='YOUR_API_KEY'
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    exit()

ARCO_SPARQL_ENDPOINT = "https://dati.beniculturali.it/sparql"
DBPEDIA_SPARQL_ENDPOINT = "http://dbpedia.org/sparql"
USER_AGENT = "AdvancedQAGen/0.1 (Educational Script)"

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SPARQL Management ---
def execute_sparql_query(endpoint: str, query: str) -> Optional[List[Dict[str, Any]]]:
    """Executes a SPARQL query against a given endpoint."""
    try:
        sparql = SPARQLWrapper(endpoint)
        sparql.setReturnFormat(JSON)
        sparql.agent = USER_AGENT
        sparql.setQuery(query)
        results = sparql.query().convert()
        return results.get("results", {}).get("bindings", [])
    except Exception as e:
        logging.error(f"SPARQL query failed for endpoint {endpoint}: {e}")
        logging.debug(f"Failed query:\n{query}")
        return None

# --- Core Logic Functions ---

def get_wikipedia_summary(entity_label: str) -> Optional[str]:
    """Fetches the summary of a Wikipedia page."""
    try:
        # auto_suggest=False is more reliable for exact matches
        summary = wikipedia.summary(entity_label, sentences=5, auto_suggest=False)
        logging.info(f"Successfully fetched Wikipedia summary for '{entity_label}'.")
        return summary
    except wikipedia.exceptions.PageError:
        logging.warning(f"Wikipedia page not found for '{entity_label}'.")
    except wikipedia.exceptions.DisambiguationError as e:
        logging.warning(f"Disambiguation error for '{entity_label}': {e.options[:3]}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching from Wikipedia: {e}")
    return None


def get_arco_schema_for_entity(entity_uri: str) -> str:
    """Queries ArCo to discover the 'data shape' or available properties for an entity."""
    logging.info(f"Fetching ArCo schema for entity: {entity_uri}")
    query = f"""
        SELECT DISTINCT ?p_label ?o_type_label WHERE {{
          <{entity_uri}> ?p ?o .
          OPTIONAL {{
            ?p rdfs:label ?p_label_raw .
            FILTER(LANG(?p_label_raw) = 'it' || LANG(?p_label_raw) = 'en')
          }}
          OPTIONAL {{
            ?o a ?o_type .
            ?o_type rdfs:label ?o_type_label_raw .
            FILTER(LANG(?o_type_label_raw) = 'it' || LANG(?o_type_label_raw) = 'en')
          }}
          BIND(COALESCE(?p_label_raw, REPLACE(STR(?p), ".*[/#]", "")) AS ?p_label)
          BIND(COALESCE(?o_type_label_raw, "") AS ?o_type_label)
        }} LIMIT 20
    """
    results = execute_sparql_query(ARCO_SPARQL_ENDPOINT, query)
    if not results:
        return "No specific properties found."

    schema_lines = []
    for res in results:
        prop = res.get('p_label', {}).get('value', 'N/A')
        obj_type = res.get('o_type_label', {}).get('value', '')
        line = f"- Property: `{prop}`"
        if obj_type:
            line += f", connects to an object of type: `{obj_type}`"
        schema_lines.append(line)
        
    return "\n".join(sorted(list(set(schema_lines))))


def generate_qa_pairs_with_gemini(entity_label: str, wiki_summary: str, arco_schema: str) -> Optional[List[Dict[str, str]]]:
    """Generates QA pairs using the Gemini API based on the provided context."""
    logging.info(f"Prompting Gemini for QA pairs for '{entity_label}'...")

    prompt = f"""
    You are an expert in Italian cultural heritage and a helpful assistant for creating educational datasets.
    Your task is to generate pairs of (natural language question, SPARQL query) about a specific cultural entity.

    **Primary Goal:**
    Generate creative, high-quality questions based on the Wikipedia summary that can be answered **strictly** using the available ArCo data schema.

    **Constraints:**
    1.  The SPARQL query MUST be executable against the ArCo knowledge graph.
    2.  The query MUST ONLY use properties and relationships listed in the 'Available ArCo Data Schema'.
    3.  The question must be natural, interesting, and directly answerable by the SPARQL query.
    4.  Generate 2-3 diverse questions.

    ---
    **Context:**

    **Entity:** {entity_label}

    **Wikipedia Summary:**
    {wiki_summary}

    **Available ArCo Data Schema for this entity:**
    {arco_schema}

    ---
    **Prefixes for SPARQL (use these):**
    PREFIX cis: <http://dati.beniculturali.it/cis/>
    PREFIX clvapit: <https://wids.org/italia/onto/CLV/>
    PREFIX smapit: <https://w3id.org/italia/onto/SM/>
    PREFIX l0: <https://w3id.org/italia/onto/l0/>
    PREFIX accessCondition: <https://w3id.org/arco/ontology/access-condition/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    ---
    **Output Format (Strict JSON list of objects):**
    [
      {{
        "question": "A clear, natural language question.",
        "sparql_query": "A complete and correct SPARQL query."
      }}
    ]

    ---
    **Generated Output:**
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        # Clean up the response from markdown code blocks if present
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        return json.loads(cleaned_response)
    except Exception as e:
        logging.error(f"Failed to generate or parse response from Gemini: {e}")
        logging.debug(f"Gemini raw response: {response.text if 'response' in locals() else 'N/A'}")
        return None

def main():
    """Main execution function to run the demonstration."""
    
    # --- Define our example entities ---
    # We provide the ArCo URI and the label to search on Wikipedia
    example_entities = [
        {
            "label": "Uffizi Gallery", 
            "arco_uri": "http://dati.beniculturali.it/mibact/luoghi/resource/CulturalInstituteOrSite/101341"
        },
        {
            "label": "Colosseum",
            "arco_uri": "http://dati.beniculturali.it/mibact/luoghi/resource/CulturalInstituteOrSite/102921"
        },
    ]

    final_verified_pairs = []

    for entity in example_entities:
        print("\n" + "="*50)
        logging.info(f"Processing Entity: {entity['label']}")
        print("="*50)

        # 1. Get Wikipedia Summary
        summary = get_wikipedia_summary(entity['label'])
        if not summary:
            continue

        # 2. Get ArCo Schema
        schema = get_arco_schema_for_entity(entity['arco_uri'])
        if not schema:
            continue
        
        # 3. Generate QA pairs with Gemini
        generated_pairs = generate_qa_pairs_with_gemini(entity['label'], summary, schema)
        if not generated_pairs:
            continue

        # 4. Verify each generated pair
        logging.info(f"Verifying {len(generated_pairs)} pairs generated by Gemini...")
        for pair in tqdm(generated_pairs, desc=f"Verifying {entity['label']}"):
            query = pair.get("sparql_query")
            if not query:
                continue

            # This is the crucial step: check if the LLM-generated query actually works
            results = execute_sparql_query(ARCO_SPARQL_ENDPOINT, query)
            if results is not None and len(results) > 0:
                logging.info(f"  -> VERIFIED: '{pair['question']}'")
                final_verified_pairs.append(pair)
            else:
                logging.warning(f"  -> REJECTED: Query for '{pair['question']}' returned no results or failed.")

    # --- Final Output ---
    print("\n" + "="*50)
    print("      FINAL VERIFIED QUESTION-ANSWER PAIRS")
    print("="*50 + "\n")

    if not final_verified_pairs:
        print("No verifiable QA pairs were generated.")
    else:
        # Pretty print the final JSON
        print(json.dumps(final_verified_pairs, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()