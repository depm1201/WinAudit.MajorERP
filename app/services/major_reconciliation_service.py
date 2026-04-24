from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from operator import attrgetter

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.major_repository import MajorRepository


@dataclass
class MajorReconciliationSummary:
    batch_id: int
    reconciliation_status: str
    total_accounts: int
    matched_accounts: int
    catalog_only_accounts: int
    mapping_only_accounts: int
    missing_accounts: int
    warnings: int
    errors: int
    message: str


class MajorReconciliationService:
    def __init__(self) -> None:
        self._repo = MajorRepository()

    def reconcile_batch(self, session: Session, batch_id: int) -> MajorReconciliationSummary:
        batch = self._repo.get_import_batch(session, batch_id)
        if not batch:
            raise ValidationError("Batch no encontrado.")
        if batch.report_code != "LEDGER":
            raise ValidationError("La conciliacion solo aplica a lotes de mayor contable.")

        self._repo.delete_validation_rows(session, batch_id, scope="RECONCILIATION")

        ledger_rows = self._repo.list_ledger_rows(session, batch.id)
        catalog_rows = self._repo.list_catalog_accounts(session, batch.client_id)
        mappings = self._repo.list_account_mappings(session, batch.client_id)
        if not ledger_rows:
            raise ValidationError("El batch no contiene filas de mayor para conciliar.")

        catalog_codes = {row.account_code for row in catalog_rows}
        mapping_codes = {row.target_account_code for row in mappings if row.target_account_code}

        issues: list[dict] = []
        matched_accounts = 0
        catalog_only_accounts = 0
        mapping_only_accounts = 0
        missing_accounts = 0

        ordered_rows = sorted(ledger_rows, key=lambda item: (item.account_code, item.source_row or 0, item.id))
        for account_code, account_rows_iter in groupby(ordered_rows, key=attrgetter("account_code")):
            account_rows = list(account_rows_iter)
            first_row = account_rows[0]
            catalog_hit = account_code in catalog_codes
            mapping_hit = account_code in mapping_codes

            if catalog_hit and mapping_hit:
                matched_accounts += 1
                result_status = "PASS"
                validation_code = "ACCOUNT_RECONCILED"
                validation_name = "Cuenta conciliada"
            elif catalog_hit:
                catalog_only_accounts += 1
                result_status = "WARN"
                validation_code = "CATALOG_WITHOUT_MAPPING"
                validation_name = "Cuenta en catalogo sin mapeo"
            elif mapping_hit:
                mapping_only_accounts += 1
                result_status = "WARN"
                validation_code = "MAPPING_WITHOUT_CATALOG"
                validation_name = "Mapeo sin cuenta en catalogo"
            else:
                missing_accounts += 1
                result_status = "ERROR"
                validation_code = "UNMAPPED_ACCOUNT"
                validation_name = "Cuenta sin catalogo ni mapeo"

            issues.append(
                self._issue(
                    code=validation_code,
                    name=validation_name,
                    status=result_status,
                    source_row=first_row.source_row,
                    account_code=account_code,
                    expected_value=Decimal("1") if catalog_hit else Decimal("0"),
                    actual_value=Decimal("1") if mapping_hit else Decimal("0"),
                    detail={
                        "account_code": account_code,
                        "catalog_hit": catalog_hit,
                        "mapping_hit": mapping_hit,
                        "row_count": len(account_rows),
                    },
                )
            )

        if issues:
            self._repo.save_validation_results(session, batch.client_id, batch.id, issues)

        warnings = catalog_only_accounts + mapping_only_accounts
        errors = missing_accounts
        if errors:
            reconciliation_status = "RECONCILED_WITH_ERRORS"
            message = f"Conciliacion finalizada con {errors} errores y {warnings} advertencias."
        elif warnings:
            reconciliation_status = "RECONCILED_WITH_WARNINGS"
            message = f"Conciliacion finalizada con {warnings} advertencias."
        else:
            reconciliation_status = "RECONCILED"
            message = "Conciliacion completada sin observaciones."

        return MajorReconciliationSummary(
            batch_id=batch.id,
            reconciliation_status=reconciliation_status,
            total_accounts=len(issues),
            matched_accounts=matched_accounts,
            catalog_only_accounts=catalog_only_accounts,
            mapping_only_accounts=mapping_only_accounts,
            missing_accounts=missing_accounts,
            warnings=warnings,
            errors=errors,
            message=message,
        )

    def _issue(
        self,
        *,
        code: str,
        name: str,
        status: str,
        source_row: int | None,
        account_code: str | None,
        expected_value: Decimal | None,
        actual_value: Decimal | None,
        detail: dict,
    ) -> dict:
        difference_value = None
        if expected_value is not None and actual_value is not None:
            difference_value = actual_value - expected_value
        return {
            "validation_code": code,
            "validation_name": name,
            "validation_scope": "RECONCILIATION",
            "source_account_code": account_code,
            "source_row": source_row,
            "expected_value": expected_value,
            "actual_value": actual_value,
            "difference_value": difference_value,
            "result_status": status,
            "detail_json": detail,
        }
