import pytest
from httpx import AsyncClient
from app.services import coingecko

pytestmark = pytest.mark.asyncio

async def test_get_holdings_empty(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("empty@example.com", "securepassword123")
    response = await async_client.get("/api/v1/holdings", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

async def test_create_holding_success(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("create@example.com", "securepassword123")
    response = await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "bitcoin",
            "coin_symbol": "btc",
            "quantity": 1.5,
            "avg_buy_price": 45000.0
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["coin_id"] == "bitcoin"
    assert data["coin_symbol"] == "btc"
    assert data["quantity"] == 1.5
    assert data["avg_buy_price"] == 45000.0
    assert "id" in data

async def test_create_holding_invalid_quantity(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("invalidqty@example.com", "securepassword123")
    response = await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "bitcoin",
            "coin_symbol": "btc",
            "quantity": -1.0,
            "avg_buy_price": 45000.0
        }
    )
    assert response.status_code == 422

async def test_create_holding_same_coin_twice(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("twice@example.com", "securepassword123")
    await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "bitcoin",
            "coin_symbol": "btc",
            "quantity": 1.0,
            "avg_buy_price": 40000.0
        }
    )
    response = await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "bitcoin",
            "coin_symbol": "btc",
            "quantity": 2.0,
            "avg_buy_price": 50000.0
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["quantity"] == 3.0
    assert abs(data["avg_buy_price"] - 46666.66666667) < 1e-4

async def test_delete_holding_success(async_client: AsyncClient, register_and_login_helper, monkeypatch):
    headers = await register_and_login_helper("delete@example.com", "securepassword123")
    create_response = await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "bitcoin",
            "coin_symbol": "btc",
            "quantity": 2.5,
            "avg_buy_price": 42000.0
        }
    )
    holding_id = create_response.json()["id"]

    async def mock_get_prices(coin_ids):
        return {"bitcoin": 48000.0}
    monkeypatch.setattr(coingecko, "get_prices", mock_get_prices)

    response = await async_client.delete(f"/api/v1/holdings/{holding_id}", headers=headers)
    assert response.status_code == 204

    get_response = await async_client.get("/api/v1/holdings", headers=headers)
    assert get_response.json() == []

async def test_delete_holding_not_found(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("notfound@example.com", "securepassword123")
    response = await async_client.delete("/api/v1/holdings/9999", headers=headers)
    assert response.status_code == 404

async def test_create_holding_invalid_coin_id(async_client: AsyncClient, register_and_login_helper):
    headers = await register_and_login_helper("invalidcoin@example.com", "securepassword123")
    response = await async_client.post(
        "/api/v1/holdings",
        headers=headers,
        json={
            "coin_id": "invalidcoin123",
            "coin_symbol": "inv",
            "quantity": 1.5,
            "avg_buy_price": 45000.0
        }
    )
    assert response.status_code == 400
    assert "not a valid cryptocurrency on CoinGecko" in response.json()["detail"]
