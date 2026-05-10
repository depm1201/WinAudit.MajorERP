from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.v1.schemas import (
    MajorBatchResponse,
    MajorEntryResponse,
    MajorImportResponse,
    MajorMappingResponse,
    MajorMappingSyncResponse,
    MajorReconciliationRunResponse,
    MajorValidationResponse,
    MajorValidationRunResponse,
)
from app.core.auth import verify_token
from app.core.exceptions import ClientNotFoundError, MajorERPError, StorageError, TenantNotFoundError, ValidationError
from app.core.tenant_session import get_tenant_session
from app.repositories.major_repository import MajorRepository
from app.services.major_import_service import MajorImportService
from app.services.major_export_service import MajorExportService
from app.services.major_mapping_service import MajorMappingService
from app.services.major_reconciliation_service import MajorReconciliationService
from app.services.major_validation_service import MajorValidationService

router = APIRouter(tags=["major"], dependencies=[Depends(verify_token)])
repository = MajorRepository()
service = MajorImportService()
export_service = MajorExportService()
validation_service = MajorValidationService()
mapping_service = MajorMappingService()
reconciliation_service = MajorReconciliationService()


@router.post("/major/import", response_model=MajorImportResponse, status_code=202)
async def import_major(
    tenant_id: int = Form(...),
    ruc: str = Form(...),
    fiscal_period: str | None = Form(None),
    file: UploadFile = File(...),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="El archivo no puede estar vacio.")

    try:
        result = service.import_major_workbook(
            tenant_id=tenant_id,
            client_ruc=ruc,
            file_name=file.filename or "major.xlsx",
            file_bytes=content,
            fiscal_period_hint=fiscal_period,
        )
        return MajorImportResponse(**result.__dict__)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValidationError, StorageError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MajorERPError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/major/imports/{batch_id}/validate", response_model=MajorValidationRunResponse)
