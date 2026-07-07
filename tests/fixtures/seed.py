#!/usr/bin/env python3
"""Seed the database with fixture data for boots-shopping-app."""
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

FIXTURES = Path(__file__).parent
PROJECT_ROOT = FIXTURES.parent.parent
MANIFEST = PROJECT_ROOT / ".elite" / "test-credentials.json"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://boots_shopping_app_test_app:Qwsj2Yk1W8PeGRfxVGK2bx7SPOqjEtnk@localhost:5432/boots_shopping_app_test",
)

# Make the app importable so we can call its own hash helper.
sys.path.insert(0, str(PROJECT_ROOT))


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using the workspace's own bcrypt helper."""
    from app.core.security import hash_password as _hash  # noqa: PLC0415
    return _hash(plaintext)


async def seed_sql(conn, sql_file: Path) -> None:
    """Execute a single SQL fixture file against the connected DB."""
    if sql_file.exists():
        await conn.execute(sql_file.read_text())
        print(f"  Applied {sql_file.name}")


async def seed_auth_entity(conn) -> None:
    """
    Insert the test-login user row from .elite/test-credentials.json.

    The hashed_password value is computed at seed-time from the plaintext
    stored in the manifest — it is never stored as a literal hash in SQL.
    This is the ONLY code path that produces the primary auth DB row.
    """
    if not MANIFEST.exists():
        print("  No .elite/test-credentials.json found — skipping auth seed.")
        return

    m = json.loads(MANIFEST.read_text())
    table = m["entity_table"]               # "users"
    field = m["auth_id_field"]              # "email"
    value = m["auth_id_value"]              # "test.user@demo.local"
    secret = hash_password(m["password_plaintext"])
    extra = dict(m.get("extra_columns") or {})

    hash_column = "hashed_password"  # column name from app/domains/account/models.py

    # Build the INSERT using positional placeholders for asyncpg.
    cols = [field, hash_column, *extra.keys()]
    vals = [value, secret, *extra.values()]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT ({field}) DO UPDATE SET {hash_column} = EXCLUDED.{hash_column}"
    )
    await conn.execute(sql, *vals)

    # Sanity-check: the row must be retrievable or the E2E login will 401.
    found = await conn.fetchval(
        f"SELECT 1 FROM {table} WHERE {field} = $1", value
    )
    assert found, f"Auth entity not seeded: {table}.{field}={value!r}"
    print(f"  Auth entity seeded: {table}.{field}={value!r}")


async def seed_demo_users(conn) -> None:
    """
    Insert demo user rows (alice, bob, carol) used by demo_data.sql FK references.
    Passwords are hashed at seed-time — no literal hash values in SQL files.
    """
    demo_password = hash_password("DemoPass123!")
    demo_users = [
        {
            "id": "00000000-0000-0000-0000-000000000401",
            "email": "alice.johnson@demo.local",
            "hashed_password": demo_password,
            "full_name": "Alice Johnson",
            "is_active": True,
            "is_superuser": False,
            "created_at": "2026-01-15 08:00:00+00",
            "updated_at": "2026-01-15 08:00:00+00",
        },
        {
            "id": "00000000-0000-0000-0000-000000000402",
            "email": "bob.smith@demo.local",
            "hashed_password": demo_password,
            "full_name": "Bob Smith",
            "is_active": True,
            "is_superuser": False,
            "created_at": "2026-01-16 09:30:00+00",
            "updated_at": "2026-01-16 09:30:00+00",
        },
        {
            "id": "00000000-0000-0000-0000-000000000403",
            "email": "carol.white@demo.local",
            "hashed_password": demo_password,
            "full_name": "Carol White",
            "is_active": True,
            "is_superuser": False,
            "created_at": "2026-01-17 10:00:00+00",
            "updated_at": "2026-01-17 10:00:00+00",
        },
    ]
    for u in demo_users:
        await conn.execute(
            """
            INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, $8::timestamptz)
            ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """,
            u["id"], u["email"], u["hashed_password"], u["full_name"],
            u["is_active"], u["is_superuser"], u["created_at"], u["updated_at"],
        )
    print(f"  Demo users seeded: {len(demo_users)} rows")


async def main() -> None:
    print(f"Connecting to {DATABASE_URL!r} …")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 1. Reference/lookup data (categories) — no user FK deps.
        await seed_sql(conn, FIXTURES / "seed_data.sql")
        # 2. Demo users — must exist before demo_data.sql references their IDs
        #    (carts.user_id, orders.user_id, reviews.user_id).
        await seed_demo_users(conn)
        # 3. Primary test-login user from the credentials manifest.
        await seed_auth_entity(conn)
        # 4. Transactional demo rows (products, variants, carts, orders, reviews).
        await seed_sql(conn, FIXTURES / "demo_data.sql")
    finally:
        await conn.close()
    print("Seeded successfully ✓")


if __name__ == "__main__":
    asyncio.run(main())
