import rasterio
import numpy as np

def probe(url):
    with rasterio.open(url) as src:
        # Read a very small downsampled version to find data
        data = src.read(1, out_shape=(100, 100))
        valid_indices = np.where(data > 0)
        if len(valid_indices[0]) > 0:
            # Map back to original scale
            y, x = valid_indices[0][0], valid_indices[1][0]
            real_y, real_x = int(y * (src.height / 100)), int(x * (src.width / 100))
            print(f"VALID_DATA_FOUND|{real_x}|{real_y}|VAL:{data[y,x]}")
        else:
            print("NO_DATA_FOUND")

url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/45/Q/XD/2026/1/S2C_45QXD_20260125_0_L2A/B04.tif"
probe(url)
