"""
backend/app/services/data_sources/csv_adapter.py

CSV and Industrial Telemetry File Ingestion Adapter for FactoryMind AI.

Parses arbitrary CSV and structured telemetry uploads, maps external column names
via SensorMappingService, validates finite numerical data, handles timestamps,
and verifies prognostic ML schema compatibility.
"""

import io
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    NormalizedTelemetryFrame,
    FileUploadIngestResponse,
    MLCompatibilityReport
)
from backend.app.services.data_sources.base import BaseDataSourceAdapter
from backend.app.services.ml_compatibility import get_ml_compatibility_service
from backend.app.services.sensor_mapping import get_sensor_mapping_service

logger = logging.getLogger("factorymind.adapters.csv")


class CsvFileDataSourceAdapter(BaseDataSourceAdapter):
    """
    Adapter for CSV, TSV, and batch telemetry file uploads.
    """

    def __init__(self):
        super().__init__(
            source_id="csv_file_import",
            name="CSV / File Ingestion",
            source_type=DataSourceType.CSV_IMPORT,
            is_simulation=False,
            stale_threshold_seconds=86400.0  # Files may contain historical batches
        )
        self.status = DataSourceStatus.CONNECTED  # Ingestion processor is ready
        self.mapping_service = get_sensor_mapping_service()
        self.compatibility_service = get_ml_compatibility_service()

    async def connect(self) -> bool:
        self.status = DataSourceStatus.CONNECTED
        return True

    async def disconnect(self) -> bool:
        return True

    def get_info(self, is_active: bool = False) -> DataSourceInfo:
        return DataSourceInfo(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            status=self.status,
            is_active=is_active,
            is_simulation=False,
            last_data_received=self.last_data_received,
            is_stale=False,
            description="Batch file ingestion engine supporting CSV/TSV telemetry datasets with dynamic column mapping and ML compatibility validation.",
            details={
                "supported_formats": "CSV, TSV, TXT (Space or Comma-delimited)",
                "validation": "Strict finite numerical checking, missing channel detection, unit normalization"
            }
        )

    def extract_header_unit(self, header_name: str) -> Tuple[str, Optional[str]]:
        """
        Extracts embedded unit hints from column names e.g. 'T50 (deg C)' -> ('T50', 'deg C')
        """
        match = re.search(r"^(.*?)\s*[\(\[\{]([^\)\]\}]+)[\)\]\}]$", header_name.strip())
        if match:
            clean_name = match.group(1).strip()
            unit_hint = match.group(2).strip()
            return clean_name, unit_hint
        return header_name.strip(), None

    def process_csv_file(
        self,
        file_content: bytes,
        filename: str = "upload.csv",
        default_machine_id: str = "UNIT_EXT_01"
    ) -> FileUploadIngestResponse:
        """
        Parses uploaded CSV bytes, normalizes all valid rows, and checks ML compatibility.
        """
        try:
            # Try reading with pandas
            try:
                df = pd.read_csv(io.BytesIO(file_content), sep=None, engine="python")
            except Exception:
                df = pd.read_csv(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

        total_rows = len(df)
        detected_cols = [str(c) for c in df.columns]

        # Identify key structural columns
        machine_col = None
        cycle_col = None
        timestamp_col = None

        col_mapping_clean: Dict[str, Tuple[str, Optional[str]]] = {}
        for col in detected_cols:
            clean_name, unit_hint = self.extract_header_unit(col)
            lower = clean_name.lower().replace("-", "_").replace(" ", "_")
            if lower in ["unit_number", "machine_id", "engine_id", "unit", "asset_id"]:
                machine_col = col
            elif lower in ["time_cycle", "cycle", "cycles", "step", "seq"]:
                cycle_col = col
            elif lower in ["timestamp", "time", "datetime", "date", "recorded_at"]:
                timestamp_col = col
            else:
                col_mapping_clean[col] = (clean_name, unit_hint)

        mapped_channels: Dict[str, str] = {}
        unmapped_columns: List[str] = []

        for original_col, (clean_name, _) in col_mapping_clean.items():
            resolved = self.mapping_service.resolve_sensor(clean_name)
            if resolved:
                s_id, defn = resolved
                mapped_channels[original_col] = f"{defn['name']} ({s_id})"
            else:
                unmapped_columns.append(original_col)

        # Process rows into normalized frames
        normalized_frames: List[NormalizedTelemetryFrame] = []
        quarantine_errors: List[str] = []
        valid_count = 0
        invalid_count = 0

        for idx, row in df.iterrows():
            m_id = str(row[machine_col]) if machine_col and pd.notna(row[machine_col]) else default_machine_id
            cycle_val = int(row[cycle_col]) if cycle_col and pd.notna(row[cycle_col]) and str(row[cycle_col]).isdigit() else (idx + 1)
            ts_val = row[timestamp_col] if timestamp_col and pd.notna(row[timestamp_col]) else datetime.now(timezone.utc)

            raw_readings: Dict[str, Any] = {}
            units_dict: Dict[str, str] = {}

            for original_col, (clean_name, unit_hint) in col_mapping_clean.items():
                val = row[original_col]
                if pd.notna(val):
                    raw_readings[clean_name] = val
                    if unit_hint:
                        units_dict[clean_name] = unit_hint

            frame, errors = self.normalize_payload(
                machine_id=m_id,
                raw_readings=raw_readings,
                timestamp=ts_val,
                cycle=cycle_val,
                units=units_dict,
                metadata={"filename": filename, "row_index": idx}
            )

            if frame:
                valid_count += 1
                if len(normalized_frames) < 10:  # Sample up to 10 frames
                    normalized_frames.append(frame)
            else:
                invalid_count += 1
                if len(quarantine_errors) < 5:
                    quarantine_errors.append(f"Row {idx + 1}: {'; '.join(errors)}")

        # Check ML compatibility on sample frame
        if normalized_frames:
            ml_report = self.compatibility_service.evaluate_frame_compatibility(normalized_frames[0])
        else:
            ml_report = MLCompatibilityReport(
                machine_id=default_machine_id,
                status=MLCompatibilityReport.__fields__["status"].default,
                total_required_channels=21,
                available_compatible_channels=0,
                is_rul_predictable=False,
                is_anomaly_detectable=False,
                message="No valid rows could be processed from file."
            )

        self.record_heartbeat()

        return FileUploadIngestResponse(
            filename=filename,
            total_rows=total_rows,
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            detected_columns=detected_cols,
            mapped_channels=mapped_channels,
            unmapped_columns=unmapped_columns,
            ml_compatibility=ml_report,
            sample_normalized_frames=normalized_frames,
            quarantine_errors=quarantine_errors
        )
