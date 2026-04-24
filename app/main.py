import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import router as major_router
from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging(service="api", level=settings.LOG_LEVEL)

logger = logging.getLogger("majorerp.api")
request_logger = logging.getLogger("majorerp.api.requests")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Servicio para carga y validacion del mayor contable de Contifico.",
)

app.include_router(major_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.on_event("startup")
def on_startup():
    logger.info("===== %s iniciando =====", settings.PROJECT_NAME)
    logger.info("ADMIN_DB_URL: %s", settings.ADMIN_DB_URL.split("@")[-1])
    logger.info("STORAGE: %s", settings.storage_path)
    logger.info("LOGS: %s", settings.logs_path)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    started = time.perf_counter()
    client_ip = request.client.host if request.client else "-"
    method = request.method
    path = request.url.path
    query = request.url.query
    route = f"{path}?{query}" if query else path

    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        request_logger.info(
            "REQ method=%s path=%s client=%s status=%s elapsed_ms=%.2f",
            method,
            route,
            client_ip,
            response.status_code,
            elapsed_ms,
        )
        return response
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        request_logger.exception(
            "REQ method=%s path=%s client=%s status=500 elapsed_ms=%.2f",
            method,
            route,
            client_ip,
            elapsed_ms,
        )
        raise


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Error no manejado | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)},
    )
