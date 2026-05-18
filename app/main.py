from time import perf_counter
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .api.routers import department, employee
from .core.database import dispose_engine
from .utils import (
    DomainBadRequestError400,
    DomainNotFoundError404,
    DomainConflictError409,
)
from .core.logger import setup_logger, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logger()
    yield
    await dispose_engine()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Emit structured request logs with timing."""
    logger = get_logger("http")
    start = perf_counter()
    response = await call_next(request)
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


@app.exception_handler(DomainBadRequestError400)
async def bad_request_handler(request: Request, exc: DomainBadRequestError400) -> JSONResponse:
    """Invalid input; maps to HTTP 400"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


@app.exception_handler(DomainNotFoundError404)
async def not_found_handler(request: Request, exc: DomainNotFoundError404) -> JSONResponse:
    """Map missing entities to HTTP 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


@app.exception_handler(DomainConflictError409)
async def conflict_handler(request: Request, exc: DomainConflictError409) -> JSONResponse:
    """Map domain conflicts to HTTP 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


@app.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(department.router)
app.include_router(employee.router)
