import pytest
from fastapi import HTTPException
import tenacity
from httpx import AsyncClient
from app.services import coingecko

pytestmark = pytest.mark.asyncio

async def test_get_price_success(async_client: AsyncClient, register_and_login_helper, monkeypatch):
    headers = await register_and_login_helper("price_user@example.com", "securepassword123")

    async def mock_get_prices(coin_ids):
        return {"bitcoin": 45000.0}
    monkeypatch.setattr(coingecko, "get_prices", mock_get_prices)

    response = await async_client.get("/api/v1/prices/bitcoin", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["coin_id"] == "bitcoin"
    assert data["price_usd"] == 45000.0

async def test_get_price_coin_not_found(async_client: AsyncClient, register_and_login_helper, monkeypatch):
    headers = await register_and_login_helper("price_user2@example.com", "securepassword123")

    async def mock_get_prices(coin_ids):
        return {}
    monkeypatch.setattr(coingecko, "get_prices", mock_get_prices)

    response = await async_client.get("/api/v1/prices/invalidcoin", headers=headers)
    assert response.status_code == 404
    assert "Coin price not found" in response.json()["detail"]

async def test_coingecko_retries_on_failure(monkeypatch):
    monkeypatch.setattr(coingecko.settings, "COINGECKO_BASE_URL", "http://localhost:9999")
    monkeypatch.setattr(coingecko._fetch_prices.retry, "wait", tenacity.wait_none())

    with pytest.raises(HTTPException) as exc_info:
        await coingecko.get_prices(["bitcoin"])
    
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "CoinGecko service unavailable"
    assert coingecko._fetch_prices.retry.statistics["attempt_number"] == 3
