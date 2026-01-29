import rasterio
from rasterio.windows import Window
import numpy as np

red_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif"
nir_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B08.tif"

with rasterio.open(red_url) as r_src, rasterio.open(nir_url) as n_src:
    for y in range(0, 8000, 2000):
        for x in range(7400, 10000, 1000):
            win = Window(x, y, 512, 512)
            red = r_src.read(1, window=win).astype('float32')
            nir = n_src.read(1, window=win).astype('float32')
            mask = (red > 0) & (nir > 0)
            if np.any(mask):
                ndvi = (nir[mask] - red[mask]) / (nir[mask] + red[mask])
                print(f"WINDOW|x:{x}|y:{y}|NDVI:{np.mean(ndvi):.3f}")
