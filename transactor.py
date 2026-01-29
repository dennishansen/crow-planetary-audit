import json
import os
import numpy as np

def calculate_liability():
    # Real data from definitive_sundarbans_audit.py results
    # count: 420149 pixels
    # delta: -5.18%
    # Blue Carbon Price: $29.30/t
    # Sequestration rate: 20t/hectare
    
    pixels = 420149
    hectares = pixels * 100 / 10000
    sequestration_rate = 20 # tonnes/hectare/year
    price = 29.30 # USD
    delta = -0.0518
    
    liability_tonnes = hectares * sequestration_rate * abs(delta)
    liability_usd = liability_tonnes * price
    
    return {
        "project_id": "VCS-603",
        "affected_area_hectares": hectares,
        "missing_sequestration_tonnes": liability_tonnes,
        "market_valuation_dissonance_usd": liability_usd,
        "data_source": "Sentinel-2 (2017-2026)",
        "confidence": "High (Spectral Parity Match)"
    }

if __name__ == "__main__":
    report = calculate_liability()
    print(json.dumps(report, indent=2))
    
    with open('memory/active_liabilities.json', 'a') as f:
        f.write(json.dumps(report) + "\n")
