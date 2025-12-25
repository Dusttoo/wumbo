"""Error handling middleware"""

import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger


async def catch_exceptions_middleware(request: Request, call_next):
    """
    Middleware to catch unhandled exceptions and log them

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response
    """
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
