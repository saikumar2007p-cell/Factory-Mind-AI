"""
scripts/download_datasets.py

Automated dataset acquisition for FactoryMind AI.
Downloads genuine public industrial datasets from official sources.

Datasets:
  1. NASA C-MAPSS FD001 — Already present, validate only
  2. PHM 2009 Gearbox — Download from official/mirror sources
  3. PHMAP 2023 Valve — Download from official/mirror sources

Zero Fabrication: Only downloads real data. Never generates synthetic replacements.
"""

import os
import sys
import json
import zipfile
import io
import logging
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dataset_downloader")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"

# ============================================================================
# NASA C-MAPSS FD001
# ============================================================================

CMAPSS_DIR = DATA_RAW
CMAPSS_FILES = ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"]
CMAPSS_URLS = [
    # NASA official data.nasa.gov dataset (redirects to S3)
    "https://data.nasa.gov/download/xaut-bemq/application%2Fx-zip-compressed",
    # Ti.arc.nasa.gov mirror
    "https://ti.arc.nasa.gov/c/6/",
]


def download_cmapss():
    """Validate or download NASA C-MAPSS FD001 dataset."""
    logger.info("=== NASA C-MAPSS FD001 ===")

    # Check if already present
    missing = [f for f in CMAPSS_FILES if not (CMAPSS_DIR / f).exists()]
    if not missing:
        sizes = {f: (CMAPSS_DIR / f).stat().st_size for f in CMAPSS_FILES}
        logger.info(f"C-MAPSS FD001 already present. Files: {sizes}")
        return True

    logger.info(f"Missing C-MAPSS files: {missing}")
    logger.info("C-MAPSS data should be in data/raw/. Check existing files.")

    # The data is already in the repo from initial setup
    return not missing


# ============================================================================
# PHM 2009 Gearbox — Attempt automated download
# ============================================================================

PHM2009_DIR = DATA_RAW / "phm2009_gearbox"
PHM2009_URLS = [
    # Kaggle dataset mirror (public, no auth required for some mirrors)
    "https://github.com/mathworks/PHM-Gearbox-Dataset/archive/refs/heads/main.zip",
    # Alternative: MATLAB examples dataset
]

# Known structure of PHM 2009 labeled gearbox data:
# CSV files with columns: [input_voltage, output_voltage, tachometer]
# Operating conditions: 30Hz, 35Hz, 40Hz, 45Hz, 50Hz × high/low load


def create_phm2009_sample_from_description():
    """
    The PHM 2009 gearbox dataset requires manual download from:
    https://www.phmsociety.org/competition/phm/09

    Since automated download requires PHM Society registration,
    we create a dataset status report instead of fabricating data.
    """
    PHM2009_DIR.mkdir(parents=True, exist_ok=True)

    status = {
        "datasetId": "PHM_2009_GEARBOX",
        "status": "REQUIRES_MANUAL_DOWNLOAD",
        "reason": "PHM Society requires user registration for dataset download",
        "officialSource": "https://www.phmsociety.org/competition/phm/09",
        "alternativeSource": "https://www.kaggle.com/datasets/brjapon/gearbox-fault-diagnosis",
        "instructions": [
            "1. Visit https://www.phmsociety.org/competition/phm/09",
            "2. Download the labeled dataset (Released November 2009)",
            "3. Extract CSV files to: data/raw/phm2009_gearbox/",
            "OR",
            "1. Visit https://www.kaggle.com/datasets/brjapon/gearbox-fault-diagnosis",
            "2. Download and extract to: data/raw/phm2009_gearbox/"
        ],
        "expectedFormat": {
            "columns": ["input_voltage", "output_voltage", "tachometer"],
            "fileType": "CSV",
            "operatingConditions": ["30Hz", "35Hz", "40Hz", "45Hz", "50Hz"],
            "loadConditions": ["high", "low"],
            "faultTypes": ["tooth_damage", "shaft_imbalance", "bearing_defect", "normal"]
        }
    }

    status_path = PHM2009_DIR / "download_status.json"
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)
    logger.info(f"PHM 2009 status written to {status_path}")
    return False


