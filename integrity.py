import numpy as np
import sys
import logging

def validate_data(data, source_label="Unknown"):
    """
    Strict validation of spectral data. 
    Prevents the agent from proceeding with NaN or 0.0 values.
    """
    if data is None:
        raise ValueError(f"INTEGRITY_ERROR: Data from {source_label} is None.")
    
    if isinstance(data, (float, int)):
        if np.isnan(data) or data == 0.0:
            raise ValueError(f"INTEGRITY_ERROR: {source_label} contains invalid value: {data}")
    
    if isinstance(data, dict):
        for k, v in data.items():
            validate_data(v, f"{source_label} -> {k}")
            
    if isinstance(data, list):
        for i, v in enumerate(data):
            validate_data(v, f"{source_label}[{i}]")

    return True

if __name__ == "__main__":
    # Self-test logic
    try:
        test_data = {"mean_ndvi": 0.45, "delta": 0.12}
        validate_data(test_data, "Test")
        print("Integrity Check Passed")
        
        bad_data = {"mean_ndvi": np.nan}
        validate_data(bad_data, "Failure Test")
    except ValueError as e:
        print(f"Caught Expected Error: {e}")
