import sys
import time
from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | {message}",
    level="INFO",
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} {duration:.2f}ms"
        )
        return response
