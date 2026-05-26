from fastapi import FastAPI
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.exceptions import setup_exception_handlers
from app.limiter import limiter
from app.middleware.logging import LoggingMiddleware
from app.routers import auth, holdings, portfolio, prices

app = FastAPI(
    title="Crypto Portfolio Tracker",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(LoggingMiddleware)

setup_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(holdings.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("server started")
