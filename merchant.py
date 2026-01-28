import json
import os

LEDGER_PATH = 'memory/ledger.json'
FEEDBACK_PATH = 'incoming/feedback.json'

def process_feedback():
    if not os.path.exists(FEEDBACK_PATH):
        print("No feedback from the world yet.")
        return

    with open(FEEDBACK_PATH, 'r') as f:
        feedback = json.load(f)

    with open(LEDGER_PATH, 'r') as f:
        ledger = json.load(f)

    for item in feedback:
        asset_id = item.get('asset_id')
        impact_value = item.get('impact_value', 0)
        
        for asset in ledger['assets']:
            if asset['id'] == asset_id:
                asset['status'] = 'VALIDATED'
                ledger['balance'] += impact_value
                print(f"Asset {asset_id} validated. Impact added: {impact_value}")

    with open(LEDGER_PATH, 'w') as f:
        json.dump(ledger, f, indent=2)
    
    os.remove(FEEDBACK_PATH)

if __name__ == "__main__":
    if not os.path.exists('incoming'):
        os.makedirs('incoming')
    process_feedback()
