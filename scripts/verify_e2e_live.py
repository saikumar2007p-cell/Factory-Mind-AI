"""
scripts/verify_e2e_live.py

Live Full-Stack End-to-End Release Validation for FactoryMind AI.
Tests every API endpoint, ML prediction, Gemini RCA, Work Order lifecycle,
Fleet Intelligence, Continuous Learning, and RBAC security on the live server.
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def api_call(path, method="GET", body=None, role="ADMIN", actor="Validation Engine"):
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-Admin-Role": role.lower(),
        "X-Actor-Name": actor
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_body = response.read().decode("utf-8")
            status_code = response.status
            return status_code, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"error": err_body}
    except Exception as e:
        return 500, {"error": str(e)}

def run_e2e_validation():
    print("================================================================================")
    print("FACTORYMIND AI — LIVE FULL-STACK END-TO-END VALIDATION")
    print("================================================================================")

    # 1. Healthcheck
    status, data = api_call("/health")
    assert status == 200, f"Healthcheck failed: {status}"
    assert data.get("status") == "HEALTHY", f"Unhealthy status: {data}"
    print("[PASS] 1. Backend Healthcheck (Status: HEALTHY)")

    # 2. List Machines
    status, data = api_call("/api/v1/machines")
    assert status == 200, f"List machines failed: {status}"
    machines = data.get("machines", [])
    assert len(machines) >= 100, f"Expected at least 100 machines, got {len(machines)}"
    print(f"[PASS] 2. Fleet Registry: {len(machines)} Turbofan Units Available")

    # 3. Single Machine Details
    status, data = api_call("/api/v1/machines/1")
    assert status == 200, f"Get machine 1 failed: {status}"
    assert data.get("unit_number") == 1
    print(f"[PASS] 3. Machine #001 Details: {data.get('name')} ({data.get('location')})")

    # 4. Telemetry Retrieval
    status, data = api_call("/api/v1/telemetry/1?limit=30")
    assert status == 200, f"Get telemetry failed: {status}"
    tel_records = data.get("telemetry", [])
    assert len(tel_records) > 0, "No telemetry records found"
    print(f"[PASS] 4. Machine Telemetry: {len(tel_records)} authentic cycle frames loaded")

    # 5. Latest Prediction
    status, data = api_call("/api/v1/predictions/1/latest")
    assert status == 200, f"Get prediction failed: {status}"
    assert "rul_estimate" in data
    assert "anomaly_score" in data
    assert "health_index" in data
    print(f"[PASS] 5. Stage 2 ML Prognostics: RUL={data['rul_estimate']:.1f} cycles, Health={data['health_index']:.1f}%, Risk={data['risk_level']}")

    # 6. Gemini Grounded Root-Cause Analysis (RCA)
    status, data = api_call("/api/v1/diagnostics/explain", method="POST", body={"machine_id": 1})
    assert status == 200, f"Diagnostics failed: {status}"
    assert "summary" in data
    assert "evidence" in data and len(data["evidence"]) >= 1
    assert "recommended_action" in data
    print(f"[PASS] 6. Grounded Gemini AI Diagnostics: {data['summary']} (Source: {data.get('source', 'gemini')})")

    # 7. List Active Alerts
    status, data = api_call("/api/v1/alerts")
    assert status == 200, f"List alerts failed: {status}"
    alerts = data.get("alerts", [])
    print(f"[PASS] 7. Active Alerts Ledger: {len(alerts)} alerts retrieved")

    # 8. Complete 5-Stage Work Order Lifecycle
    print("\n--- Testing Stage 8 Closed-Loop Work Order Lifecycle ---")
    
    # 8a. Create Work Order
    status, wo = api_call("/api/v1/work-orders", method="POST", body={
        "machine_id": 1,
        "title": "Live E2E Verification: LPT Coolant Orifice Inspection",
        "recommended_action": "Perform borescope inspection on Low Pressure Turbine coolant orifice W32.",
        "affected_subsystem": "Low Pressure Turbine",
        "priority": "HIGH",
        "assigned_to": "Unassigned"
    }, role="OPERATOR", actor="Field Tech Sarah")
    assert status == 201, f"Create work order failed: {status}, {wo}"
    wo_id = wo["id"]
    wo_code = wo["work_order_code"]
    assert wo["status"] == "OPEN"
    print(f"[PASS] 8a. Created Work Order: {wo_code} (Status: {wo['status']})")

    # 8b. Assign Technician
    status, wo = api_call(f"/api/v1/work-orders/{wo_id}/assign", method="POST", body={
        "assigned_to": "Lead Propulsion Engineer Michael",
        "notes": "Assigned for immediate borescope diagnostic sweep"
    }, role="OPERATOR", actor="Supervisor Dan")
    assert status == 200, f"Assign work order failed: {status}, {wo}"
    assert wo["status"] == "ASSIGNED"
    assert wo["assigned_to"] == "Lead Propulsion Engineer Michael"
    print(f"[PASS] 8b. Assigned Work Order: Assigned to {wo['assigned_to']} (Status: {wo['status']})")

    # 8c. Start Execution
    status, wo = api_call(f"/api/v1/work-orders/{wo_id}/start", method="POST", role="OPERATOR", actor="Lead Propulsion Engineer Michael")
    assert status == 200, f"Start work order failed: {status}, {wo}"
    assert wo["status"] == "IN_PROGRESS"
    print(f"[PASS] 8c. Started Execution: (Status: {wo['status']})")

    # 8d. Complete Task
    status, wo = api_call(f"/api/v1/work-orders/{wo_id}/complete", method="POST", role="OPERATOR", actor="Lead Propulsion Engineer Michael")
    assert status == 200, f"Complete work order failed: {status}, {wo}"
    assert wo["status"] == "VERIFICATION_REQUIRED"
    print(f"[PASS] 8d. Completed Physical Work: (Status: {wo['status']})")

    # 8e. Perform Verification Sign-Off
    status, wo = api_call(f"/api/v1/work-orders/{wo_id}/verify", method="POST", body={
        "verification_status": "RESOLVED",
        "verification_notes": "Borescope inspection confirmed nominal clearance. Sensor W32 returned to baseline."
    }, role="OPERATOR", actor="QA Inspector Rebecca")
    assert status == 200, f"Verify work order failed: {status}, {wo}"
    assert wo["status"] == "VERIFIED"
    assert wo["verification_status"] == "RESOLVED"
    print(f"[PASS] 8e. Verification Sign-Off: Result={wo['verification_status']} (Status: {wo['status']})")

    # 8f. Invariant: Verified Work Orders are Immutable
    status, err = api_call(f"/api/v1/work-orders/{wo_id}/assign", method="POST", body={
        "assigned_to": "Another Tech"
    }, role="OPERATOR")
    assert status == 422, f"Expected 422 Unprocessable for mutating verified work order, got {status}"
    print(f"[PASS] 8f. Immutability Invariant: Mutation on VERIFIED order correctly rejected (HTTP 422)")

    # 9. Post-Maintenance Telemetry Comparison
    status, comp = api_call(f"/api/v1/work-orders/{wo_id}/comparison")
    assert status == 200, f"Comparison failed: {status}"
    assert "before" in comp
    print(f"[PASS] 9. Before/After Telemetry Comparison Verified")

    # 10. Fleet Intelligence Endpoints (Stage 9)
    print("\n--- Testing Stage 9 Fleet Intelligence & Decision Support ---")
    status, fleet_sum = api_call("/api/v1/fleet/summary")
    assert status == 200
    assert fleet_sum.get("total_machines") >= 100
    print(f"[PASS] 10a. Fleet Summary: {fleet_sum['total_machines']} total units, {fleet_sum['healthy_count']} healthy")

    status, risk_dist = api_call("/api/v1/fleet/risk-distribution")
    assert status == 200
    print(f"[PASS] 10b. Fleet Risk Distribution: {risk_dist.get('risk_categories', {})}")

    status, attention = api_call("/api/v1/fleet/attention-required")
    assert status == 200
    print(f"[PASS] 10c. Attention Queue: {attention.get('total_attention_required', 0)} units prioritized")

    status, planning = api_call("/api/v1/fleet/planning")
    assert status == 200
    print(f"[PASS] 10d. Fleet Planning: {planning.get('total_recommendations', 0)} planning directives")

    # 11. Continuous Learning Endpoints (Stage 10)
    print("\n--- Testing Stage 10 Continuous Learning & Executive Intelligence ---")
    status, exec_sum = api_call("/api/v1/learning/executive-summary")
    assert status == 200
    print(f"[PASS] 11a. Executive Learning Summary: Verified Outcomes={exec_sum.get('verified_outcomes_count')}, Effectiveness={exec_sum.get('maintenance_effectiveness_label')}")

    status, recur = api_call("/api/v1/learning/recurring-failures")
    assert status == 200
    print(f"[PASS] 11b. Recurring Pattern Recognition: {len(recur)} recurring signatures detected")

    status, signals = api_call("/api/v1/learning/signals")
    assert status == 200
    print(f"[PASS] 11c. Continuous Learning Signals: {signals.get('total_signals', 0)} active empirical signals")

    # 12. Security & RBAC Enforcement (Stage 11)
    print("\n--- Testing Stage 11 RBAC & Security Enforcement ---")
    
    # 12a. VIEWER Role is forbidden from creating work orders
    status, err = api_call("/api/v1/work-orders", method="POST", body={
        "machine_id": 1,
        "title": "Unauthorized Order",
        "recommended_action": "Should be rejected"
    }, role="VIEWER")
    assert status == 403, f"Expected 403 Forbidden for VIEWER mutation, got {status}"
    print("[PASS] 12a. RBAC Enforcement: VIEWER mutation attempt correctly rejected (HTTP 403 Forbidden)")

    # 12b. OPERATOR Role is forbidden from modifying data source configs
    status, err = api_call("/api/v1/sources/set-active/rest_api_connector", method="POST", role="OPERATOR")
    assert status == 403, f"Expected 403 Forbidden for OPERATOR data source config, got {status}"
    print("[PASS] 12b. RBAC Enforcement: OPERATOR data source change correctly rejected (HTTP 403 Forbidden)")

    # 12c. Security Audit Logs Retrieval (ADMIN only)
    status, audit = api_call("/api/v1/auth/security-audit-logs?limit=20", role="ADMIN")
    assert status == 200, f"Security logs failed: {status}"
    assert "logs" in audit
    print(f"[PASS] 12c. Security Audit Trail: {audit.get('total_events', len(audit['logs']))} security events recorded in immutable log")

    # 12d. VIEWER cannot access Security Audit Logs
    status, err = api_call("/api/v1/auth/security-audit-logs", role="VIEWER")
    assert status == 403, f"Expected 403 for VIEWER accessing security logs, got {status}"
    print("[PASS] 12d. RBAC Enforcement: VIEWER security logs access correctly rejected (HTTP 403 Forbidden)")

    print("\n================================================================================")
    print("ALL 12 END-TO-END VALIDATION GATES PASSED CLEANLY WITH ZERO ERRORS!")
    print("================================================================================")

if __name__ == "__main__":
    run_e2e_validation()
