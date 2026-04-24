from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ClientNotFoundError, StorageError, ValidationError
from app.core.tenant_session import get_tenant_session
from app.db.models import AccImportBatch
from app.parser.major_excel_parser import MajorExcelParser, ParsedMajorWorkbook
from app.repositories.major_repository import MajorRepository
from app.services.major_validation_service import MajorValidationService
from app.storage.major_storage_manager import MajorStorageManager


@dataclass
class MajorImportResult:
    status: str
    message: str
    batch_id: int | None = None
    tenant_id: int | None = None
    client_id: int | None = None
    fiscal_period: str | None = None
    sheet_name: str | None = None
    report_type: str | None = None
    rows_processed: int = 0
    account_rows: int = 0
    ledger_rows: int = 0
    validation_status: str | None = None
    validation_issues: int = 0
    validation_warnings: int = 0
    validation_errors: int = 0


class MajorImportService:
    def __init__(self) -> None:
        self._repo = MajorRepository()
        self._parser = MajorExcelParser()
        self._storage = MajorStorageManager()
        self._validator = MajorValidationService()

    def import_major_workbook(
        self,
        *,
        tenant_id: int,
        client_ruc: str,
        file_name: str,
        file_bytes: bytes,
        fiscal_period_hint: str | None = None,
    ) -> MajorImportResult:
        session = get_tenant_session(tenant_id)
        batch: AccImportBatch | None = None
        try:
            client = self._repo.get_client_by_ruc(session, client_ruc)
            if not client:
                raise ClientNotFoundError(f"No se encontro cliente para RUC {client_ruc}")

            tenant_code = self._resolve_tenant_code(tenant_id)
            parsed_file_path = self._persist_raw_file(
                tenant_code=tenant_code,
                ruc=client_ruc,
                file_name=file_name,
                file_bytes=file_bytes,
                fiscal_period=fiscal_period_hint or "UNKNOWN",
            )
            file_hash = self._hash_bytes(file_bytes)

            batch = self._repo.create_import_batch(
                session,
                client_id=client.id,
                batch_type="MAYOR_CONTIFICO",
                source_system="CONTIFICO",
                report_code=None,
                report_name=None,
                fiscal_period=fiscal_period_hint,
                period_start=None,
                period_end=None,
                original_file_name=file_name,
                stored_file_path=str(parsed_file_path),
                file_hash=file_hash,
                sheet_name=None,
                row_count=0,
                debit_total=0,
                credit_total=0,
                balance_total=0,
                validation_status="PENDING",
                validation_message=None,
                status=1,
            )
            session.commit()

            parsed = self._parser.parse(parsed_file_path, fiscal_period_hint=fiscal_period_hint)
            result = self._persist_parsed_workbook(session, batch, tenant_id, client.id, parsed, parsed_file_path)
            validation_summary = self._validator.validate_batch(session, batch.id)
            result.validation_status = validation_summary.validation_status
            result.validation_issues = validation_summary.issues
            result.validation_warnings = validation_summary.warnings
            result.validation_errors = validation_summary.errors
            session.commit()
            return result
        except ValidationError as exc:
            session.rollback()
            if batch:
                self._repo.update_import_batch(
                    session,
                    batch,
                    validation_status="INVALID",
                    validation_message=str(exc),
                )
                session.commit()
            return self._mark_batch_error(session, tenant_id, client_ruc, file_name, str(exc), fiscal_period_hint)
        except Exception as exc:
            session.rollback()
            if batch:
                self._repo.update_import_batch(
                    session,
                    batch,
                    validation_status="ERROR",
                    validation_message=str(exc),
                )
                session.commit()
            return self._mark_batch_error(session, tenant_id, client_ruc, file_name, str(exc), fiscal_period_hint)
        finally:
            session.close()

    def _persist_parsed_workbook(
        self,
        session: Session,
        batch: AccImportBatch,
        tenant_id: int,
        client_id: int,
        parsed: ParsedMajorWorkbook,
        file_path: Path,
    ) -> MajorImportResult:
        account_rows = len(parsed.account_rows)
        ledger_rows = len(parsed.ledger_rows)
        debit_total, credit_total, balance_total = parsed.ledger_totals()

        if parsed.report_type == "ACCOUNT_CATALOG":
            inserted = self._repo.save_account_catalog_rows(
                session,
                client_id=client_id,
                import_batch_id=batch.id,
                rows=[self._account_row_dict(row, file_path.name) for row in parsed.account_rows],
            )
        elif parsed.report_type == "LEDGER":
            inserted = self._repo.save_main_ledger_rows(
                session,
                client_id=client_id,
                import_batch_id=batch.id,
                fiscal_period=parsed.fiscal_period,
                rows=[self._ledger_row_dict(row, file_path.name) for row in parsed.ledger_rows],
            )
        else:
            raise ValidationError(f"Tipo de reporte no soportado: {parsed.report_type}")

        self._repo.update_import_batch(
            session,
            batch,
            report_code=parsed.report_type,
            report_name=parsed.report_name,
            fiscal_period=parsed.fiscal_period,
            sheet_name=parsed.sheet_name,
            row_count=parsed.row_count,
            debit_total=debit_total,
            credit_total=credit_total,
            balance_total=balance_total,
            validation_status="LOADED",
            validation_message="Carga completada correctamente",
            updated_at=datetime.utcnow(),
        )
        if parsed.warnings:
            self._repo.save_validation_results(
                session,
                client_id=client_id,
                import_batch_id=batch.id,
                rows=[
                    {
                        "validation_code": "WARN_TEMPLATE",
                        "validation_name": "Advertencia de plantilla",
                        "validation_scope": "MAYOR",
                        "source_account_code": None,
                        "source_row": None,
                        "expected_value": None,
                        "actual_value": None,
                        "difference_value": None,
                        "result_status": "WARN",
                        "detail_json": {"message": warning},
                    }
                    for warning in parsed.warnings
                ],
            )

        return MajorImportResult(
            status="LOADED",
            message=f"Se importaron {inserted} registros correctamente.",
            batch_id=batch.id,
            tenant_id=tenant_id,
            client_id=client_id,
            fiscal_period=parsed.fiscal_period,
            sheet_name=parsed.sheet_name,
            report_type=parsed.report_type,
            rows_processed=parsed.row_count,
            account_rows=account_rows,
            ledger_rows=ledger_rows,
            validation_status=batch.validation_status,
        )

    def _mark_batch_error(
        self,
        session: Session,
        tenant_id: int,
        client_ruc: str,
        file_name: str,
        error_message: str,
        fiscal_period_hint: str | None,
    ) -> MajorImportResult:
        return MajorImportResult(
            status="ERROR",
            message=error_message,
            tenant_id=tenant_id,
        )

    def _persist_raw_file(
        self,
        *,
        tenant_code: str,
        ruc: str,
        file_name: str,
        file_bytes: bytes,
        fiscal_period: str,
    ) -> Path:
        target_dir = self._storage.ensure_paths(tenant_code, ruc, fiscal_period)
        raw_dir = target_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        target_file = raw_dir / file_name
        try:
            target_file.write_bytes(file_bytes)
        except Exception as exc:
            raise StorageError(f"No se pudo guardar el archivo original: {exc}") from exc
        return target_file

    def _resolve_tenant_code(self, tenant_id: int) -> str:
        from app.core.tenant_session import resolve_tenant_code

        return resolve_tenant_code(tenant_id)

    def _hash_bytes(self, file_bytes: bytes) -> str:
        return sha256(file_bytes).hexdigest()

    def _account_row_dict(self, row, source_file: str) -> dict:
        return {
            "account_code": row.account_code,
            "account_name": row.account_name,
            "parent_account_code": row.parent_account_code,
            "account_level": row.account_level,
            "account_path": row.account_path,
            "sort_order": row.sort_order,
            "source_sheet": row.source_sheet,
            "source_row": row.source_row,
            "is_group": row.is_group,
            "source_file": source_file,
            "tax_category": row.tax_category,
            "tax_type": row.tax_type,
        }

    def _ledger_row_dict(self, row, source_file: str) -> dict:
        return {
            "row_type": row.row_type,
            "account_code": row.account_code,
            "account_name": row.account_name,
            "transaction_date": row.transaction_date,
            "description": row.description,
            "debit": row.debit,
            "credit": row.credit,
            "balance": row.balance,
            "related_document": row.related_document,
            "cost_center": row.cost_center,
            "project": row.project,
            "person_name": row.person_name,
            "cross_ref_person": row.cross_ref_person,
            "tax_category": row.tax_category,
            "journal_entry": row.journal_entry,
            "tax_id": row.tax_id,
            "source_file": source_file,
            "source_sheet": row.source_sheet,
            "source_row": row.source_row,
        }