def download_phm2009():
    """Attempt to download PHM 2009 Gearbox dataset."""
    logger.info("=== PHM 2009 Gearbox ===")
    PHM2009_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already present
    csv_files = list(PHM2009_DIR.glob("*.csv"))
    if csv_files:
        logger.info(f"PHM 2009 data already present: {len(csv_files)} CSV files")
        return True

    # Try automated download from GitHub mirrors
    for url in PHM2009_URLS:
        try:
            logger.info(f"Trying: {url}")
            req = Request(url, headers={"User-Agent": "FactoryMindAI/1.0"})
            response = urlopen(req, timeout=30)
            if response.status == 200:
                data = response.read()
                if url.endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        for member in zf.namelist():
                            if member.endswith(".csv"):
                                target = PHM2009_DIR / Path(member).name
                                with open(target, "wb") as f:
                                    f.write(zf.read(member))
                                logger.info(f"Extracted: {target.name}")

                csv_files = list(PHM2009_DIR.glob("*.csv"))
                if csv_files:
                    logger.info(f"PHM 2009 downloaded: {len(csv_files)} CSV files")
                    return True
        except (URLError, HTTPError, Exception) as e:
            logger.warning(f"Download failed from {url}: {e}")
            continue

    # If automated download failed, create status report
    logger.warning("Automated download unavailable — PHM Society requires registration")
    return create_phm2009_sample_from_description()


# ============================================================================
# PHMAP 2023 Valve/Pressure System
# ============================================================================

PHMAP2023_DIR = DATA_RAW / "phmap2023_valve"
PHMAP2023_URLS = [
    # GitHub repositories that host PHMAP 2023 data
    "https://github.com/PHM-Society/phmap-2023-challenge-data/archive/refs/heads/main.zip",
]


def create_phmap2023_status():
    """
    PHMAP 2023 valve dataset requires manual download from the conference site.
    """
    PHMAP2023_DIR.mkdir(parents=True, exist_ok=True)

    status = {
        "datasetId": "PHMAP_2023_VALVE",
        "status": "REQUIRES_MANUAL_DOWNLOAD",
        "reason": "PHMAP 2023 conference site requires registration for dataset access",
        "officialSource": "https://phmap.jp/2023/data-challenge/",
        "alternativeSource": "https://www.phmsociety.org/references/datasets",
        "instructions": [
            "1. Visit https://phmap.jp/2023/data-challenge/",
            "2. Register and download the competition dataset",
            "3. Extract data files to: data/raw/phmap2023_valve/"
        ],
        "expectedFormat": {
            "description": "Time-series pressure data at 1kHz from spacecraft propulsion system",
            "columns": ["pressure_upstream", "pressure_downstream", "valve_command"],
            "faultTypes": ["normal", "bubble_anomaly", "valve_fault", "leak"],
            "sampleRate": "1 kHz"
        }
    }

    status_path = PHMAP2023_DIR / "download_status.json"
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)
    logger.info(f"PHMAP 2023 status written to {status_path}")
    return False


def download_phmap2023():
    """Attempt to download PHMAP 2023 Valve dataset."""
    logger.info("=== PHMAP 2023 Valve/Pressure ===")
    PHMAP2023_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already present
    data_files = list(PHMAP2023_DIR.glob("*.csv")) + list(PHMAP2023_DIR.glob("*.npy"))
    if data_files:
        logger.info(f"PHMAP 2023 data already present: {len(data_files)} files")
        return True

    # Try automated download
    for url in PHMAP2023_URLS:
        try:
            logger.info(f"Trying: {url}")
            req = Request(url, headers={"User-Agent": "FactoryMindAI/1.0"})
            response = urlopen(req, timeout=30)
            if response.status == 200:
                data = response.read()
                if url.endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        for member in zf.namelist():
                            if member.endswith((".csv", ".npy", ".json")):
                                target = PHMAP2023_DIR / Path(member).name
                                with open(target, "wb") as f:
                                    f.write(zf.read(member))
                                logger.info(f"Extracted: {target.name}")

                data_files = list(PHMAP2023_DIR.glob("*.csv")) + list(PHMAP2023_DIR.glob("*.npy"))
                if data_files:
                    logger.info(f"PHMAP 2023 downloaded: {len(data_files)} files")
                    return True
        except (URLError, HTTPError, Exception) as e:
            logger.warning(f"Download failed from {url}: {e}")
            continue

    logger.warning("Automated download unavailable — PHMAP conference requires registration")
    return create_phmap2023_status()


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("FactoryMind AI — Automated Dataset Acquisition")
    logger.info("=" * 60)

    results = {}

    # 1. NASA C-MAPSS
    results["NASA_CMAPSS_FD001"] = download_cmapss()

    # 2. PHM 2009 Gearbox
    results["PHM_2009_GEARBOX"] = download_phm2009()

    # 3. PHMAP 2023 Valve
    results["PHMAP_2023_VALVE"] = download_phmap2023()

    # Summary
    logger.info("=" * 60)
    logger.info("DATASET ACQUISITION SUMMARY")
    logger.info("=" * 60)
    for ds_id, success in results.items():
        status = "✓ READY" if success else "✗ REQUIRES MANUAL DOWNLOAD"
        logger.info(f"  {ds_id}: {status}")

    return results


if __name__ == "__main__":
    main()
