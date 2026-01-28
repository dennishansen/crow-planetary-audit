import rasterio
from rasterio.windows import Window
import numpy as np
import json

def audit():
    window = Window(5000, 5000, 1024, 1024)
    scl_2017_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/28/P/EC/2017/1/S2A_28PEC_20170125_0_L2A/SCL.tif"
    scl_2026_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/28/P/DC/2026/1/S2C_28PDC_20260121_0_L2A/SCL.tif"
    
    try:
        with rasterio.open(scl_2017_url) as src:
            scl_17 = src.read(1, window=window)
        with rasterio.open(scl_2026_url) as src:
            scl_26 = src.read(1, window=window)

        veg_17 = np.sum(scl_17 == 4)
        veg_26 = np.sum(scl_26 == 4)
        soil_17 = np.sum(scl_17 == 5)
        soil_26 = np.sum(scl_26 == 5)
        
        return {
            "veg_loss_pct": float(((veg_26 - veg_17) / (veg_17 + 1)) * 100),
            "soil_gain_pct": float(((soil_26 - soil_17) / (soil_17 + 1)) * 100),
            "raw_veg_2017": int(veg_17),
            "raw_veg_2026": int(veg_26)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    report = audit()
    print(json.dumps(report, indent=2))
