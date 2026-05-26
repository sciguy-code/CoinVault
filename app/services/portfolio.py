from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.holding import Holding
from app.schemas.portfolio import PortfolioSummary, CoinSummary
from app.services import coingecko

async def get_portfolio_summary(user_id: int, db: AsyncSession) -> PortfolioSummary:
    stmt = select(Holding).where(Holding.user_id == user_id)
    result = await db.execute(stmt)
    holdings = result.scalars().all()

    if not holdings:
        return PortfolioSummary(
            holdings=[],
            total_invested=0.0,
            total_current_value=0.0,
            total_pnl=0.0,
            total_pnl_percent=0.0
        )

    coin_ids = list(set(h.coin_id for h in holdings))
    prices = await coingecko.get_prices(coin_ids)

    coin_summaries = []
    total_invested = 0.0
    total_current_value = 0.0

    for h in holdings:
        qty = float(h.quantity)
        avg_price = float(h.avg_buy_price)
        live_price = float(prices.get(h.coin_id, 0.0))

        invested_value = qty * avg_price
        current_value = qty * live_price
        pnl = current_value - invested_value
        pnl_percent = (pnl / invested_value * 100.0) if invested_value > 0.0 else 0.0

        coin_summaries.append(
            CoinSummary(
                coin_id=h.coin_id,
                coin_symbol=h.coin_symbol,
                quantity=qty,
                avg_buy_price=avg_price,
                live_price=live_price,
                current_value=current_value,
                invested_value=invested_value,
                pnl=pnl,
                pnl_percent=pnl_percent
            )
        )

        total_invested += invested_value
        total_current_value += current_value

    total_pnl = total_current_value - total_invested
    total_pnl_percent = (total_pnl / total_invested * 100.0) if total_invested > 0.0 else 0.0

    return PortfolioSummary(
        holdings=coin_summaries,
        total_invested=total_invested,
        total_current_value=total_current_value,
        total_pnl=total_pnl,
        total_pnl_percent=total_pnl_percent
    )
