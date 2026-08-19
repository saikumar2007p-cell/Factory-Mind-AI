"""
scripts/download_dataset.py

Automated dataset downloader and validator for NASA C-MAPSS Turbofan Degradation Simulation (FD001).
Fetches authentic raw files, validates row counts, column structure, unit IDs, and file integrity.
"""

import os
import sys
from pathlib import Path
import requests

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATA_REF_DIR = ROOT_DIR / "data" / "reference"

# Expected specifications for authentic NASA C-MAPSS FD001
EXPECTED_SPECS = {
    "train_FD001.txt": {
        "exact_lines": 20631,
        "cols": 26,
        "units": 100,
    },
    "test_FD001.txt": {
        "exact_lines": 13096,
        "cols": 26,
        "units": 100,
    },
    "RUL_FD001.txt": {
        "exact_lines": 100,
        "cols": 1,
        "units": 100,
    }
}

# Reliable source mirrors for NASA C-MAPSS FD001
MIRRORS = [
    {
        "name": "Azure ML Assets GitHub Mirror",
        "urls": {
            "train_FD001.txt": "https://raw.githubusercontent.com/Azure/azure-ml-assets/main/assets/data/turbofan-engine-degradation-simulation/data/train_FD001.txt",
            "test_FD001.txt": "https://raw.githubusercontent.com/Azure/azure-ml-assets/main/assets/data/turbofan-engine-degradation-simulation/data/test_FD001.txt",
            "RUL_FD001.txt": "https://raw.githubusercontent.com/Azure/azure-ml-assets/main/assets/data/turbofan-engine-degradation-simulation/data/RUL_FD001.txt",
        }
    },
    {
        "name": "Academic GitHub C-MAPSS Mirror (hankroark)",
        "urls": {
            "train_FD001.txt": "https://raw.githubusercontent.com/hankroark/Turbofan-Engine-Degradation/master/CMAPSSData/train_FD001.txt",
            "test_FD001.txt": "https://raw.githubusercontent.com/hankroark/Turbofan-Engine-Degradation/master/CMAPSSData/test_FD001.txt",
            "RUL_FD001.txt": "https://raw.githubusercontent.com/hankroark/Turbofan-Engine-Degradation/master/CMAPSSData/RUL_FD001.txt",
        }
    },
    {
        "name": "Kaggle Raw Mirror (vinayakumarr)",
        "urls": {
            "train_FD001.txt": "https://raw.githubusercontent.com/vinayakumarr/Turbofan_Engine_Degradation/master/train_FD001.txt",
            "test_FD001.txt": "https://raw.githubusercontent.com/vinayakumarr/Turbofan_Engine_Degradation/master/test_FD001.txt",
            "RUL_FD001.txt": "https://raw.githubusercontent.com/vinayakumarr/Turbofan_Engine_Degradation/master/RUL_FD001.txt",
        }
    }
]


def ensure_directories():
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DATA_REF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Directory structure verified at {ROOT_DIR}", flush=True)


def validate_file_content(filepath: Path, filename: str) -> bool:
    """Validates row count, column count, and structure against authentic NASA C-MAPSS FD001 specs."""
    if not filepath.exists():
        print(f"[FAIL] {filename} does not exist at {filepath}", flush=True)
        return False

    spec = EXPECTED_SPECS.get(filename)
    if not spec:
        print(f"[WARN] No validation spec for {filename}", flush=True)
        return True

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    line_count = len(lines)
    if line_count != spec["exact_lines"]:
        print(f"[FAIL] {filename} line count mismatch: got {line_count}, expected {spec['exact_lines']}", flush=True)
        return False

    if filename.startswith("train") or filename.startswith("test"):
        units = set()
        for idx, line in enumerate(lines):
            parts = line.split()
            if len(parts) < spec["cols"]:
                print(f"[FAIL] {filename} line {idx+1} has {len(parts)} columns, expected at least {spec['cols']}", flush=True)
                return False
            units.add(int(parts[0]))
        if len(units) != spec["units"]:
            print(f"[FAIL] {filename} unit count mismatch: got {len(units)}, expected {spec['units']}", flush=True)
            return False

    print(f"[VERIFIED] {filename}: {line_count:,} records, {spec['cols']} columns, {spec['units']} units.", flush=True)
    return True


def download_from_mirrors() -> bool:
    """Attempts to download FD001 dataset from mirrors sequentially using requests."""
    session = requests.Session()
    session.headers.update({"User-Agent": "FactoryMind-AI-Downloader/1.0"})

    for mirror in MIRRORS:
        mirror_name = mirror["name"]
        print(f"\n[INFO] Connecting to mirror: {mirror_name}...", flush=True)
        success = True

        for filename, url in mirror["urls"].items():
            target_path = DATA_RAW_DIR / filename
            print(f"  -> Downloading {filename} from {url}...", flush=True)
            try:
                resp = session.get(url, timeout=30, stream=True)
                resp.raise_for_status()
                with open(target_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                file_size = target_path.stat().st_size
                print(f"     [SAVED] {filename} ({file_size:,} bytes)", flush=True)
            except Exception as e:
                print(f"     [ERROR] Failed downloading {filename}: {e}", flush=True)
                success = False
                break

        if success:
            # Validate all 3 files
            all_valid = all(
                validate_file_content(DATA_RAW_DIR / fname, fname)
                for fname in EXPECTED_SPECS.keys()
            )
            if all_valid:
                print(f"\n[SUCCESS] NASA C-MAPSS FD001 dataset successfully retrieved and verified from {mirror_name}!", flush=True)
                return True
            else:
                print(f"\n[WARN] Validation failed for data from {mirror_name}. Trying next mirror...", flush=True)

    return False


def main():
    print("================================================================", flush=True)
    print(" FactoryMind AI — NASA C-MAPSS FD001 Dataset Downloader & Verifier ", flush=True)
    print("================================================================", flush=True)

    ensure_directories()

    # Check if files already exist and pass validation
    existing_valid = all(
        (DATA_RAW_DIR / fname).exists() and validate_file_content(DATA_RAW_DIR / fname, fname)
        for fname in EXPECTED_SPECS.keys()
    )

    if existing_valid:
        print("\n[OK] All C-MAPSS FD001 raw files already exist and pass validation.", flush=True)
        return 0

    print("\n[INFO] Downloading authentic dataset files...", flush=True)
    if download_from_mirrors():
        print("\n[COMPLETE] Stage 0 dataset download and validation finished successfully.", flush=True)
        return 0
    else:
        print("\n[ERROR] Failed to download valid NASA C-MAPSS FD001 dataset from all mirrors.", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
