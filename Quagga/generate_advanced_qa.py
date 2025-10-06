import os
import json
import wikipedia
import google.generativeai as genai
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
from tqdm import tqdm
import logging
from typing import List, Dict, Any, Optional

# --- Configuration ---
# Set your Google API key as an environment variable:
# export GEMINI_API_KEY='YOUR_API_KEY'
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("FATAL ERROR: GEMINI_API_KEY environment variable not set. Exiting.")
    exit()

# Set DEBUG=true in your environment to enable detailed file logging
DEBUG_MODE = os.environ.get("DEBUG", "false").lower() == "true"
LOG_FILE = "generation_debug.log"

ARCO_SPARQL_ENDPOINT = "https://dati.beniculturali.it/sparql"
DBPEDIA_SPARQL_ENDPOINT = "http://dbpedia.org/sparql"
USER_AGENT = "AdvancedQAGen/0.2 (Debug Enabled; Educational Script)"

# --- Setup Logging ---
# Console logger (for high-level info)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# File logger (for detailed debug traces)
file_handler = logging.FileHandler(LOG_FILE, mode='w') # 'w' to overwrite the log each run
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))

# Root logger configuration
logger = logging.getLogger()
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
logger.handlers.clear() # Clear any default handlers
logger.addHandler(console_handler)
if DEBUG_MODE:
    logger.addHandler(file_handler)
    logger.info(f"DEBUG mode is ON. Detailed logs will be written to {LOG_FILE}")


# --- SPARQL Management ---
def execute_sparql_query(endpoint: str, query: str) -> (Optional[List[Dict[str, Any]]], str):
    """
    Executes a SPARQL query.
    Returns a tuple: (results, error_message).
    On success, results is a list and error_message is empty.
    On failure, results is None and error_message contains the reason.
    """
    try:
        sparql = SPARQLWrapper(endpoint)
        sparql.setReturnFormat(JSON)
        sparql.agent = USER_AGENT
        sparql.setQuery(query)
        logger.debug(f"Executing SPARQL query on {endpoint}:\n{query}")
        results = sparql.query().convert()
        bindings = results.get("results", {}).get("bindings", [])
        return bindings, ""
    except QueryBadFormed as e:
        error_msg = f"SPARQL QueryBadFormed: {e}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"SPARQL query failed for endpoint {endpoint}: {e}"
        logger.error(error_msg)
        return None, error_msg

# --- Core Logic Functions ---

def get_wikipedia_summary(entity_label: str) -> Optional[str]:
    """Fetches the summary of a Wikipedia page."""
    logger.debug(f"Attempting to fetch Wikipedia summary for '{entity_label}'")
    try:
        summary = wikipedia.summary(entity_label, sentences=5, auto_suggest=False)
        logger.info(f"Successfully fetched Wikipedia summary for '{entity_label}'.")
        return summary
    except wikipedia.exceptions.PageError:
        logger.warning(f"Wikipedia page not found for '{entity_label}'.")
    except wikipedia.exceptions.DisambiguationError as e:
        logger.warning(f"Disambiguation error for '{entity_label}': {e.options[:3]}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching from Wikipedia: {e}")
    return None


def get_arco_schema_for_entity(entity_uri: str) -> str:
    """Queries ArCo to discover the 'data shape' or available properties for an entity."""
    logger.info(f"Fetching ArCo schema for entity: {entity_uri}")
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
    results, error = execute_sparql_query(ARCO_SPARQL_ENDPOINT, query)
    if error or not results:
        logger.warning(f"Could not retrieve ArCo schema for {entity_uri}. Error: {error}")
        return "No specific properties found."

    schema_lines = []
    for res in results:
        prop = res.get('p_label', {}).get('value', 'N/A')
        obj_type = res.get('o_type_label', {}).get('value', '')
        line = f"- Property: `{prop}`"
        if obj_type:
            line += f", connects to an object of type: `{obj_type}`"
        schema_lines.append(line)
    
    schema_str = "\n".join(sorted(list(set(schema_lines))))
    logger.debug(f"Generated ArCo Schema for {entity_uri}:\n{schema_str}")
    return schema_str


