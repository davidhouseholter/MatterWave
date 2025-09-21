
import json
import argparse
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm

# --- Configuration ---
CONFIG = {
    "sparql_endpoint": "https://dbpedia.org/sparql",
    "user_agent": "KGEntityDiscoverer/1.0 (YourEmail@YourDomain.com)",
}

class EntityDiscoverer:
    """A simple crawler to discover entity URIs from DBpedia categories."""
    def __init__(self, config):
        self.config = config
        self.sparql = SPARQLWrapper(config["sparql_endpoint"], agent=config["user_agent"])
        self.sparql.setTimeout(30)
        self.sparql.setReturnFormat(JSON)
        self.seen_entities = set()

    def get_entities_from_category(self, category_name: str, depth_limit: int, current_depth: int = 0) -> set:
        """Recursively fetches a set of unique entity URIs from a DBpedia category."""
        if current_depth > depth_limit:
            return set()

        print(f"{'  ' * current_depth}[INFO] Crawling Category: '{category_name}' at depth {current_depth}")
        
        # Query for articles directly associated with this category
        query = f"""
        PREFIX dct: <http://purl.org/dc/terms/>
        SELECT DISTINCT ?article WHERE {{
            ?article dct:subject <http://dbpedia.org/resource/Category:{category_name.replace(" ", "_")}> .
            FILTER(STRSTARTS(STR(?article), "http://dbpedia.org/resource/"))
        }}
        """
        self.sparql.setQuery(query)
        
        try:
            results = self.sparql.query().convert()
        except Exception as e:
            print(f"[ERROR] SPARQL query failed for category {category_name}: {e}")
            return set()
            
        entities = {r["article"]["value"] for r in results["results"]["bindings"]}
        new_entities = entities - self.seen_entities
        self.seen_entities.update(new_entities)
        
        # If depth allows, find subcategories and recurse
        if current_depth < depth_limit:
            sub_query = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?subCategory WHERE {{
                ?subCategory skos:broader <http://dbpedia.org/resource/Category:{category_name.replace(" ", "_")}> .
            }}
            """
            self.sparql.setQuery(sub_query)
            try:
                sub_results = self.sparql.query().convert()
                for r in tqdm(sub_results["results"]["bindings"], desc=f"{'  ' * (current_depth+1)}Sub-categories", leave=False):
                    sub_cat_uri = r["subCategory"]["value"]
                    if "Category:" in sub_cat_uri:
                        sub_cat_name = sub_cat_uri.split("Category:")[-1].replace("_", " ")
                        new_entities.update(self.get_entities_from_category(sub_cat_name, depth_limit, current_depth + 1))
            except Exception as e:
                print(f"[ERROR] SPARQL sub-category query failed: {e}")

        return new_entities

def main():
    parser = argparse.ArgumentParser(description="Discover DBpedia entity URIs from a starting category.")
    parser.add_argument("--category", type=str, required=True, help="The starting DBpedia category (e.g., 'Science').")
    parser.add_argument("--depth", type=int, default=1, help="How many levels of sub-categories to crawl.")
    parser.add_argument("--output", type=str, default="discovered_entities.json", help="The output JSON file to save the list of URIs.")
    args = parser.parse_args()

    print(f"--- Starting Entity Discovery ---")
    print(f"Root Category: {args.category}, Depth: {args.depth}")
    
    discoverer = EntityDiscoverer(CONFIG)
    all_entities = list(discoverer.get_entities_from_category(args.category, args.depth))

    print(f"\n[SUCCESS] Discovered {len(all_entities)} unique entities.")

    with open(args.output, 'w') as f:
        json.dump(all_entities, f, indent=2)

    print(f"List of URIs saved to '{args.output}'.")

if __name__ == "__main__":
    main()
