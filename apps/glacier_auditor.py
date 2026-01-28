import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import numpy as np
import json

def get_ice_stats(green_url, swir_url, bbox):
    try:
        with rasterio.open(green_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox)
            window = from_bounds(left, bottom, right, top, src.transform)
            green = src.read(1, window=window).astype('float32')
        with rasterio.open(swir_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox)
            window = from_bounds(left, bottom, right, top, src.transform)
            swir = src.read(1, window=window, out_shape=green.shape).astype('float32')
        
        ndsi = (green - swir) / (green + swir + 1e-10)
        ice_fraction = float(np.sum(ndsi > 0.4) / ndsi.size)
        return {"mean_ndsi": float(np.nanmean(ndsi)), "ice_fraction": ice_fraction}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    target_bbox = [-147.12, 61.08, -147.08, 61.12]
    
    # 2017 Baseline (6VVN)
    g17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/6/V/VN/2017/10/S2A_6VVN_20171019_0_L2A/B03.tif"
    s17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/6/V/VN/2017/10/S2A_6VVN_20171019_0_L2A/B11.tif"
    
    # Correct 2025 Current (6VVN)
    g25 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/6/V/VN/2025/10/S2C_6VVN_20251007_0_L2A/B03.tif"
    s25 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/6/V/VN/2025/10/S2C_6VVN_20251007_0_L2A/B11.tif"
    
    report = {
        "2017": get_ice_stats(g17, s17, target_bbox),
        "2025": get_ice_stats(g25, s25, target_bbox)
    }
    
    f17 = report["2017"]["ice_fraction"]
    f25 = report["2025"]["ice_fraction"]
    report["ice_loss_pct"] = float(((f17 - f25) / f17) * 100) if f17 > 0 else 0
    print(json.dumps(report, indent=2))
