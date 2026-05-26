from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models.transaction import Transaction
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.holding import TransactionResponse
from app.schemas.portfolio import PortfolioSummary
from app.services import portfolio as portfolio_service

settings = get_settings()
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get(
    "/summary",
    response_model=PortfolioSummary,
    summary="Get current user portfolio summary including P&L calculations."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await portfolio_service.get_portfolio_summary(current_user.id, db)

@router.get(
    "/history",
    response_model=list[TransactionResponse],
    summary="Get transaction history for current user, ordered by timestamp descending."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Transaction).where(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
