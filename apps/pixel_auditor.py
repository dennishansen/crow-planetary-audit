import rasterio
from rasterio.windows import Window
import numpy as np
import json

def audit_transitions(scl_2020_url, scl_2025_url):
    window = Window(5000, 5000, 1024, 1024)
    try:
        print("Reading SCL 2020...")
        with rasterio.open(scl_2020_url) as src:
            scl_2020 = src.read(1, window=window)
            
        print("Reading SCL 2025...")
        with rasterio.open(scl_2025_url) as src:
            scl_2025 = src.read(1, window=window)

        # Sentinel-2 SCL Classes: 4=Vegetation, 5=Not-vegetated(Soil), 6=Water
        veg_2020 = np.sum(scl_2020 == 4)
        veg_2025 = np.sum(scl_2025 == 4)
        
        soil_2020 = np.sum(scl_2020 == 5)
        soil_2025 = np.sum(scl_2025 == 5)

        total_pixels = 1024 * 1024
        
        report = {
            "veg_change_pct": float(((veg_2025 - veg_2020) / veg_2020) * 100),
            "soil_expansion_pct": float(((soil_2025 - soil_2020) / (soil_2020 + 1)) * 100),
            "raw_veg_2020": int(veg_2020),
            "raw_veg_2025": int(veg_2025)
        }
        return report
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # URLs for SCL bands
    scl_2020 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RP/2020/11/S2B_20LRP_20201128_0_L2A/SCL.tif"
    scl_2025 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RR/2025/11/S2C_20LRR_20251117_0_L2A/SCL.tif"
    
    report = audit_transitions(scl_2020, scl_2025)
    print(json.dumps(report, indent=2))
