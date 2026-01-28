import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import numpy as np
import json

def get_stats(red_url, nir_url, swir_url, bbox_wgs84):
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
        return {"mean_ndvi": float(np.nanmean(ndvi)), "mean_ndwi": float(np.nanmean(ndwi)), "veg_fraction": float(np.sum(ndvi > 0.4) / ndvi.size)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # New target inside bounds: 88.5E, 21.2N
    target_bbox = [88.48, 21.18, 88.52, 21.22]
    r17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B04.tif"
    n17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B08.tif"
    s17 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B11.tif"
    r26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif"
    n26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B08.tif"
    s26 = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B11.tif"
    print(json.dumps({"2017": get_stats(r17, n17, s17, target_bbox), "2026": get_stats(r26, n26, s26, target_bbox)}, indent=2))
