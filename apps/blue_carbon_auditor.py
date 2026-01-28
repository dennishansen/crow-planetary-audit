import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import numpy as np
import json

def get_blue_stats(red_url, nir_url, swir_url, bbox_wgs84):
    try:
        with rasterio.open(red_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox_wgs84)
            window = from_bounds(left, bottom, right, top, src.transform)
            red = src.read(1, window=window).astype('float32')
            
        with rasterio.open(nir_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox_wgs84)
            window = from_bounds(left, bottom, right, top, src.transform)
            nir = src.read(1, window=window).astype('float32')
            
        with rasterio.open(swir_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *bbox_wgs84)
            window = from_bounds(left, bottom, right, top, src.transform)
            swir = src.read(1, window=window, out_shape=red.shape).astype('float32')
            
        ndvi = (nir - red) / (nir + red + 1e-10)
        ndwi = (nir - swir) / (nir + swir + 1e-10)
        
        return float(np.nanmean(ndvi)), float(np.nanmean(ndwi))
    except Exception as e:
        print(f"Error: {e}")
        return None, None

if __name__ == "__main__":
    # Corrected Sundarbans Coordinate (Inside tile bounds)
    # West, South, East, North
    target_bbox = (88.95, 21.60, 89.00, 21.65)
    
    # 2017 Baseline
    r17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B04.tif"
    n17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B08.tif"
    s17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B11.tif"
    
    # 2026 Current
    r26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif"
    n26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B08.tif"
    s26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B11.tif"
    
    ndvi17, ndwi17 = get_blue_stats(r17, n17, s17, target_bbox)
    ndvi26, ndwi26 = get_blue_stats(r26, n26, s26, target_bbox)
    
    report = {
        "location": "Sundarbans Heart (21.62N, 88.97E)",
        "2017": {"ndvi": ndvi17, "ndwi": ndwi17},
        "2026": {"ndvi": ndvi26, "ndwi": ndwi26},
        "ndvi_delta_pct": float((ndvi26 - ndvi17)/ndvi17 * 100) if ndvi17 else 0,
        "ndwi_delta_pct": float((ndwi26 - ndwi17)/ndwi17 * 100) if ndvi17 else 0
    }
    print(json.dumps(report, indent=2))
