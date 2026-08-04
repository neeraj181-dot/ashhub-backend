#!/usr/bin/env python3
"""
PostgreSQL Schema Migration & Verification Script for AshHub
Performs ALTER TABLE schema migrations without using drop_all() / create_all(),
verifies information_schema.columns, and tests registration/login/JWT/OAuth.
"""

import sys
import os
import httpx
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.user import User


def run_migration():
    print("==================================================")
    print("POSTGRESQL MIGRATION & SCHEMA VERIFICATION AUDIT")
    print("==================================================")

    # 1. Inspect existing columns in PostgreSQL users table using information_schema
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)).fetchall()

    before_columns = {row[0]: row[1] for row in res}
    print("\n1. BEFORE MIGRATION - Existing PostgreSQL 'users' columns:")
    for col_name, dtype in before_columns.items():
        print(f"  • {col_name:<25}: {dtype}")

    # Expected target columns and their SQL definitions
    target_columns = {
        "github_id": "INTEGER",
        "github_username": "VARCHAR(255)",
        "github_avatar_url": "VARCHAR(512)",
        "github_access_token": "VARCHAR(255)",
        "github_connected_at": "TIMESTAMP WITH TIME ZONE",
        "is_active": "BOOLEAN DEFAULT TRUE",
        "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
    }

    sql_executed = []
    missing_columns = [col for col in target_columns if col not in before_columns]

    print(f"\n2. DETECTED MISSING COLUMNS ({len(missing_columns)}):")
    if missing_columns:
        for col in missing_columns:
            print(f"  • {col} ({target_columns[col]})")
    else:
        print("  • None (All target columns already present)")

    # 3. Execute ALTER TABLE ADD COLUMN IF NOT EXISTS SQL statements (No drop_all/create_all)
    if missing_columns:
        with engine.begin() as conn:
            for col in missing_columns:
                col_def = target_columns[col]
                sql = f'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "{col}" {col_def};'
                conn.execute(text(sql))
                sql_executed.append(sql)

    # 4 & 5. Verify final schema using information_schema.columns
    with engine.connect() as conn:
        after_res = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)).fetchall()

    after_columns = {row[0]: row[1] for row in after_res}
    print("\n3. SQL MIGRATION EXECUTED:")
    if sql_executed:
        for stmt in sql_executed:
            print(f"  {stmt}")
    else:
        print("  No ALTER TABLE statements required.")

    print("\n4. FINAL POSTGRESQL 'users' TABLE SCHEMA (via information_schema.columns):")
    for col_name, dtype in after_columns.items():
        print(f"  • {col_name:<25}: {dtype}")

    # Check required columns list
    required_cols = [
        "id", "email", "hashed_password", "full_name",
        "github_id", "github_username", "github_avatar_url",
        "github_access_token", "github_connected_at",
        "is_active", "created_at", "updated_at"
    ]
    all_present = all(c in after_columns for c in required_cols)
    print(f"\nAll 12 Required Columns Present: {'YES [OK]' if all_present else 'NO [FAIL]'}")

    # 6, 7, 8, 9, 10. Perform Registration, Login, JWT verification, and OAuth state verification
    print("\n5. END-TO-END VERIFICATION (Registration, Login, JWT & OAuth):")
    test_email = "oauth_repair@ashhub.io"
    test_pass = "RepairPassword123!"

    # Clean up existing test user
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.email == test_email).first()
        if existing:
            session.delete(existing)
            session.commit()
    finally:
        session.close()

    try:
        with httpx.Client(timeout=10.0) as client:
            # Registration
            reg_resp = client.post("http://localhost:8000/auth/register", json={
                "email": test_email,
                "password": test_pass,
                "full_name": "OAuth Repair Tester"
            })
            print(f"  • POST /auth/register Status: {reg_resp.status_code}")
            assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"

            reg_data = reg_resp.json()
            jwt_token = reg_data["token"]["access_token"]
            print(f"  • Generated JWT Access Token: {jwt_token[:30]}...")

            # Login
            login_resp = client.post("http://localhost:8000/auth/login", json={
                "email": test_email,
                "password": test_pass
            })
            print(f"  • POST /auth/login Status: {login_resp.status_code}")
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"

            # GET /auth/me Profile check
            me_resp = client.get("http://localhost:8000/auth/me", headers={"Authorization": f"Bearer {jwt_token}"})
            print(f"  • GET /auth/me Status: {me_resp.status_code}")
            assert me_resp.status_code == 200, f"GET /auth/me failed: {me_resp.text}"

            # OAuth URL generation check
            oauth_resp = client.get("http://localhost:8000/github/login", headers={"Authorization": f"Bearer {jwt_token}"})
            print(f"  • GET /github/login Status: {oauth_resp.status_code}")
            assert oauth_resp.status_code == 200, f"OAuth login failed: {oauth_resp.text}"
            print(f"  • OAuth Login URL: {oauth_resp.json()['url'][:60]}...")

            print("\n==================================================")
            print("[OK] MIGRATION & END-TO-END VERIFICATION COMPLETE!")
            print("==================================================")

    except Exception as e:
        print(f"[X] Verification Error: {e}")


if __name__ == "__main__":
    run_migration()
