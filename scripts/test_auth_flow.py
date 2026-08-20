"""
scripts/test_auth_flow.py
Verification test for persistent database registration and login.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.request
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def request_json(path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def main():
    test_email = f"engineer_{uuid.uuid4().hex[:6]}@factorymind.ai"
    test_password = "SecurePassword123!"
    test_name = "Lead Propulsion Engineer Test"

    print(f"--- 1. Testing Registration for {test_email} ---")
    status, reg_resp = request_json("/api/v1/auth/register", {
        "email": test_email,
        "password": test_password,
        "display_name": test_name,
        "role": "OPERATOR"
    })
    assert status == 201, f"Registration failed ({status}): {reg_resp}"
    print(f"[PASS] Registered: User ID={reg_resp.get('user_id')}, Display={reg_resp.get('display_name')}, Role={reg_resp.get('role')}")

    print("--- 2. Testing Duplicate Registration Prevention ---")
    status, dup_resp = request_json("/api/v1/auth/register", {
        "email": test_email,
        "password": test_password,
        "display_name": test_name
    })
    assert status == 400, f"Duplicate was not prevented ({status}): {dup_resp}"
    print("[PASS] Duplicate registration prevented cleanly with HTTP 400")

    print("--- 3. Testing Valid Login ---")
    status, login_resp = request_json("/api/v1/auth/login", {
        "email": test_email,
        "password": test_password
    })
    assert status == 200, f"Login failed ({status}): {login_resp}"
    assert login_resp.get("email") == test_email
    assert login_resp.get("role") == "OPERATOR"
    print(f"[PASS] Logged in successfully: {login_resp.get('message')}, Role={login_resp.get('role')}")

    print("--- 4. Testing Wrong Password Rejection ---")
    status, bad_resp = request_json("/api/v1/auth/login", {
        "email": test_email,
        "password": "WrongPassword999"
    })
    assert status == 401, f"Bad password was not rejected ({status}): {bad_resp}"
    print("[PASS] Bad password rejected with HTTP 401")

    print("\n=======================================================")
    print("ALL AUTHENTICATION DATABASE PERSISTENCE TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    main()
