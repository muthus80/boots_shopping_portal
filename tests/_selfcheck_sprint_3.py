"""
Sprint 3 T-026 acceptance-criteria behavior check.

Exercises GET /api/v1/account/orders against its US-003 acceptance criteria
using FastAPI's in-process TestClient + ephemeral SQLite.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.domains.account.models import User
from app.domains.checkout.models import Order
from app.main import app as fastapi_app

import app.domains.auth.models          # noqa: F401
import app.domains.categories.models    # noqa: F401
import app.domains.products.models      # noqa: F401
import app.domains.cart.models          # noqa: F401
import app.domains.checkout.models      # noqa: F401


@pytest_asyncio.fixture()
async def selfcheck_db_and_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:

        async def _override_db():
            yield session

        fastapi_app.dependency_overrides[get_db] = _override_db
        client = TestClient(fastapi_app, raise_server_exceptions=True)

        yield session, client

    fastapi_app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ac_unauthenticated_returns_401(selfcheck_db_and_client):
    """AC: session expiry → 401, so frontend redirects to login."""
    _, client = selfcheck_db_and_client
    resp = client.get("/api/v1/account/orders")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ac_empty_order_history_returns_message(selfcheck_db_and_client):
    """AC: user with no orders → empty list with descriptive message."""
    db, client = selfcheck_db_and_client

    user = User(
        email=f"selfcheck_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Self Check User",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    resp = client.get("/api/v1/account/orders", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["orders"] == []
    assert body["total"] == 0
    assert body["message"] is not None


@pytest.mark.asyncio
async def test_ac_orders_show_required_fields(selfcheck_db_and_client):
    """AC: each order shows order number, date, total price, status."""
    db, client = selfcheck_db_and_client

    user = User(
        email=f"selfcheck_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Self Check User",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    for i in range(3):
        o = Order(
            order_number=f"ORD-SC-{uuid.uuid4().hex[:6].upper()}",
            user_id=user.id,
            status="confirmed",
            payment_status="paid",
            subtotal=Decimal(f"{(i + 1) * 50}.00"),
            shipping_cost=Decimal("5.00"),
            tax=Decimal("10.00"),
            total=Decimal(f"{(i + 1) * 65}.00"),
            total_amount=Decimal(f"{(i + 1) * 65}.00"),
            currency="GBP",
            shipping_address={"line1": "1 Test Lane", "city": "London"},
        )
        db.add(o)
    await db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    resp = client.get("/api/v1/account/orders", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] == 3
    for o in body["orders"]:
        assert "id" in o
        assert "status" in o
        assert "total_amount" in o
        assert "created_at" in o


@pytest.mark.asyncio
async def test_ac_pagination_narrows_results(selfcheck_db_and_client):
    """AC: page/per_page parameters correctly paginate the result set."""
    db, client = selfcheck_db_and_client

    user = User(
        email=f"selfcheck_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Self Check User",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    for _ in range(3):
        db.add(Order(
            order_number=f"ORD-P-{uuid.uuid4().hex[:6].upper()}",
            user_id=user.id,
            status="confirmed",
            payment_status="paid",
            subtotal=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            tax=Decimal("10.00"),
            total=Decimal("65.00"),
            total_amount=Decimal("65.00"),
            currency="GBP",
            shipping_address={},
        ))
    await db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    resp1 = client.get("/api/v1/account/orders?page=1&per_page=2", headers=headers)
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert len(body1["orders"]) == 2
    assert body1["total"] == 3

    resp2 = client.get("/api/v1/account/orders?page=2&per_page=2", headers=headers)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["orders"]) == 1
    # No overlap between pages
    ids1 = {o["id"] for o in body1["orders"]}
    ids2 = {o["id"] for o in body2["orders"]}
    assert ids1.isdisjoint(ids2)
