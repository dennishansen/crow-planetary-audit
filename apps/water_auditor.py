import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np
import json

def calculate_ndwi(nir_url, swir_url, label):
    # We want a 1024x1024 window at 10m resolution (NIR resolution)
    target_window = Window(5000, 5000, 1024, 1024)
    
    try:
        # Read NIR (10m)
        with rasterio.open(nir_url) as src:
            nir = src.read(1, window=target_window).astype('float32')
            
        # Read SWIR (20m) and resample to match 1024x1024
        # Since SWIR is 20m, we read half the pixels from the same geographic area
        # and resample it back to 1024x1024
        swir_window = Window(2500, 2500, 512, 512) 
        with rasterio.open(swir_url) as src:
            swir = src.read(
                1, 
                window=swir_window, 
                out_shape=(1, 1024, 1024),
                resampling=Resampling.bilinear
            ).astype('float32')
        
        # NDWI = (NIR - SWIR) / (NIR + SWIR)
        ndwi = (nir - swir) / (nir + swir + 1e-10) # Add small epsilon to avoid div by zero
        mean_ndwi = np.nanmean(ndwi)
        
        return mean_ndwi
    except Exception as e:
        print(f"Error in {label}: {e}")
        return None

if __name__ == "__main__":
    nir_2020 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RP/2020/11/S2B_20LRP_20201128_0_L2A/B08.tif"
    swir_2020 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RP/2020/11/S2B_20LRP_20201128_0_L2A/B11.tif"
    
    nir_2025 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RR/2025/11/S2C_20LRR_20251117_0_L2A/B08.tif"
    swir_2025 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RR/2025/11/S2C_20LRR_20251117_0_L2A/B11.tif"
    
    val_2020 = calculate_ndwi(nir_2020, swir_2020, "2020 Baseline")
    val_2025 = calculate_ndwi(nir_2025, swir_2025, "2025 Current")
    
    if val_2020 is not None and val_2025 is not None:
        delta = val_2025 - val_2020
        delta_pct = (delta / (val_2020 + 1e-10)) * 100
        
        report = {
            "ndwi_2020": float(val_2020),
            "ndwi_2025": float(val_2025),
            "ndwi_delta_pct": float(delta_pct)
        }
        print(json.dumps(report, indent=2))
        with open('memory/water_stress_report.json', 'w') as f:
            json.dump(report, f, indent=2)
