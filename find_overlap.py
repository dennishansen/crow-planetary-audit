import rasterio
import numpy as np
import json

def get_valid_bounds(url):
    with rasterio.open(url) as src:
        # Read downsampled mask (1/100th scale)
        data = src.read(1, out_shape=(100, 100))
        mask = data > 0
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        
        # Map back to full resolution
        return {
            "y_range": (int(rmin * src.height / 100), int(rmax * src.height / 100)),
            "x_range": (int(cmin * src.width / 100), int(cmax * src.width / 100))
        }

url_2017 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B04.tif"
url_2026 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif"

try:
    bounds_2017 = get_valid_bounds(url_2017)
    bounds_2026 = get_valid_bounds(url_2026)
    
    # Find overlap of valid ranges
    y_overlap = (max(bounds_2017["y_range"][0], bounds_2026["y_range"][0]), 
                 min(bounds_2017["y_range"][1], bounds_2026["y_range"][1]))
    x_overlap = (max(bounds_2017["x_range"][0], bounds_2026["x_range"][0]), 
                 min(bounds_2017["x_range"][1], bounds_2026["x_range"][1]))
    
    print(json.dumps({"y_overlap": y_overlap, "x_overlap": x_overlap}, indent=2))
except Exception as e:
    print(f"Error: {e}")
