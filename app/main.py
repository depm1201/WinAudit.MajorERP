import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import router as major_router
from app.core.config import settings
from app.core.exceptions import ClientNotFoundError, MajorERPError, StorageError, TenantNotFoundError, ValidationError
from app.core.logging_config import setup_logging

setup_logging(service="api", level=settings.LOG_LEVEL)

logger = logging.getLogger("majorerp.api")
request_logger = logging.getLogger("majorerp.api.requests")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Servicio para carga y validacion del mayor contable de Contifico.",
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(major_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "logo": "/static/majorerp-logo.svg",
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
    logger.info("ALLOWED_ORIGINS: %s", ",".join(settings.allowed_origins))


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Error de validacion | method=%s url=%s errors=%s",
        request.method,
        request.url,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validacion",
            "error": "RequestValidationError",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTPException | method=%s url=%s status=%s detail=%s",
        request.method,
        request.url,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "StarletteHTTPException | method=%s url=%s status=%s detail=%s",
        request.method,
        request.url,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(ValidationError)
async def domain_validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning(
        "Error de dominio | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(ClientNotFoundError)
async def client_not_found_exception_handler(request: Request, exc: ClientNotFoundError):
    logger.warning(
        "Cliente no encontrado | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(TenantNotFoundError)
async def tenant_not_found_exception_handler(request: Request, exc: TenantNotFoundError):
    logger.warning(
        "Tenant no encontrado | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(StorageError)
async def storage_error_exception_handler(request: Request, exc: StorageError):
    logger.error(
        "Error de storage | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )


@app.exception_handler(MajorERPError)
async def major_error_exception_handler(request: Request, exc: MajorERPError):
    logger.warning(
        "Error de negocio | method=%s url=%s error=%s",
        request.method,
        request.url,
        exc,
    )
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error": exc.__class__.__name__,
        },
    )
