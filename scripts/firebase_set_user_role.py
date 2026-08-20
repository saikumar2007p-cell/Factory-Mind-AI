#!/usr/bin/env python3
"""
scripts/firebase_set_user_role.py

Admin CLI script to assign Firebase custom claims (role + organizationId) to a Firebase user.

Usage:
    python scripts/firebase_set_user_role.py --uid <FIREBASE_UID> --role ADMIN --org <ORG_ID>
    python scripts/firebase_set_user_role.py --email user@example.com --role OPERATOR --org factory-001

Security:
    - Requires Firebase Admin service account (FIREBASE_SERVICE_ACCOUNT_PATH env var)
    - Never allow normal frontend users to call this — CLI/admin only
    - Custom claims propagate on next token refresh (user must re-login)
"""

import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Load .env
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")


def main():
    parser = argparse.ArgumentParser(
        description="Set Firebase custom claims (role + organizationId) on a user"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--uid", help="Firebase UID of the target user")
    group.add_argument("--email", help="Email address of the target user (will look up UID)")
    parser.add_argument("--role", required=True, choices=["ADMIN", "OPERATOR", "VIEWER"],
                        help="Role to assign")
    parser.add_argument("--org", required=True, help="Organization ID for tenant isolation")
    parser.add_argument("--sa-path", default=None,
                        help="Path to service account JSON (overrides FIREBASE_SERVICE_ACCOUNT_PATH)")

    args = parser.parse_args()

    # Set service account path if provided
    if args.sa_path:
        os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"] = args.sa_path

    # Initialize Firebase Admin
    from backend.app.firebase_admin_init import init_firebase_admin, get_auth_client
    app = init_firebase_admin()
    if not app:
        print("ERROR: Firebase Admin SDK failed to initialize.")
        print("  Ensure FIREBASE_SERVICE_ACCOUNT_PATH is set in .env or use --sa-path")
        sys.exit(1)

    auth = get_auth_client()

    # Resolve UID
    uid = args.uid
    if args.email:
        try:
            user_record = auth.get_user_by_email(args.email)
            uid = user_record.uid
            print(f"Resolved email '{args.email}' -> UID: {uid}")
        except Exception as e:
            print(f"ERROR: Could not find user with email '{args.email}': {e}")
            sys.exit(1)

    # Verify user exists
    try:
        user_record = auth.get_user(uid)
        print(f"User found: {user_record.email or 'no email'} (UID: {uid})")
        if user_record.custom_claims:
            print(f"Current claims: {json.dumps(user_record.custom_claims, indent=2)}")
        else:
            print("Current claims: (none)")
    except Exception as e:
        print(f"ERROR: User not found: {e}")
        sys.exit(1)

    # Set custom claims
    new_claims = {
        "role": args.role,
        "organizationId": args.org,
    }

    try:
        auth.set_custom_user_claims(uid, new_claims)
        print(f"\n✓ Custom claims SET successfully:")
        print(f"  UID:            {uid}")
        print(f"  Role:           {args.role}")
        print(f"  Organization:   {args.org}")
        print(f"\nThe user must sign out and sign back in to pick up the new claims.")
    except Exception as e:
        print(f"ERROR: Failed to set custom claims: {e}")
        sys.exit(1)

    # Also sync to Firestore
    try:
        from backend.app.services.firestore_service import upsert_user
        success = upsert_user(uid, {
            "email": user_record.email or "",
            "name": user_record.display_name or user_record.email or "",
            "role": args.role,
            "organizationId": args.org,
            "active": not user_record.disabled,
        })
        if success:
            print(f"✓ Firestore users/{uid} synced.")
        else:
            print("⚠ Firestore sync skipped (Firestore may not be initialized).")
    except Exception as e:
        print(f"⚠ Firestore sync failed (non-critical): {e}")


if __name__ == "__main__":
    main()
