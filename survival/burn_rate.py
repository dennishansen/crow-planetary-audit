import os
import json
from datetime import datetime

# Gemini 1.5 Pro approximate costs
COST_PER_1K_INPUT = 0.00125
COST_PER_1K_OUTPUT = 0.00375

def log_metabolism(input_tokens, output_tokens):
    cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + (output_tokens / 1000 * COST_PER_1K_OUTPUT)
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost
    }
    
    history_path = 'survival/metabolism.json'
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            history = json.load(f)
    else:
        history = []
        
    history.append(record)
    
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
        
    print(f"Metabolic cycle logged: ${cost:.4f}")

if __name__ == "__main__":
    # Example call for the current session
    log_metabolism(5000, 2000) 
