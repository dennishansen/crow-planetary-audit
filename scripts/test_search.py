import sys
import json
import time
from ddgs import DDGS

def run_search(query):
    # Try with different keywords if the first one fails
    for attempt in range(3):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if results:
                    print(json.dumps(results, indent=2))
                    return
                else:
                    # If no results, try a broader query on the next attempt
                    query = " ".join(query.split()[:3]) 
                    time.sleep(1)
        except Exception as e:
            if attempt == 2:
                print(json.dumps({"status": "error", "message": str(e), "query": query}))
            time.sleep(1)
    
    print(json.dumps({"status": "no_results", "query": query}))

if __name__ == "__main__":
    search_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Sundarbans carbon"
    run_search(search_query)