def generate_qa_pairs_with_gemini(entity_label: str, wiki_summary: str, arco_schema: str, entity_uri: str) -> Optional[List[Dict[str, str]]]:
    """Generates QA pairs using the Gemini API based on the provided context."""
    logger.info(f"Prompting Gemini for QA pairs for '{entity_label}'...")

    prompt = f"""
    You are an expert in Italian cultural heritage and a helpful assistant for creating educational datasets.
    Your task is to generate pairs of (natural language question, SPARQL query) about a specific cultural entity.

    **Primary Goal:**
    Generate creative, high-quality questions based on the Wikipedia summary that can be answered **strictly** using the available ArCo data schema.

    **Instructions & Constraints:**
    1.  The SPARQL query MUST be executable against the ArCo knowledge graph. Use the provided entity URI `{entity_uri}` as the subject.
    2.  The query MUST ONLY use properties, relationships, and types listed in the 'Available ArCo Data Schema'. Do not invent properties.
    3.  The question must be natural, interesting, and directly answerable by the SPARQL query you provide.
    4.  Generate 2-3 diverse questions.

    ---
    **Context:**

    **Entity Name:** {entity_label}
    **Entity URI:** {entity_uri}

    **Wikipedia Summary:**
    {wiki_summary}

    **Available ArCo Data Schema for this entity:**
    {arco_schema}

    ---
    **Prefixes for SPARQL (use these):**
    PREFIX cis: <http://dati.beniculturali.it/cis/>
    PREFIX clvapit: <https://w3id.org/italia/onto/CLV/>
    PREFIX smapit: <https://w3id.org/italia/onto/SM/>
    PREFIX l0: <https://w3id.org/italia/onto/l0/>
    PREFIX accessCondition: <https://w3id.org/arco/ontology/access-condition/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

    ---
    **Output Format (Strict JSON list of objects):**
    [
      {{
        "question": "A clear, natural language question.",
        "sparql_query": "A complete and correct SPARQL query using the provided prefixes and entity URI."
      }}
    ]

    ---
    **Generated Output:**
    """
    
    logger.debug(f"--- PROMPT SENT TO GEMINI FOR '{entity_label}' ---\n{prompt}\n---------------------------------")
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        logger.debug(f"--- RAW RESPONSE FROM GEMINI FOR '{entity_label}' ---\n{response.text}\n---------------------------------")
        
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        return json.loads(cleaned_response)
    except Exception as e:
        logger.error(f"Failed to generate or parse response from Gemini: {e}")
        return None

def main():
    """Main execution function to run the demonstration."""
    
    # --- Define our example entities ---
    example_entities = [
        {
            "label": "Uffizi Gallery", 
            "arco_uri": "http://dati.beniculturali.it/mibact/luoghi/resource/CulturalInstituteOrSite/101341"
        },
        {
            "label": "Colosseum",
            "arco_uri": "http://dati.beniculturali.it/mibact/luoghi/resource/CulturalInstituteOrSite/102921"
        },
        {
            "label": "Royal Palace of Caserta",
            "arco_uri": "http://dati.beniculturali.it/mibact/luoghi/resource/CulturalInstituteOrSite/100067" # Reggia di Caserta
        }
    ]

    final_verified_pairs = []

    for entity in example_entities:
        logger.info("="*50)
        logger.info(f"Processing Entity: {entity['label']}")
        logger.info("="*50)

        summary = get_wikipedia_summary(entity['label'])
        if not summary:
            continue

        schema = get_arco_schema_for_entity(entity['arco_uri'])
        if not schema:
            continue
        
        generated_pairs = generate_qa_pairs_with_gemini(entity['label'], summary, schema, entity['arco_uri'])
        if not generated_pairs:
            continue

        logger.info(f"Verifying {len(generated_pairs)} pairs generated by Gemini for '{entity['label']}'...")
        for pair in generated_pairs:
            question = pair.get("question", "N/A")
            query = pair.get("sparql_query")
            
            if not query:
                logger.warning(f"  -> REJECTED: Gemini output for '{question}' did not contain a 'sparql_query' key.")
                continue

            # This is the crucial step: check if the LLM-generated query actually works
            results, error_msg = execute_sparql_query(ARCO_SPARQL_ENDPOINT, query)
            
            if error_msg:
                rejection_reason = f"Query failed with an error: {error_msg}"
                logger.warning(f"  -> REJECTED: '{question}'. Reason: {rejection_reason}")
                logger.debug(f"Rejected Query:\n{query}")
            elif results is not None and len(results) > 0:
                logger.info(f"  -> VERIFIED: '{question}'")
                final_verified_pairs.append(pair)
            else: # results is empty list
                rejection_reason = "Query returned no results."
                logger.warning(f"  -> REJECTED: '{question}'. Reason: {rejection_reason}")
                logger.debug(f"Rejected Query:\n{query}")
                

    # --- Final Output ---
    logger.info("="*50)
    logger.info("      FINAL VERIFIED QUESTION-ANSWER PAIRS")
    logger.info("="*50)

    if not final_verified_pairs:
        logger.info("No verifiable QA pairs were generated across all entities.")
    else:
        # Pretty print the final JSON to the console
        print(json.dumps(final_verified_pairs, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()