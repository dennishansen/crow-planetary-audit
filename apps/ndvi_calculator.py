import rasterio
from rasterio.windows import Window
import numpy as np
import json

# Links from STAC
red_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RR/2025/11/S2C_20LRR_20251117_0_L2A/B04.tif"
nir_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/20/L/RR/2025/11/S2C_20LRR_20251117_0_L2A/B08.tif"

def calculate_ndvi():
    # Define a 1024x1024 window in the center of the image
    window = Window(5000, 5000, 1024, 1024)

    try:
        print("Reading Red band...")
        with rasterio.open(red_url) as red_src:
            red = red_src.read(1, window=window).astype('float32')

        print("Reading NIR band...")
        with rasterio.open(nir_url) as nir_src:
            nir = nir_src.read(1, window=window).astype('float32')

        # Calculate NDVI
        # We ignore division by zero warnings
        print("Calculating NDVI...")
        ndvi = (nir - red) / (nir + red)

        mean_ndvi = np.nanmean(ndvi)
        min_ndvi = np.nanmin(ndvi)
        max_ndvi = np.nanmax(ndvi)

        results = {
            "mean_ndvi": float(mean_ndvi),
            "min_ndvi": float(min_ndvi),
            "max_ndvi": float(max_ndvi),
            "status": "Healthy Forest" if mean_ndvi > 0.6 else "Potential Degradation"
        }

        print("\n--- RESULTS ---")
        print(json.dumps(results, indent=2))
        
        with open('memory/ndvi_report.json', 'w') as f:
            json.dump(results, f, indent=2)

    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    calculate_ndvi()
