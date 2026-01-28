import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
from rasterio.enums import Resampling
import numpy as np
import json

def get_reef_stats(coastal_url, blue_url, bbox):
    try:
        # Read Blue (10m resolution)
        with rasterio.open(blue_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox)
            window = from_bounds(left, bottom, right, top, src.transform)
            blue = src.read(1, window=window).astype('float32')
            
        # Read Coastal (60m res) - Resample to match Blue shape
        with rasterio.open(coastal_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox)
            window = from_bounds(left, bottom, right, top, src.transform)
            coastal = src.read(1, window=window, out_shape=blue.shape, resampling=Resampling.bilinear).astype('float32')
            
        # We focus on the brightest pixels in the window (the reef top)
        # Healthy coral is darker (absorbs light), bleached is brighter
        mean_blue = np.nanmean(blue)
        mean_coastal = np.nanmean(coastal)
        
        return {
            "mean_blue": float(mean_blue),
            "mean_coastal": float(mean_coastal),
            "brightness_sum": float(mean_blue + mean_coastal)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Heron Island lagoon coords
    target_bbox = [151.91, -23.45, 151.92, -23.44]
    
    # 2021 URLs
    c21 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/56/K/LV/2021/2/S2A_56KLV_20210223_0_L2A/B01.tif"
    b21 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/56/K/LV/2021/2/S2A_56KLV_20210223_0_L2A/B02.tif"
    
    # 2026 URLs
    c26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/56/K/LV/2026/1/S2C_56KLV_20260121_0_L2A/B01.tif"
    b26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/56/K/LV/2026/1/S2C_56KLV_20260121_0_L2A/B02.tif"
    
    report = {
        "2021_baseline": get_reef_stats(c21, b21, target_bbox),
        "2026_current": get_reef_stats(c26, b26, target_bbox)
    }
    
    # Calculate change
    b21_val = report['2021_baseline']['brightness_sum']
    b26_val = report['2026_current']['brightness_sum']
    report['brightness_delta_pct'] = float(((b26_val - b21_val) / b21_val) * 100)
    
    print(json.dumps(report, indent=2))
    with open('memory/coral_report.json', 'w') as f:
        json.dump(report, f, indent=2)
