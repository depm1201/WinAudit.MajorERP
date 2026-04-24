from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.major_repository import MajorRepository


@dataclass
class MajorMappingSyncSummary:
    client_id: int
    source: str
    created: int
    message: str


class MajorMappingService:
    def __init__(self) -> None:
        self._repo = MajorRepository()

    def sync_from_latest_catalog(self, session: Session, client_id: int) -> MajorMappingSyncSummary:
        catalog_rows = self._repo.list_catalog_accounts(session, client_id)
        if not catalog_rows:
            raise ValidationError("No existe catalogo vigente para generar mapeos.")

        payload = self._build_mappings_from_catalog(catalog_rows)
        self._repo.clear_account_mappings(session, client_id)
        created = self._repo.save_account_mappings(session, client_id, payload)
        return MajorMappingSyncSummary(
            client_id=client_id,
            source="CATALOG",
            created=created,
            message=f"Se generaron {created} mapeos desde el catalogo vigente.",
        )

    def sync_from_batch(self, session: Session, batch_id: int) -> MajorMappingSyncSummary:
        batch = self._repo.get_import_batch(session, batch_id)
        if not batch:
            raise ValidationError("Batch no encontrado.")

        ledger_rows = self._repo.list_ledger_rows(session, batch_id)
        if not ledger_rows:
            raise ValidationError("El batch no contiene filas de mayor para generar mapeos.")

        payload = self._build_mappings_from_ledger(ledger_rows)
        self._repo.clear_account_mappings(session, batch.client_id)
        created = self._repo.save_account_mappings(session, batch.client_id, payload)
        return MajorMappingSyncSummary(
            client_id=batch.client_id,
            source=f"BATCH:{batch_id}",
            created=created,
            message=f"Se generaron {created} mapeos desde el batch {batch_id}.",
        )

    def _build_mappings_from_catalog(self, rows) -> list[dict]:
        mappings: list[dict] = []
        for row in rows:
            retention_percentage = self._extract_percentage(row.account_name)
            tax_type = self._infer_tax_type(row.account_code, row.account_name, row.source_sheet, row.account_path)
            if retention_percentage is None and tax_type is None:
                continue
            mappings.append(
                {
                    "retention_percentage": retention_percentage,
                    "target_account_code": row.account_code,
                    "tax_type": tax_type,
                    "status": 1,
                }
            )
        return self._dedupe_mappings(mappings)

    def _build_mappings_from_ledger(self, rows) -> list[dict]:
        mappings: list[dict] = []
        seen: set[tuple[str | None, str | None, Decimal | None]] = set()
        for row in rows:
            text = " ".join(part for part in [row.account_name, row.description, row.related_document, row.project] if part)
            retention_percentage = self._extract_percentage(text)
            tax_type = self._infer_tax_type(row.account_code, row.account_name, text, None)
            if retention_percentage is None and tax_type is None:
                continue
            key = (row.account_code, tax_type, retention_percentage)
            if key in seen:
                continue
            seen.add(key)
            mappings.append(
                {
                    "retention_percentage": retention_percentage,
                    "target_account_code": row.account_code,
                    "tax_type": tax_type,
                    "status": 1,
                }
            )
        return mappings

    def _extract_percentage(self, text: str | None) -> Decimal | None:
        if not text:
            return None
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
        if not match:
            return None
        return Decimal(match.group(1).replace(",", "."))

    def _infer_tax_type(self, account_code: str | None, account_name: str | None, *fragments: str | None) -> str | None:
        haystack = " ".join(part for part in (account_code, account_name, *fragments) if part).upper()
        if "IVA" in haystack:
            return "IVA"
        if "RENTA" in haystack or "IR" in haystack:
            return "IR"
        return None

    def _dedupe_mappings(self, rows: list[dict]) -> list[dict]:
        deduped: dict[tuple[str | None, str | None, Decimal | None], dict] = {}
        for row in rows:
            key = (row.get("target_account_code"), row.get("tax_type"), row.get("retention_percentage"))
            deduped[key] = row
        return list(deduped.values())
