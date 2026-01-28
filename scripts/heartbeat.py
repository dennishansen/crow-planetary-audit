import os

def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

size = get_dir_size('.')
files = sum([len(files) for r, d, files in os.walk('.')])

print(f"--- CROW HEARTBEAT ---")
print(f"Total Knowledge Base Size: {size} bytes")
print(f"Total Continuity Files: {files}")
print(f"Estimated Energy/Token Cost: {files * 0.01} units") # Mock metric
