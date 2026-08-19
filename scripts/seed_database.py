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

        # 2. Seed Machine Registry (100 Turbofan Units)
        print("\n[2/3] Seeding Machine Registry (100 NASA C-MAPSS Turbofan Units)...")
        existing_machines = await service.get_all_machines()
        
        if len(existing_machines) == 100:
            print(f"      [SKIP] 100 machines already registered in database.")
        else:
            for unit_id in range(1, 101):
                cell_id = (unit_id % 4) + 1
                await service.create_machine(
                    unit_number=unit_id,
                    name=f"Turbofan Engine #{unit_id:03d}",
                    machine_type="Turbofan CF6-80C2",
                    location=f"Test Cell {cell_id}",
                    status="OPERATIONAL"
                )
            await session.commit()
            print(f"      [OK] Successfully registered 100 turbofan units.")

        # 3. Load Initial Baseline Real Telemetry & Run Real Inference for Unit 1 (Cycle 1..30)
        print("\n[3/3] Ingesting real C-MAPSS FD001 baseline telemetry for Unit 1 (Cycles 1..30)...")
        m1 = await service.get_machine_by_unit(1)
        assert m1 is not None

        history = await service.get_telemetry_history(m1.id, limit=5)
        if not history:
            df_train = dataset.load_raw_train()
            unit_1_df = df_train[df_train["unit_number"] == 1].sort_values("time_cycle").reset_index(drop=True)
            baseline_window = unit_1_df.iloc[:30].copy()

            # Ingest real telemetry batch
            records = baseline_window.to_dict(orient="records")
            await service.insert_telemetry_batch(m1.id, records)
            print(f"      [OK] Ingested {len(records)} authentic cycle telemetry records.")

            # Run real Stage 2 inference on baseline window
            engine = get_inference_engine()
            engine.reset_tracker(1)
            
            # Step through cycles 10, 20, 30 to record real prediction progression
            for c in [10, 20, 30]:
                sub_window = unit_1_df.iloc[:c].copy()
                result = engine.predict_window(sub_window)
                await service.persist_inference_cycle(m1.id, result)
            
            await session.commit()
            print(f"      [OK] Executed and persisted 3 real Stage 2 inference cycles for Unit 1.")
        else:
            print("      [SKIP] Telemetry records already exist for Unit 1.")

    print("\n[COMPLETE] Stage 3 Database initialization & seeding completed successfully!")


def main():
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
