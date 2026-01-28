import sys
from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        keywords = "Sundarbans mangrove carbon project Verra Gold Standard project developer"
        results = list(ddgs.text(keywords, max_results=10))
        for r in results:
            print(f"TITLE: {r['title']}\nURL: {r['href']}\n")
except Exception as e:
    print(f"Error: {e}")
