from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from operator import attrgetter

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.db.models import AccImportBatch
from app.repositories.major_repository import MajorRepository


@dataclass
class MajorValidationSummary:
    batch_id: int
    validation_status: str
    issues: int
    warnings: int
    errors: int
    message: str


class MajorValidationService:
    def __init__(self) -> None:
        self._repo = MajorRepository()

    def validate_batch(self, session: Session, batch_id: int) -> MajorValidationSummary:
        batch = self._repo.get_import_batch(session, batch_id)
        if not batch:
            raise ValidationError("Batch no encontrado.")

        self._repo.delete_validation_rows(session, batch_id, scope="MAYOR")

        issues: list[dict] = []
        if batch.report_code == "ACCOUNT_CATALOG":
            issues.extend(self._validate_account_catalog(session, batch))
        elif batch.report_code == "LEDGER":
            issues.extend(self._validate_ledger(session, batch))
        else:
            raise ValidationError(f"Tipo de reporte no soportado para validacion: {batch.report_code}")

        warning_count = sum(1 for row in issues if row["result_status"] == "WARN")
        error_count = sum(1 for row in issues if row["result_status"] == "ERROR")

        if issues:
            self._repo.save_validation_results(session, batch.client_id, batch.id, issues)

        if error_count:
            validation_status = "VALIDATED_WITH_ERRORS"
            message = f"Validacion finalizada con {error_count} errores y {warning_count} advertencias."
        elif warning_count:
            validation_status = "VALIDATED_WITH_WARNINGS"
            message = f"Validacion finalizada con {warning_count} advertencias."
        else:
            validation_status = "VALIDATED"
            message = "Validacion completada sin observaciones."

        self._repo.update_import_batch(
            session,
            batch,
            validation_status=validation_status,
            validation_message=message,
        )

        return MajorValidationSummary(
            batch_id=batch.id,
            validation_status=validation_status,
            issues=len(issues),
            warnings=warning_count,
            errors=error_count,
            message=message,
        )

    def _validate_account_catalog(self, session: Session, batch: AccImportBatch) -> list[dict]:
        rows = self._repo.list_account_rows(session, batch.id)
        issues: list[dict] = []
        seen_codes: dict[str, int] = {}
        codes = {row.account_code for row in rows}

        for row in rows:
            if row.account_code in seen_codes:
                issues.append(
                    self._issue(
                        code="DUP_ACCOUNT_CODE",
                        name="Codigo de cuenta duplicado",
                        status="ERROR",
                        source_row=row.source_row,
                        account_code=row.account_code,
                        detail={"first_row": seen_codes[row.account_code], "duplicate_row": row.source_row},
                    )
                )
            else:
                seen_codes[row.account_code] = row.source_row or 0

            if row.parent_account_code and row.parent_account_code not in codes:
                issues.append(
                    self._issue(
                        code="ORPHAN_PARENT",
                        name="Cuenta padre inexistente",
                        status="ERROR",
                        source_row=row.source_row,
                        account_code=row.account_code,
                        detail={"parent_account_code": row.parent_account_code},
                    )
                )

        return issues

    def _validate_ledger(self, session: Session, batch: AccImportBatch) -> list[dict]:
        rows = self._repo.list_ledger_rows(session, batch.id)
        issues: list[dict] = []
        catalog_rows = self._repo.list_catalog_accounts(session, batch.client_id)
        known_accounts = {row.account_code for row in catalog_rows}
        catalog_codes = known_accounts

        for row in rows:
            if row.account_code not in known_accounts:
                if self._repo.get_account_mapping_by_target_code(session, batch.client_id, row.account_code):
                    continue
                family_prefix = self._find_catalog_family_prefix(row.account_code, catalog_codes)
                status = "WARN" if family_prefix else "ERROR"
                issues.append(
                    self._issue(
                        code="UNKNOWN_ACCOUNT" if status == "ERROR" else "FAMILY_ACCOUNT_NOT_EXPLICIT",
                        name="Cuenta no existe en catalogo" if status == "ERROR" else "Cuenta no cargada explicitamente en catalogo",
                        status=status,
                        source_row=row.source_row,
                        account_code=row.account_code,
                        detail={
                            "account_code": row.account_code,
                            "family_prefix": family_prefix,
                        },
                    )
                )

        for account_code, account_rows_iter in groupby(sorted(rows, key=lambda item: (item.account_code, item.source_row or 0, item.id)), key=attrgetter("account_code")):
            account_rows = list(account_rows_iter)
            previous_balance: Decimal | None = None
            opening_seen = False

            for row in account_rows:
                if row.row_type == "OPENING":
                    opening_seen = True
                    previous_balance = row.balance
                    continue

                if row.balance is None:
                    continue

                debit = row.debit or Decimal("0")
                credit = row.credit or Decimal("0")
                base_balance = previous_balance if previous_balance is not None else Decimal("0")
                expected_balance = base_balance + debit - credit

                if self._has_balance_gap(expected_balance, row.balance):
                    issues.append(
                        self._issue(
                            code="BALANCE_SEQUENCE_ERROR",
                            name="Secuencia de saldo inconsistente",
                            status="ERROR",
                            source_row=row.source_row,
                            account_code=account_code,
                            detail={
                                "expected_balance": str(expected_balance),
                                "actual_balance": str(row.balance),
                                "debit": str(debit),
                                "credit": str(credit),
                                "opening_seen": opening_seen,
                            },
                        )
                    )
                previous_balance = row.balance

            if not opening_seen and account_rows and account_rows[0].balance is not None:
                issues.append(
                    self._issue(
                        code="MISSING_OPENING_ROW",
                        name="No existe fila de saldo anterior",
                        status="WARN",
                        source_row=account_rows[0].source_row,
                        account_code=account_code,
                        detail={"account_code": account_code},
                    )
                )

        return issues

    def _find_catalog_family_prefix(self, account_code: str, catalog_codes: set[str]) -> str | None:
        parts = [part for part in account_code.split(".") if part]
        for size in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:size])
            if any(code == prefix or code.startswith(f"{prefix}.") for code in catalog_codes):
                return prefix
        return None

    def _issue(
        self,
        *,
        code: str,
        name: str,
        status: str,
        source_row: int | None,
        account_code: str | None,
        detail: dict,
    ) -> dict:
        return {
            "validation_code": code,
            "validation_name": name,
            "validation_scope": "MAYOR",
            "source_account_code": account_code,
            "source_row": source_row,
            "expected_value": None,
            "actual_value": None,
            "difference_value": None,
            "result_status": status,
            "detail_json": detail,
        }

    def _has_balance_gap(self, expected: Decimal, actual: Decimal) -> bool:
        return abs(expected - actual) > Decimal("0.01")
