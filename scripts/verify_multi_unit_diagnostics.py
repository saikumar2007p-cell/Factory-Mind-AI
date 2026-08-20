import urllib.request
import json

base_url = "http://127.0.0.1:8000"

def test_multi_unit_predictions():
    units = [1, 2, 5, 15, 30]
    print("=== Testing Unique Predictions Across Units ===")
    results = {}
    for u in units:
        try:
            req = urllib.request.urlopen(f"{base_url}/api/v1/predictions/{u}/latest")
            data = json.loads(req.read().decode("utf-8"))
            rul = data.get("rul_estimate")
            health = data.get("health_index")
            risk = data.get("risk_level")
            print(f"[PASS] Unit #{u:03d} -> RUL: {rul:.1f} cycles, Health: {health:.1f}%, Risk: {risk}")
            results[u] = (rul, health)
        except Exception as e:
            print(f"[FAIL] Unit #{u:03d}: {e}")

    # Check distinct values
    unique_ruls = {v[0] for v in results.values()}
    print(f"Total units tested: {len(results)}, Unique RULs: {len(unique_ruls)}")
    assert len(unique_ruls) > 1, "RUL values must not be identical across different units!"

def test_multi_unit_diagnostics():
    print("\n=== Testing Unit-Specific Diagnostics / RCA ===")
    units = [1, 2, 15]
    for u in units:
        try:
            req = urllib.request.Request(
                f"{base_url}/api/v1/diagnostics/explain",
                data=json.dumps({"machine_id": u}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req)
            diag = json.loads(resp.read().decode("utf-8"))
            print(f"[PASS] Diagnostics for Unit #{u:03d}:")
            print(f"       Summary: {diag.get('summary')}")
            print(f"       Action:  {diag.get('recommended_action')}")
        except Exception as e:
            print(f"[FAIL] Diagnostics Unit #{u:03d}: {e}")

if __name__ == "__main__":
    test_multi_unit_predictions()
    test_multi_unit_diagnostics()
