from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from app.config import get_settings
from app.limiter import limiter
from app.routers.auth import get_current_user
from app.models.user import User
from app.services import coingecko

settings = get_settings()
router = APIRouter(prefix="/prices", tags=["prices"])

class PriceResponse(BaseModel):
    coin_id: str
    price_usd: float

@router.get(
    "/{coin_id}",
    response_model=PriceResponse,
    summary="Get live price for a specific coin by ID."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_price(
    request: Request,
    coin_id: str,
    current_user: User = Depends(get_current_user)
):
    prices = await coingecko.get_prices([coin_id])
    if coin_id not in prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coin price not found for id: {coin_id}"
        )
    return PriceResponse(coin_id=coin_id, price_usd=prices[coin_id])
