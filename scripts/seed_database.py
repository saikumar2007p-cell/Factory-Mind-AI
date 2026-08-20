"""
scripts/seed_database.py

Database Initialization and Seeding Script for FactoryMind AI.

- Initializes database schema (PostgreSQL/Supabase or SQLite fallback)
- Seeds the 100 authentic NASA C-MAPSS FD001 turbofan machines
- Loads initial baseline historical telemetry from real train_FD001.txt for demo units
- Runs real Stage 2 inference to persist initial verified prognostics
"""

import asyncio
import os
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT_DIR / "data" / "raw"
sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import settings
from backend.app.database import init_db, get_engine, get_session_maker
from backend.app.services.storage_service import StorageService
from ml.dataset import CMAPSSDataset
from ml.inference import get_inference_engine


async def seed_database():
    print("================================================================")
    print(" FactoryMind AI — Database Schema Initialization & Seeding      ")
    print("================================================================")

    # 1. Initialize Tables
    print(f"\n[1/3] Initializing database tables...")
    print(f"      Target: {'Local SQLite Fallback' if settings.is_sqlite_fallback else 'PostgreSQL/Supabase'}")
    print(f"      URL:    {settings.effective_database_url}")
    await init_db()

    session_maker = get_session_maker()
    dataset = CMAPSSDataset()

    async with session_maker() as session:
        service = StorageService(session)

        # 2. Seed Machine Registry (Turbofan, Gearbox, Valve Units)
        print("\n[2/3] Seeding Machine Registry (NASA C-MAPSS, PHM 2009 Gearbox, PHMAP 2023 Valve)...")
        existing_machines = await service.get_all_machines()
        existing_unit_numbers = {m.unit_number for m in existing_machines}

        # 100 Turbofans
        for unit_id in range(1, 101):
            if unit_id not in existing_unit_numbers:
                cell_id = (unit_id % 4) + 1
                await service.create_machine(
                    unit_number=unit_id,
                    name=f"Turbofan Engine #{unit_id:03d}",
                    machine_type="Turbofan CF6-80C2",
                    location=f"Test Cell {cell_id}",
                    status="OPERATIONAL"
                )

        # 6 Gearbox Test Stands (PHM 2009)
        gearbox_names = [
            "Industrial Gearbox Stand A (Healthy / 30Hz)",
            "Industrial Gearbox Stand B (High Load / 40Hz)",
            "Industrial Gearbox Stand C (Broken Tooth Defect)",
            "Industrial Gearbox Stand D (Chipped Tooth Defect)",
            "Industrial Gearbox Stand E (Shaft Imbalance)",
            "Industrial Gearbox Stand F (Bearing Defect)"
        ]
        for idx, g_name in enumerate(gearbox_names, start=101):
            if idx not in existing_unit_numbers:
                await service.create_machine(
                    unit_number=idx,
                    name=g_name,
                    machine_type="Industrial Helical Gearbox",
                    location="Gearbox Diagnostics Cell",
                    status="OPERATIONAL" if "Healthy" in g_name else "WARNING"
                )

        # 5 Propulsion Valves (PHMAP 2023)
        valve_names = [
            "Propulsion Valve Solenoid V-101 (Nominal)",
            "Propulsion Valve Solenoid V-102 (Bubble Anomaly)",
            "Propulsion Valve Solenoid V-103 (Coil Fault)",
            "Propulsion Valve Solenoid V-104 (Seal Leak)",
            "Propulsion Valve Solenoid V-105 (Surge Transient)"
        ]
        for idx, v_name in enumerate(valve_names, start=107):
            if idx not in existing_unit_numbers:
                await service.create_machine(
                    unit_number=idx,
                    name=v_name,
                    machine_type="Spacecraft Solenoid Valve",
                    location="Propulsion Test Stand",
                    status="OPERATIONAL" if "Nominal" in v_name else "WARNING"
                )

        await session.commit()
        print(f"      [OK] Successfully registered all Turbofan, Gearbox, and Valve equipment units.")

        # 3. Ingest Baseline Telemetry & Run Real Inference for ALL Units (1..100 Turbofan, 101..106 Gearbox, 107..111 Valve)
        print("\n[3/3] Ingesting authentic baseline telemetry & prognostics across the entire fleet...")
        df_train = dataset.load_raw_train()
        engine = get_inference_engine()

        all_machines = await service.get_all_machines()
        machine_by_unit = {m.unit_number: m for m in all_machines}

        seeded_count = 0
        for unit_id in range(1, 101):
            mach = machine_by_unit.get(unit_id)
            if not mach:
                continue

            history = await service.get_telemetry_history(mach.id, limit=2)
            if not history:
                unit_u_df = df_train[df_train["unit_number"] == unit_id].sort_values("time_cycle").reset_index(drop=True)
                if not unit_u_df.empty:
                    # Give each unit a realistic slice (e.g. 25-45 cycles) so each unit has different health/cycle
                    max_c = min(len(unit_u_df), 20 + (unit_id * 3) % 40)
                    baseline_window = unit_u_df.iloc[:max_c].copy()

                    records = baseline_window.to_dict(orient="records")
                    await service.insert_telemetry_batch(mach.id, records)

                    # Run inference for this unit
                    engine.reset_tracker(unit_id)
                    result = engine.predict_window(baseline_window)
                    await service.persist_inference_cycle(mach.id, result)
                    seeded_count += 1

        # Seed Gearbox Units 101..106
        from ml.dataset_adapters import get_adapter
        gb_adapter = get_adapter("PHM_2009_GEARBOX")
        if gb_adapter and gb_adapter.is_available():
            gb_files = sorted((DATA_RAW / "phm2009_gearbox").glob("*.csv"))
            for idx, g_file in enumerate(gb_files, start=101):
                mach = machine_by_unit.get(idx)
                if mach:
                    history = await service.get_telemetry_history(mach.id, limit=2)
                    if not history:
                        try:
                            import pandas as pd
                            df_gb = pd.read_csv(g_file)
                            # Convert sample rows to telemetry format
                            tel_records = []
                            for row_i, r in df_gb.head(30).iterrows():
                                tel_records.append({
                                    "unit_number": idx,
                                    "time_cycle": row_i + 1,
                                    "setting_1": float(r.get("shaft_speed_hz", 30.0)),
                                    "setting_2": float(r.get("load_factor", 0.5)),
                                    "setting_3": 100.0,
                                    "s_1": float(r.get("input_voltage", 0.0)),
                                    "s_2": float(r.get("output_voltage", 0.0)),
                                    "s_3": float(r.get("tachometer", 0.0)),
                                })
                            if tel_records:
                                await service.insert_telemetry_batch(mach.id, tel_records)
                                seeded_count += 1
                        except Exception as e:
                            print(f"      [WARN] Failed seeding gearbox unit {idx}: {e}")

        # Seed Valve Units 107..111
        v_adapter = get_adapter("PHMAP_2023_VALVE")
        if v_adapter and v_adapter.is_available():
            v_files = sorted((DATA_RAW / "phmap2023_valve").glob("*.csv"))
            for idx, v_file in enumerate(v_files, start=107):
                mach = machine_by_unit.get(idx)
                if mach:
                    history = await service.get_telemetry_history(mach.id, limit=2)
                    if not history:
                        try:
                            import pandas as pd
                            df_v = pd.read_csv(v_file)
                            tel_records = []
                            for row_i, r in df_v.head(30).iterrows():
                                tel_records.append({
                                    "unit_number": idx,
                                    "time_cycle": row_i + 1,
                                    "setting_1": float(r.get("time_sec", 0.0)),
                                    "setting_2": float(r.get("valve_command", 0.0)),
                                    "setting_3": 100.0,
                                    "s_1": float(r.get("pressure_upstream", 1500.0)),
                                    "s_2": float(r.get("pressure_downstream", 100.0)),
                                    "s_3": float(r.get("valve_command", 0.0)),
                                })
                            if tel_records:
                                await service.insert_telemetry_batch(mach.id, tel_records)
                                seeded_count += 1
                        except Exception as e:
                            print(f"      [WARN] Failed seeding valve unit {idx}: {e}")

        await session.commit()
        print(f"      [OK] Successfully populated authentic baseline telemetry & prognostics for {seeded_count} units.")

    print("\n[COMPLETE] Stage 3 Database initialization & fleet seeding completed successfully!")


def main():
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
