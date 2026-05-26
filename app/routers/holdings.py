from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.holding import HoldingCreate, HoldingResponse
from app.services import coingecko

settings = get_settings()
router = APIRouter(prefix="/holdings", tags=["holdings"])

@router.post(
    "",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new holding or update an existing one."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_holding(
    request: Request,
    req: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    coin_list = await coingecko.get_coin_list()
    valid_coin_ids = {coin["id"] for coin in coin_list}
    if req.coin_id not in valid_coin_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coin ID '{req.coin_id}' is not a valid cryptocurrency on CoinGecko"
        )

    stmt = select(Holding).where(
        Holding.user_id == current_user.id,
        Holding.coin_id == req.coin_id
    )
    res = await db.execute(stmt)
    holding = res.scalar_one_or_none()

    if holding:
        existing_qty = float(holding.quantity)
        existing_avg = float(holding.avg_buy_price)
        new_qty = req.quantity
        new_price = req.avg_buy_price

        new_avg = (existing_qty * existing_avg + new_qty * new_price) / (existing_qty + new_qty)
        holding.quantity = Decimal(str(existing_qty + new_qty))
        holding.avg_buy_price = Decimal(str(new_avg))
    else:
        holding = Holding(
            user_id=current_user.id,
            coin_id=req.coin_id,
            coin_symbol=req.coin_symbol,
            quantity=Decimal(str(req.quantity)),
            avg_buy_price=Decimal(str(req.avg_buy_price))
        )
        db.add(holding)

    transaction = Transaction(
        user_id=current_user.id,
        coin_id=req.coin_id,
        type="BUY",
        quantity=Decimal(str(req.quantity)),
        price_at_time=Decimal(str(req.avg_buy_price))
    )
    db.add(transaction)

    await db.commit()
    await db.refresh(holding)
    return holding

@router.get(
    "",
    response_model=list[HoldingResponse],
    summary="Retrieve all holdings for the current user."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_holdings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Holding).where(Holding.user_id == current_user.id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.delete(
    "/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a holding and record a sell transaction."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def delete_holding(
    request: Request,
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Holding).where(
        Holding.id == holding_id,
        Holding.user_id == current_user.id
    )
    res = await db.execute(stmt)
    holding = res.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    prices = await coingecko.get_prices([holding.coin_id])
    if holding.coin_id not in prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Live price not found for coin to complete sale"
        )
    live_price = prices[holding.coin_id]

    transaction = Transaction(
        user_id=current_user.id,
        coin_id=holding.coin_id,
        type="SELL",
        quantity=holding.quantity,
        price_at_time=Decimal(str(live_price))
    )
    db.add(transaction)
    await db.delete(holding)
    await db.commit()
