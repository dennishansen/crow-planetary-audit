import rasterio
from rasterio.windows import Window
import numpy as np
import json

def get_ndvi(red_url, nir_url, window):
    with rasterio.open(red_url) as r_src, rasterio.open(nir_url) as n_src:
        red = r_src.read(1, window=window).astype('float32')
        nir = n_src.read(1, window=window).astype('float32')
        mask = (red > 0) & (nir > 0)
        ndvi = np.full(red.shape, np.nan)
        ndvi[mask] = (nir[mask] - red[mask]) / (nir[mask] + red[mask])
        return ndvi

audit_window = Window(9400, 0, 1024, 1024)

urls_2017 = {
    "red": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B04.tif",
    "nir": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2017/12/S2A_45QXD_20171228_0_L2A/B08.tif"
}
urls_2026 = {
    "red": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif",
    "nir": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B08.tif"
}

n17 = get_ndvi(urls_2017['red'], urls_2017['nir'], audit_window)
n26 = get_ndvi(urls_2026['red'], urls_2026['nir'], audit_window)

# Find pixels that are vegetation (NDVI > 0.4) in BOTH years
veg_mask = (n17 > 0.4) & (n26 > 0.4)

if np.any(veg_mask):
    results = {
        "count": int(np.sum(veg_mask)),
        "2017_veg_mean": float(np.mean(n17[veg_mask])),
        "2026_veg_mean": float(np.mean(n26[veg_mask])),
    }
    results["delta_pct"] = ((results["2026_veg_mean"] - results["2017_veg_mean"]) / results["2017_veg_mean"]) * 100
    print(json.dumps(results, indent=2))
else:
    print(json.dumps({"error": "No overlapping vegetation pixels found"}))
