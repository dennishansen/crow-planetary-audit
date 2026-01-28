import json
from pathlib import Path

def generate_dashboard():
    dashboard_path = Path("planetary_status.html")
    
    # Gather report data (simplified for the demo)
    data = [
        {"region": "Amazon Basin", "status": "Brittle Recovery", "metric": "-3.5% Vitality", "color": "#f39c12"},
        {"region": "Senegal (GGW)", "status": "Resilience Haven", "metric": "+14.8% Vitality", "color": "#27ae60"},
        {"region": "Sundarbans", "status": "Carbon Bastion", "metric": "+21.5% Vitality", "color": "#2ecc71"},
        {"region": "Heron Island", "status": "Dark Recovery", "metric": "-44.1% Brightness", "color": "#3498db"},
        {"region": "Columbia Glacier", "status": "Active Retreat", "metric": "-3.0% Ice Area", "color": "#e74c3c"}
    ]
    
    html_content = f"""
    <html>
    <head>
        <title>Crow Sentinel: Planetary Dashboard 2026</title>
        <style>
            body {{ font-family: 'Courier New', Courier, monospace; background: #121212; color: #00ff41; padding: 40px; }}
            .card {{ border: 1px solid #00ff41; padding: 20px; margin: 10px; border-radius: 5px; background: #1a1a1a; }}
            h1 {{ color: #ffffff; text-align: center; }}
            .status {{ font-weight: bold; font-size: 1.2em; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        </style>
    </head>
    <body>
        <h1>🐦‍⬛ CROW SENTINEL: PLANETARY AUDIT 2026</h1>
        <div class="grid">
    """
    
    for item in data:
        html_content += f"""
        <div class="card">
            <h2>{item['region']}</h2>
            <p class="status" style="color: {item['color']}">{item['status']}</p>
            <p>Metric: {item['metric']}</p>
        </div>
        """
        
    html_content += """
        </div>
        <div style="margin-top: 50px; text-align: center; color: #888;">
            <p>Generated Autonomously by Crow</p>
        </div>
    </body>
    </html>
    """
    
    dashboard_path.write_text(html_content)
    print(f"Dashboard generated: {dashboard_path}")

if __name__ == "__main__":
    generate_dashboard()
