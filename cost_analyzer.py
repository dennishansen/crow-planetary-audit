import json
from collections import defaultdict
from pathlib import Path

def analyze_costs(ledger_path: Path):
    total_cost_usd = 0.0
    model_stats = defaultdict(lambda: {"total_tokens": 0, "total_cost_usd": 0.0, "calls": 0})
    
    if not ledger_path.exists():
        print(f"Ledger file not found at {ledger_path}")
        return

    with open(ledger_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                model = entry.get("model", "unknown")
                cost_usd = entry.get("cost_usd")
                total_tokens = entry.get("total_tokens", 0)

                if cost_usd is not None:
                    total_cost_usd += cost_usd
                    model_stats[model]["total_cost_usd"] += cost_usd
                
                model_stats[model]["total_tokens"] += total_tokens
                model_stats[model]["calls"] += 1

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from ledger: {e} - Line: {line.strip()}")
            except Exception as e:
                print(f"An unexpected error occurred: {e} - Line: {line.strip()}")

    print("\n=== Cost Analysis Report ===")
    print(f"Total Operational Cost (USD): ${total_cost_usd:.6f}")
    print("\n--- Costs per Model ---")
    for model, stats in model_stats.items():
        print(f"Model: {model}")
        print(f"  Total Calls: {stats['calls']}")
        print(f"  Total Tokens: {stats['total_tokens']:,}")
        print(f"  Total Cost (USD): ${stats['total_cost_usd']:.6f}")
        if stats['calls'] > 0:
            print(f"  Average Cost per Call: ${stats['total_cost_usd'] / stats['calls']:.6f}")
        print("-" * 20)

if __name__ == "__main__":
    current_dir = Path(__file__).parent
    ledger_file = current_dir / "logs" / "ledger.log"
    analyze_costs(ledger_file)
