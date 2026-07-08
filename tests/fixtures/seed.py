#!/usr/bin/env python3
"""Seed the database with fixture data.

Responsibilities
----------------
1. Execute seed_data.sql (reference/lookup rows).
2. Execute demo_data.sql (transactional demo rows).
3. If .elite/test-credentials.json exists, insert ONE row into the auth-entity
   table (users) with the plaintext password from the manifest passed through
   the workspace's own bcrypt hash function.

The test user is always inserted at UUID 00000000-0000-0000-0000-000000000001
so that demo_data.sql FK references (order history, reviews, carts) resolve
correctly.
"""

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
    "postgresql://boots_shopping_app_test_app:Vff8CLjkgAEcSCLILhxUxOXbZFFzYQMI@localhost:5432/boots_shopping_app_test",
)

# Make the app importable so we can call its own hash helper.
sys.path.insert(0, str(PROJECT_ROOT))


async def ensure_schema() -> None:
    """Ensure all ORM tables exist in the target database before seeding.

    This is the schema-bootstrap step for E2E test environments where
    `alembic upgrade head` has not been run (QA-fix: relation 'products'
    does not exist at Playwright runtime).

    SQLAlchemy create_all uses IF NOT EXISTS semantics — safe to run
    against a database that already has the full Alembic-managed schema.
    """
    # Build the asyncpg-compatible URL for SQLAlchemy
    sa_url = DATABASE_URL
    if sa_url.startswith("postgresql://"):
        sa_url = sa_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif sa_url.startswith("postgres://"):
        sa_url = sa_url.replace("postgres://", "postgresql+asyncpg://", 1)

    from sqlalchemy.ext.asyncio import create_async_engine
    from app.core.database import Base  # noqa: F401 — registers DeclarativeBase

    # Import all domain models so Base.metadata is fully populated
    import app.domains.account.models  # noqa: F401
    import app.domains.auth.models  # noqa: F401
    import app.domains.categories.models  # noqa: F401
    import app.domains.products.models  # noqa: F401
    import app.domains.cart.models  # noqa: F401
    import app.domains.checkout.models  # noqa: F401

    engine = create_async_engine(sa_url, echo=False, future=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("  Schema bootstrapped via SQLAlchemy create_all (idempotent).")
    finally:
        await engine.dispose()


def hash_password(plaintext: str) -> str:
    """Hash using the workspace's own bcrypt helper (app.core.security)."""
    from app.core.security import hash_password as _hash  # noqa: PLC0415
    return _hash(plaintext)


async def seed_sql(conn: asyncpg.Connection) -> int:
    """Execute seed_data.sql and demo_data.sql; return total statements run."""
    total = 0
    for sql_file in [FIXTURES / "seed_data.sql", FIXTURES / "demo_data.sql"]:
        if sql_file.exists():
            await conn.execute(sql_file.read_text())
            total += 1
    return total


async def seed_auth_entity(conn: asyncpg.Connection) -> None:
    """Insert the test user row whose password hash is computed at seed-time.

    The test user UUID is pinned to 00000000-0000-0000-0000-000000000001 so
    that demo_data.sql rows referencing that UUID remain consistent.
    """
    if not MANIFEST.exists():
        return  # No auth story in scope — nothing to insert.

    m = json.loads(MANIFEST.read_text())
    table = m["entity_table"]           # "users"
    field = m["auth_id_field"]          # "email"
    value = m["auth_id_value"]          # "test.user@demo.local"
    secret = hash_password(m["password_plaintext"])
    extra = dict(m.get("extra_columns") or {})

    # Pinned UUID so FK references in demo_data.sql resolve.
    pinned_id = "00000000-0000-0000-0000-000000000001"
    hash_column = "hashed_password"

    cols = ["id", field, hash_column, *extra.keys()]
    vals = [pinned_id, value, secret, *extra.values()]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    col_list = ", ".join(cols)

    sql = (
        f"INSERT INTO {table} ({col_list}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT ({field}) DO UPDATE SET "
        f"  {hash_column} = EXCLUDED.{hash_column}, "
        f"  id = EXCLUDED.id"
    )
    await conn.execute(sql, *vals)

    # Verify the row exists — fail loudly rather than silently break E2E login.
    found = await conn.fetchval(
        f"SELECT 1 FROM {table} WHERE {field} = $1", value
    )
    assert found, f"Auth entity not seeded: {table}.{field}={value!r}"
    print(f"  Auth entity seeded: {table}.{field}={value!r} (id={pinned_id})")


async def main() -> None:
    print("Ensuring schema exists …")
    await ensure_schema()

    print(f"Connecting to database …")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Applying seed_data.sql and demo_data.sql …")
        await seed_sql(conn)
        print("Seeding auth entity …")
        await seed_auth_entity(conn)
    finally:
        await conn.close()
    print("Seeded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
