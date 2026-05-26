from pydantic import BaseModel, ConfigDict

class CoinSummary(BaseModel):
    coin_id: str
    coin_symbol: str
    quantity: float
    avg_buy_price: float
    live_price: float
    current_value: float
    invested_value: float
    pnl: float
    pnl_percent: float

    model_config = ConfigDict(from_attributes=True)

class PortfolioSummary(BaseModel):
    holdings: list[CoinSummary]
    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_percent: float

    model_config = ConfigDict(from_attributes=True)
