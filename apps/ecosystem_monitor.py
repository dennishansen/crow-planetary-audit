import rasterio
from rasterio.windows import Window
import numpy as np
import json
import sys

def analyze_coordinate(red_url, nir_url, label="Unknown Location"):
    window = Window(5000, 5000, 1024, 1024)
    try:
        with rasterio.open(red_url) as red_src:
            red = red_src.read(1, window=window).astype('float32')
        with rasterio.open(nir_url) as nir_src:
            nir = nir_src.read(1, window=window).astype('float32')
        
        ndvi = (nir - red) / (nir + red)
        mean_v = np.nanmean(ndvi)
        
        status = "Healthy" if mean_v > 0.6 else "Stressed/Degraded"
        if mean_v < 0.3: status = "Critical/Deforested"
        
        return {
            "label": label,
            "mean_ndvi": float(mean_v),
            "status": status
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # This can be expanded to take arguments
    print("Ecosystem Monitor Module initialized.")
