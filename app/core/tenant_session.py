from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.exceptions import TenantNotFoundError
from app.db.models import AdmTenant
from app.db.session import SessionLocal as AdminSessionLocal


@lru_cache(maxsize=8)
def _build_engine(database_name: str):
    url = make_url(settings.ADMIN_DB_URL)
    tenant_url = url.set(database=database_name)
    return create_engine(tenant_url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=8)
def _sessionmaker_for_database(database_name: str):
    return sessionmaker(autocommit=False, autoflush=False, bind=_build_engine(database_name))


def get_admin_session():
    return AdminSessionLocal()


def resolve_tenant_code(tenant_id: int) -> str:
    session = get_admin_session()
    try:
        row = session.execute(
            text('SELECT "Id", code, status FROM "adm_Tenant" WHERE "Id" = :tenant_id AND status = 1'),
            {"tenant_id": tenant_id},
        ).mappings().first()
        if not row:
            raise TenantNotFoundError(f"No existe tenant activo para id={tenant_id}")
        return str(row["code"]).strip()
    finally:
        session.close()


def get_tenant_db_name(tenant_id: int) -> str:
    code = resolve_tenant_code(tenant_id)
    return f"{settings.TENANT_DB_PREFIX}{code}"


def get_tenant_session(tenant_id: int):
    db_name = get_tenant_db_name(tenant_id)
    return _sessionmaker_for_database(db_name)()

