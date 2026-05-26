import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_register_success(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "newuser@example.com"

async def test_register_duplicate_email(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "securepassword123"}
    )
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "differentpassword123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

async def test_login_success(async_client: AsyncClient):
    email = "loginuser@example.com"
    password = "securepassword123"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(async_client: AsyncClient):
    email = "wrongpass@example.com"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepassword123"}
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrongpassword123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
