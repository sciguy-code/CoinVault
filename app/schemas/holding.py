from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class HoldingCreate(BaseModel):
    coin_id: str
    coin_symbol: str
    quantity: float = Field(..., gt=0)
    avg_buy_price: float = Field(..., gt=0)

class HoldingResponse(BaseModel):
    id: int
    user_id: int
    coin_id: str
    coin_symbol: str
    quantity: float
    avg_buy_price: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    coin_id: str
    type: str
    quantity: float
    price_at_time: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
