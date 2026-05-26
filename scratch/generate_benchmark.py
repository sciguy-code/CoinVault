import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.services import coingecko

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def mock_get_prices(coin_ids):
    return {coin_id: 65000.0 for coin_id in coin_ids}

async def mock_get_coin_list():
    return [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]

coingecko.get_prices = mock_get_prices
coingecko.get_coin_list = mock_get_coin_list

async def benchmark_run(iterations: int):
    # Setup tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.limiter.enabled = False
    db_session = TestingSessionLocal()
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    results = {}
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        email = f"bench_{iterations}@example.com"
        password = "securepassword123"

        await client.post("/api/v1/auth/register", json={"email": email, "password": password})
        login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/holdings",
            headers=headers,
            json={"coin_id": "bitcoin", "coin_symbol": "btc", "quantity": 1.0, "avg_buy_price": 50000.0}
        )

        endpoints = {
            "POST Register": lambda: client.post(
                "/api/v1/auth/register",
                json={"email": f"b_{iterations}_{time.perf_counter()}@example.com", "password": password}
            ),
            "POST Login": lambda: client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": password}
            ),
            "GET Live Price": lambda: client.get(
                "/api/v1/prices/bitcoin",
                headers=headers
            ),
            "POST Buy Holding": lambda: client.post(
                "/api/v1/holdings",
                headers=headers,
                json={"coin_id": "bitcoin", "coin_symbol": "btc", "quantity": 0.1, "avg_buy_price": 60000.0}
            ),
            "GET Portfolio Summary": lambda: client.get(
                "/api/v1/portfolio/summary",
                headers=headers
            )
        }

        for name, req_func in endpoints.items():
            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                await req_func()
                latencies.append((time.perf_counter() - start) * 1000)
            results[name] = sum(latencies) / iterations

    await db_session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    return results

async def main():
    data_points = [10, 50, 250]
    all_results = {}

    for dp in data_points:
        print(f"Running benchmarks for iteration count (hyper-parameter): {dp} requests...")
        all_results[dp] = await benchmark_run(dp)

    # Plot Grouped Bar Chart (Premium Sleek Dark Theme)
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

    categories = list(all_results[10].keys())
    x = np.arange(len(categories))
    width = 0.25

    # Modern high-contrast color scheme
    rects1 = ax.bar(x - width, [all_results[10][cat] for cat in categories], width, label="10 Requests", color="#4D96FF")
    rects2 = ax.bar(x, [all_results[50][cat] for cat in categories], width, label="50 Requests", color="#6BCB77")
    rects3 = ax.bar(x + width, [all_results[250][cat] for cat in categories], width, label="250 Requests", color="#FF6B6B")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#888888")

    ax.set_ylabel("Average Latency (ms)", fontsize=11, labelpad=10, color="#AAAAAA")
    ax.set_title("Request Processing Latency Comparison Across Loads", fontsize=15, fontweight="bold", pad=20, color="#FFFFFF")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10, fontweight="medium", color="#DDDDDD")
    ax.legend(frameon=False, fontsize=10, loc="upper right")

    # Add value labels on top of the bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(
                f"{height:.2f}",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),  # 3 points vertical offset
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#FFFFFF"
            )

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    plt.tight_layout()
    plt.savefig("assets/benchmark_comparison.png", transparent=True)
    print("Benchmark comparison graph generated at assets/benchmark_comparison.png")

if __name__ == "__main__":
    asyncio.run(main())