def validate_import_batch(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        summary = validation_service.validate_batch(session, batch_id)
        session.commit()
        return MajorValidationRunResponse(
            batch_id=summary.batch_id,
            validation_status=summary.validation_status,
            issues=summary.issues,
            warnings=summary.warnings,
            errors=summary.errors,
            message=summary.message,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/major/imports/{batch_id}/reconcile", response_model=MajorReconciliationRunResponse)
def reconcile_import_batch(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        summary = reconciliation_service.reconcile_batch(session, batch_id)
        session.commit()
        return MajorReconciliationRunResponse(
            batch_id=summary.batch_id,
            reconciliation_status=summary.reconciliation_status,
            total_accounts=summary.total_accounts,
            matched_accounts=summary.matched_accounts,
            catalog_only_accounts=summary.catalog_only_accounts,
            mapping_only_accounts=summary.mapping_only_accounts,
            missing_accounts=summary.missing_accounts,
            warnings=summary.warnings,
            errors=summary.errors,
            message=summary.message,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/major/imports/{batch_id}/export")
def export_import_batch(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        summary = export_service.export_batch(session, batch_id, tenant_id)
        session.commit()
        return FileResponse(
            summary.file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=summary.file_name,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/major/imports/{batch_id}", response_model=MajorBatchResponse)
def get_import_batch(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        batch = repository.get_import_batch(session, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado.")
        return MajorBatchResponse(
            id=batch.id,
            client_id=batch.client_id,
            batch_type=batch.batch_type,
            source_system=batch.source_system,
            report_code=batch.report_code,
            report_name=batch.report_name,
            fiscal_period=batch.fiscal_period,
            sheet_name=batch.sheet_name,
            row_count=batch.row_count,
            debit_total=float(batch.debit_total or 0),
            credit_total=float(batch.credit_total or 0),
            balance_total=float(batch.balance_total or 0),
            validation_status=batch.validation_status,
            validation_message=batch.validation_message,
            stored_file_path=batch.stored_file_path,
            original_file_name=batch.original_file_name,
        )
    finally:
        session.close()


@router.get("/major/imports/{batch_id}/entries", response_model=list[MajorEntryResponse])
def get_import_entries(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        batch = repository.get_import_batch(session, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado.")

        if batch.batch_type == "MAYOR_CONTIFICO" and batch.report_code == "ACCOUNT_CATALOG":
            rows = repository.list_account_rows(session, batch_id)
            return [
                MajorEntryResponse(
                    id=row.id,
                    source_row=row.source_row,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    row_type="ACCOUNT",
                    validation_status="LOADED",
                )
                for row in rows
            ]

        rows = repository.list_ledger_rows(session, batch_id)
        return [
            MajorEntryResponse(
                id=row.id,
                source_row=row.source_row,
                account_code=row.account_code,
                account_name=row.account_name,
                row_type=row.row_type,
                transaction_date=row.transaction_date.isoformat() if row.transaction_date else None,
                description=row.description,
                debit=float(row.debit or 0) if row.debit is not None else None,
                credit=float(row.credit or 0) if row.credit is not None else None,
                balance=float(row.balance or 0) if row.balance is not None else None,
                related_document=row.related_document,
                cost_center=row.cost_center,
                project=row.project,
                person_name=row.person_name,
                cross_ref_person=row.cross_ref_person,
                validation_status="LOADED",
            )
            for row in rows
        ]
    finally:
        session.close()


@router.get("/major/imports/{batch_id}/validations", response_model=list[MajorValidationResponse])
def get_import_validations(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        batch = repository.get_import_batch(session, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado.")

        rows = repository.list_validation_rows(session, batch_id, scope="MAYOR")
        return [
            MajorValidationResponse(
                id=row.id,
                validation_code=row.validation_code,
                validation_name=row.validation_name,
                validation_scope=row.validation_scope,
                source_account_code=row.source_account_code,
                source_row=row.source_row,
                expected_value=float(row.expected_value or 0) if row.expected_value is not None else None,
                actual_value=float(row.actual_value or 0) if row.actual_value is not None else None,
                difference_value=float(row.difference_value or 0) if row.difference_value is not None else None,
                result_status=row.result_status,
                detail_json=row.detail_json,
            )
            for row in rows
        ]
    finally:
        session.close()


@router.get("/major/imports/{batch_id}/reconciliation", response_model=list[MajorValidationResponse])
def get_import_reconciliation(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        batch = repository.get_import_batch(session, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado.")

        rows = repository.list_validation_rows(session, batch_id, scope="RECONCILIATION")
        return [
            MajorValidationResponse(
                id=row.id,
                validation_code=row.validation_code,
                validation_name=row.validation_name,
                validation_scope=row.validation_scope,
                source_account_code=row.source_account_code,
                source_row=row.source_row,
                expected_value=float(row.expected_value or 0) if row.expected_value is not None else None,
                actual_value=float(row.actual_value or 0) if row.actual_value is not None else None,
                difference_value=float(row.difference_value or 0) if row.difference_value is not None else None,
                result_status=row.result_status,
                detail_json=row.detail_json,
            )
            for row in rows
        ]
    finally:
        session.close()


@router.get("/major/accounts")
def list_major_accounts(tenant_id: int = 1, ruc: str | None = None):
    session = get_tenant_session(tenant_id)
    try:
        if not ruc:
            raise HTTPException(status_code=422, detail="ruc es requerido para consultar el catalogo de cuentas.")
        client = repository.get_client_by_ruc(session, ruc)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        rows = repository.list_catalog_accounts(session, client.id)
        return [
            {
                "id": row.id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "parent_account_code": row.parent_account_code,
                "account_level": row.account_level,
                "account_path": row.account_path,
                "is_group": row.is_group,
                "source_sheet": row.source_sheet,
                "source_row": row.source_row,
            }
            for row in rows
        ]
    finally:
        session.close()


@router.get("/major/accounts/{account_code}")
def get_major_account(account_code: str, tenant_id: int = 1, ruc: str | None = None):
    session = get_tenant_session(tenant_id)
    try:
        if not ruc:
            raise HTTPException(status_code=422, detail="ruc es requerido para consultar una cuenta.")
        client = repository.get_client_by_ruc(session, ruc)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        row = repository.get_catalog_account(session, client.id, account_code)
        if not row:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        return {
            "id": row.id,
            "account_code": row.account_code,
            "account_name": row.account_name,
            "parent_account_code": row.parent_account_code,
            "account_level": row.account_level,
            "account_path": row.account_path,
            "is_group": row.is_group,
            "source_sheet": row.source_sheet,
            "source_row": row.source_row,
        }
    finally:
        session.close()


@router.get("/major/mappings", response_model=list[MajorMappingResponse])
def list_major_mappings(tenant_id: int = 1, ruc: str | None = None):
    session = get_tenant_session(tenant_id)
    try:
        if not ruc:
            raise HTTPException(status_code=422, detail="ruc es requerido para consultar los mapeos contables.")
        client = repository.get_client_by_ruc(session, ruc)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        rows = repository.list_account_mappings(session, client.id)
        return [
            MajorMappingResponse(
                id=row.id,
                retention_percentage=float(row.retention_percentage) if row.retention_percentage is not None else None,
                target_account_code=row.target_account_code,
                tax_type=row.tax_type,
                status=row.status,
            )
            for row in rows
        ]
    finally:
        session.close()


@router.post("/major/mappings/sync/catalog", response_model=MajorMappingSyncResponse)
def sync_major_mappings_from_catalog(tenant_id: int = 1, ruc: str | None = None):
    session = get_tenant_session(tenant_id)
    try:
        if not ruc:
            raise HTTPException(status_code=422, detail="ruc es requerido para sincronizar mapeos.")
        client = repository.get_client_by_ruc(session, ruc)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        summary = mapping_service.sync_from_latest_catalog(session, client.id)
        session.commit()
        return MajorMappingSyncResponse(**summary.__dict__)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/major/mappings/sync/batch/{batch_id}", response_model=MajorMappingSyncResponse)
def sync_major_mappings_from_batch(batch_id: int, tenant_id: int = 1):
    session = get_tenant_session(tenant_id)
    try:
        summary = mapping_service.sync_from_batch(session, batch_id)
        session.commit()
        return MajorMappingSyncResponse(**summary.__dict__)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()
