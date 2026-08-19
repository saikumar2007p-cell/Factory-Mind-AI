"""
scripts/verify_stage8_live.py

Live End-to-End Operational Verification Script for Stage 8.
Connects directly to http://127.0.0.1:8000 to test live API contracts,
strict lifecycle transitions, invalid transition protections, audit trail persistence,
and anti-hallucination safeguards.
"""

import sys
import json
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-Admin-Role": "admin"}

def run_live_verification():
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10.0)
    print("==================================================")
    print("STAGE 8 LIVE END-TO-END VERIFICATION")
    print("==================================================")

    # 1. Startup & Data Sources
    print("\n[STEP 1] Verifying Backend Startup & Data Sources...")
    res = client.get("/health")
    assert res.status_code == 200, f"Healthcheck failed: {res.status_code}"
    health_data = res.json()
    print(f"  -> Healthcheck OK: Status={health_data['status']}, DB={health_data.get('database')}")

    res_src = client.get("/sources/active")
    assert res_src.status_code == 200, f"Active source query failed: {res_src.status_code}"
    active_src = res_src.json()
    print(f"  -> Active Data Source: {active_src['name']} (Status: {active_src['status']})")
    assert active_src["source_type"] == "CMAPSS_SIMULATION"
    assert active_src["status"] == "CONNECTED"

    # 2. Machine Registry
    print("\n[STEP 2] Verifying Machine Registry...")
    res_m = client.get("/machines")
    assert res_m.status_code == 200
    m_data = res_m.json()
    machines = m_data.get("machines", []) if isinstance(m_data, dict) else m_data
    assert len(machines) > 0, "No machines registered!"
    m_id = machines[0]["id"]
    print(f"  -> Target Machine: ID={m_id}, Unit #{machines[0]['unit_number']} ({machines[0]['name']})")

    # 3. Work Order Creation & Deterministic Priority
    print("\n[STEP 3] Testing Work Order Creation...")
    payload = {
        "machine_id": m_id,
        "title": "Stage 8 Live Overhaul & Inspection",
        "recommended_action": "Borescope inspect Low Pressure Turbine stator vanes and verify bleed valves.",
        "affected_subsystem": "Low Pressure Turbine",
        "risk_level": "CRITICAL",
        "ml_evidence": {"rul_estimate": 14.5, "anomaly_score": 0.42},
        "assigned_to": "Unassigned"
    }
    res_wo = client.post("/work-orders", json=payload)
    assert res_wo.status_code == 201, f"Work order creation failed: {res_wo.status_code} {res_wo.text}"
    wo = res_wo.json()
    wo_id = wo["id"]
    wo_code = wo["work_order_code"]
    print(f"  -> Work Order Created: Code={wo_code} (ID={wo_id}), Priority={wo['priority']}, Status={wo['status']}")
    assert wo["status"] == "OPEN"
    assert wo["priority"] == "CRITICAL"
    assert wo["assigned_to"] == "Unassigned"
    assert wo["created_at"] is not None

    # 4. Strict Lifecycle Protections (OPEN cannot Start/Complete/Verify)
    print("\n[STEP 4] Testing Backend Protection on OPEN state...")
    # 4a. OPEN -> START
    res_bad_start = client.post(f"/work-orders/{wo_id}/start")
    assert res_bad_start.status_code == 422, f"Expected 422 on OPEN->START, got {res_bad_start.status_code}"
    print(f"  -> OPEN -> START correctly rejected with HTTP 422: {res_bad_start.json()['detail']}")

    # 4b. OPEN -> COMPLETE
    res_bad_comp = client.post(f"/work-orders/{wo_id}/complete")
    assert res_bad_comp.status_code == 422, f"Expected 422 on OPEN->COMPLETE, got {res_bad_comp.status_code}"
    print(f"  -> OPEN -> COMPLETE correctly rejected with HTTP 422: {res_bad_comp.json()['detail']}")

    # 4c. OPEN -> VERIFY
    res_bad_verif = client.post(f"/work-orders/{wo_id}/verify", json={"verification_status": "RESOLVED"})
    assert res_bad_verif.status_code == 422, f"Expected 422 on OPEN->VERIFY, got {res_bad_verif.status_code}"
    print(f"  -> OPEN -> VERIFY correctly rejected with HTTP 422: {res_bad_verif.json()['detail']}")

    # 5. Assignment (OPEN -> ASSIGNED)
    print("\n[STEP 5] Testing Technician Assignment (OPEN -> ASSIGNED)...")
    res_assign = client.post(f"/work-orders/{wo_id}/assign", json={"assigned_to": "Marcus Brody (Lead Tech)"})
    assert res_assign.status_code == 200, f"Assignment failed: {res_assign.status_code} {res_assign.text}"
    wo_assigned = res_assign.json()
    assert wo_assigned["status"] == "ASSIGNED"
    assert wo_assigned["assigned_to"] == "Marcus Brody (Lead Tech)"
    print(f"  -> Assigned successfully: Status={wo_assigned['status']}, AssignedTo='{wo_assigned['assigned_to']}'")

    # 6. Backend Protection on ASSIGNED state
    print("\n[STEP 6] Testing Backend Protection on ASSIGNED state...")
    # 6a. ASSIGNED -> COMPLETE
    res_bad_comp2 = client.post(f"/work-orders/{wo_id}/complete")
    assert res_bad_comp2.status_code == 422
    print(f"  -> ASSIGNED -> COMPLETE correctly rejected with HTTP 422")

    # 6b. ASSIGNED -> VERIFY
    res_bad_verif2 = client.post(f"/work-orders/{wo_id}/verify", json={"verification_status": "RESOLVED"})
    assert res_bad_verif2.status_code == 422
    print(f"  -> ASSIGNED -> VERIFY correctly rejected with HTTP 422")

    # 7. Start Execution (ASSIGNED -> IN_PROGRESS)
    print("\n[STEP 7] Testing Start Execution (ASSIGNED -> IN_PROGRESS)...")
    res_start = client.post(f"/work-orders/{wo_id}/start")
    assert res_start.status_code == 200, f"Start failed: {res_start.status_code}"
    wo_in_prog = res_start.json()
    assert wo_in_prog["status"] == "IN_PROGRESS"
    assert wo_in_prog["started_at"] is not None
    print(f"  -> Started execution: Status={wo_in_prog['status']}, StartedAt={wo_in_prog['started_at']}")

    # 8. Backend Protection on IN_PROGRESS state
    print("\n[STEP 8] Testing Backend Protection on IN_PROGRESS state...")
    # 8a. IN_PROGRESS -> VERIFY directly
    res_bad_verif3 = client.post(f"/work-orders/{wo_id}/verify", json={"verification_status": "RESOLVED"})
    assert res_bad_verif3.status_code == 422
    print(f"  -> IN_PROGRESS -> VERIFY correctly rejected with HTTP 422")

    # 9. Complete Maintenance (IN_PROGRESS -> VERIFICATION_REQUIRED)
    print("\n[STEP 9] Testing Completion (IN_PROGRESS -> VERIFICATION_REQUIRED)...")
    res_comp = client.post(f"/work-orders/{wo_id}/complete")
    assert res_comp.status_code == 200, f"Complete failed: {res_comp.status_code}"
    wo_comp = res_comp.json()
    assert wo_comp["status"] == "VERIFICATION_REQUIRED"
    assert wo_comp["completed_at"] is not None
    assert wo_comp["verification_status"] == "PENDING"
    print(f"  -> Completed: Status={wo_comp['status']}, CompletedAt={wo_comp['completed_at']}, VerifStatus={wo_comp['verification_status']}")

    # 10. Verification Sign-Off (VERIFICATION_REQUIRED -> VERIFIED)
    print("\n[STEP 10] Testing Verification Sign-Off (VERIFICATION_REQUIRED -> VERIFIED)...")
    res_verif = client.post(f"/work-orders/{wo_id}/verify", json={
        "verification_status": "RESOLVED",
        "verification_notes": "Borescope inspection confirmed zero stator cracks; vibration spectra within nominal baseline."
    })
    assert res_verif.status_code == 200, f"Verification failed: {res_verif.status_code}"
    wo_verified = res_verif.json()
    assert wo_verified["status"] == "VERIFIED"
    assert wo_verified["verification_status"] == "RESOLVED"
    assert wo_verified["verified_at"] is not None
    print(f"  -> Verified: Status={wo_verified['status']}, Outcome={wo_verified['verification_status']}, VerifiedAt={wo_verified['verified_at']}")

    # 11. Operational Audit Trail
    print("\n[STEP 11] Verifying Operational Audit History...")
    res_detail = client.get(f"/work-orders/{wo_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    audit_logs = detail_data.get("audit_logs", [])
    print(f"  -> Retrieved {len(audit_logs)} audit records from database:")
    for log in audit_logs:
        print(f"     * [{log['timestamp']}] {log['event_type']} by {log['actor']} -> {log.get('notes', '')}")
    event_types = [l["event_type"] for l in audit_logs]
    assert "CREATED" in event_types
    assert "ASSIGNED" in event_types
    assert "STARTED" in event_types
    assert "COMPLETED" in event_types
    assert "VERIFIED" in event_types

    # 12. Post-Maintenance Telemetry Comparison
    print("\n[STEP 12] Verifying Post-Maintenance Telemetry Comparison...")
    res_comp_telemetry = client.get(f"/work-orders/{wo_id}/comparison")
    assert res_comp_telemetry.status_code == 200
    comp_obj = res_comp_telemetry.json()
    print(f"  -> Comparison Result: has_post_maintenance_data={comp_obj['has_post_maintenance_data']}, message='{comp_obj['message']}'")
    assert comp_obj["before"] is not None

    # 13. Summary Statistics
    print("\n[STEP 13] Verifying Work Orders Summary KPI Counts...")
    res_sum = client.get("/work-orders/summary")
    assert res_sum.status_code == 200
    summary = res_sum.json()
    print(f"  -> Live Operational Summary: {json.dumps(summary, indent=2)}")
    assert summary["total_work_orders"] >= 1
    assert summary["verified_count"] >= 1

    print("\n==================================================")
    print("ALL LIVE END-TO-END VERIFICATION CHECKS PASSED [OK]")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_live_verification()
    except Exception as e:
        print(f"\n[FAILED] Live verification encountered an error: {e}", file=sys.stderr)
        sys.exit(1)
