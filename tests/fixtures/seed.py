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
    "postgresql://boots_shopping_app_test_app:Py_dbdheMo67t0iSja3kO0o599rEdXCi@localhost:5432/boots_shopping_app_test",
)

# Make the app importable so we can call its own hash helper.
sys.path.insert(0, str(PROJECT_ROOT))


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using the workspace's own bcrypt helper."""
    from app.core.security import hash_password as _hash  # noqa: PLC0415
    return _hash(plaintext)


async def seed_sql(conn) -> None:
    """Execute seed_data.sql then demo_data.sql against the connected DB."""
    for sql_file in [FIXTURES / "seed_data.sql", FIXTURES / "demo_data.sql"]:
        if sql_file.exists():
            sql = sql_file.read_text()
            await conn.execute(sql)
            print(f"  Applied {sql_file.name}")


async def seed_auth_entity(conn) -> None:
    """
    Insert the test-login user row from .elite/test-credentials.json.

    The hashed_password value is computed at seed-time from the plaintext
    stored in the manifest — it is never stored as a literal hash in SQL.
    This is the ONLY code path that produces the auth DB row.
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


async def main() -> None:
    print(f"Connecting to {DATABASE_URL!r} …")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await seed_sql(conn)
        await seed_auth_entity(conn)
    finally:
        await conn.close()
    print("Seeded successfully ✓")


if __name__ == "__main__":
    asyncio.run(main())
