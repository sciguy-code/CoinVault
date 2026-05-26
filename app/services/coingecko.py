import time
from fastapi import HTTPException
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings

settings = get_settings()

_coin_list_cache = {
    "data": None,
    "timestamp": 0.0
}

def log_retry(retry_state):
    logger.warning(
        f"Coingecko API retry attempt {retry_state.attempt_number} after exception: {retry_state.outcome.exception()}"
    )

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    before_sleep=log_retry
)
async def _fetch_prices(coin_ids: list[str]) -> dict[str, float]:
    async with httpx.AsyncClient(base_url=settings.COINGECKO_BASE_URL) as client:
        response = await client.get(
            "/simple/price",
            params={
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd"
            }
        )
        response.raise_for_status()
        data = response.json()
        result = {}
        for coin_id in coin_ids:
            if coin_id in data and "usd" in data[coin_id]:
                result[coin_id] = float(data[coin_id]["usd"])
        return result

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    before_sleep=log_retry
)
async def _fetch_coin_list() -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.COINGECKO_BASE_URL) as client:
        response = await client.get("/coins/list")
        response.raise_for_status()
        return response.json()

async def get_prices(coin_ids: list[str]) -> dict[str, float]:
    if not coin_ids:
        return {}
    start_time = time.perf_counter()
    try:
        prices = await _fetch_prices(coin_ids)
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Coingecko get_prices call for {coin_ids} completed in {duration:.2f}ms"
        )
        return prices
    except Exception as exc:
        logger.error(f"Coingecko get_prices failed: {exc}")
        raise HTTPException(status_code=503, detail="CoinGecko service unavailable")

async def get_coin_list() -> list[dict]:
    now = time.time()
    if _coin_list_cache["data"] is not None and (now - _coin_list_cache["timestamp"]) < 3600:
        return _coin_list_cache["data"]
    start_time = time.perf_counter()
    try:
        data = await _fetch_coin_list()
        _coin_list_cache["data"] = data
        _coin_list_cache["timestamp"] = now
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(f"Coingecko get_coin_list completed in {duration:.2f}ms")
        return data
    except Exception as exc:
        logger.error(f"Coingecko get_coin_list failed: {exc}")
        raise HTTPException(status_code=503, detail="CoinGecko service unavailable")
