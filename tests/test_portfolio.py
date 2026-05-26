import pytest
from httpx import AsyncClient
from app.services import coingecko

pytestmark = pytest.mark.asyncio

async def test_portfolio_summary_structure(async_client: AsyncClient, register_and_login_helper, monkeypatch):
    headers = await register_and_login_helper("summary@example.com", "securepassword123")
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={"coin_id": "bitcoin", "coin_symbol": "btc", "quantity": 1.5, "avg_buy_price": 30000.0}
    )
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={"coin_id": "ethereum", "coin_symbol": "eth", "quantity": 10.0, "avg_buy_price": 2000.0}
    )

    async def mock_get_prices(coin_ids):
        return {"bitcoin": 40000.0, "ethereum": 2500.0}
    monkeypatch.setattr(coingecko, "get_prices", mock_get_prices)

    response = await async_client.get("/api/v1/portfolio/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "holdings" in data
    assert "total_invested" in data
    assert "total_current_value" in data
    assert "total_pnl" in data
    assert "total_pnl_percent" in data

    for holding in data["holdings"]:
        assert "coin_id" in holding
        assert "coin_symbol" in holding
        assert "quantity" in holding
        assert "avg_buy_price" in holding
        assert "live_price" in holding
        assert "current_value" in holding
        assert "invested_value" in holding
        assert "pnl" in holding
        assert "pnl_percent" in holding

async def test_portfolio_pnl_calculation(async_client: AsyncClient, register_and_login_helper, monkeypatch):
    headers = await register_and_login_helper("pnl@example.com", "securepassword123")
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={"coin_id": "bitcoin", "coin_symbol": "btc", "quantity": 1.5, "avg_buy_price": 30000.0}
    )

    async def mock_get_prices(coin_ids):
        return {"bitcoin": 40000.0}
    monkeypatch.setattr(coingecko, "get_prices", mock_get_prices)

    response = await async_client.get("/api/v1/portfolio/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_invested"] == 45000.0
    assert data["total_current_value"] == 60000.0
    assert data["total_pnl"] == 15000.0
    assert abs(data["total_pnl_percent"] - 33.33333333) < 1e-4

async def test_portfolio_history(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("history@example.com", "securepassword123")
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={"coin_id": "bitcoin", "coin_symbol": "btc", "quantity": 1.0, "avg_buy_price": 40000.0}
    )
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={"coin_id": "ethereum", "coin_symbol": "eth", "quantity": 5.0, "avg_buy_price": 2000.0}
    )

    response = await async_client.get("/api/v1/portfolio/history", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 2
    timestamps = [tx["timestamp"] for tx in data]
    assert timestamps == sorted(timestamps, reverse=True)
