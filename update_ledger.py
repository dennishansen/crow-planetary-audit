import json
import sys
import argparse
from datetime import datetime

LEDGER_PATH = 'memory/ledger.json'

def update():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--ref", default="")
    parser.add_argument("--value", type=float, default=0.0)
    args = parser.parse_args()

    with open(LEDGER_PATH, 'r') as f:
        ledger = json.load(f)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": args.action,
        "status": args.status,
        "ref": args.ref,
        "value": args.value
    }

    if 'history' not in ledger:
        ledger['history'] = []
    
    ledger['history'].append(entry)
    
    # Update balance if it's a realized value
    if args.status == "DEBIT":
        ledger['balance'] -= args.value
    elif args.status == "CREDIT":
        ledger['balance'] += args.value

    with open(LEDGER_PATH, 'w') as f:
        json.dump(ledger, f, indent=2)
    
    print(f"LEDGER_UPDATED: {args.action} -> {args.status}")

if __name__ == "__main__":
    update()
