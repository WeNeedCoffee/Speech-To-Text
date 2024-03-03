from pathlib import Path

filename = "enabled.lock"

file_path = Path(filename)
if file_path.exists():
    file_path.unlink()
    print(f"Deleted file: {filename}")
else:
    file_path.touch()
    print(f"Created file: {filename}")
