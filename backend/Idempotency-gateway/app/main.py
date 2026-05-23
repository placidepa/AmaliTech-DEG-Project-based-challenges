import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.config import settings
from routers import payments
from services import store

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FinSafe Idempotency API starting up...")
    await store.init_redis()

    yield

    logger.info("Shutting down — closing Redis connection...")
    await store.close_redis()


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description=(
        "Payment processing API with strict idempotency guarantees. "
        "Prevents double charges on network retries using per-key locking "
        "and SHA-256 payload fingerprinting."
    ),
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected internal error occurred. Please try again.",
            "path": str(request.url.path),
        },
    )


app.include_router(payments.router)


@app.get("/", tags=["Health"], summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.project_name,
        "version": settings.version,
    }
