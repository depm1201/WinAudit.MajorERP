from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Iterable

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import (
    AccAccountCatalog,
    AccAccountMapping,
    AccImportBatch,
    AccMainLedger,
    AccValidationResult,
    AdmClient,
)


class MajorRepository:
    def get_client_by_ruc(self, session: Session, ruc: str) -> AdmClient | None:
        stmt: Select[tuple[AdmClient]] = select(AdmClient).where(AdmClient.ruc == str(ruc), AdmClient.status == 1)
        return session.execute(stmt).scalars().first()

    def get_client_by_id(self, session: Session, client_id: int) -> AdmClient | None:
        stmt: Select[tuple[AdmClient]] = select(AdmClient).where(AdmClient.id == client_id, AdmClient.status == 1)
        return session.execute(stmt).scalars().first()

    def create_import_batch(self, session: Session, **payload) -> AccImportBatch:
        batch = AccImportBatch(**payload)
        session.add(batch)
        session.flush()
        return batch

    def update_import_batch(self, session: Session, batch: AccImportBatch, **payload) -> AccImportBatch:
        for key, value in payload.items():
            setattr(batch, key, value)
        session.add(batch)
        session.flush()
        return batch

    def get_import_batch(self, session: Session, batch_id: int) -> AccImportBatch | None:
        return session.get(AccImportBatch, batch_id)

    def list_account_rows(self, session: Session, import_batch_id: int) -> list[AccAccountCatalog]:
        stmt = select(AccAccountCatalog).where(AccAccountCatalog.import_batch_id == import_batch_id).order_by(AccAccountCatalog.source_row, AccAccountCatalog.id)
        return list(session.execute(stmt).scalars().all())

    def list_catalog_accounts(self, session: Session, client_id: int) -> list[AccAccountCatalog]:
        latest_batch_id = self.get_latest_catalog_batch_id(session, client_id)
        if latest_batch_id is None:
            return []
        stmt = (
            select(AccAccountCatalog)
            .where(
                AccAccountCatalog.client_id == client_id,
                AccAccountCatalog.import_batch_id == latest_batch_id,
            )
            .order_by(AccAccountCatalog.account_code)
        )
        return list(session.execute(stmt).scalars().all())

    def get_catalog_account(self, session: Session, client_id: int, account_code: str) -> AccAccountCatalog | None:
        latest_batch_id = self.get_latest_catalog_batch_id(session, client_id)
        if latest_batch_id is None:
            return None
        stmt = select(AccAccountCatalog).where(
            AccAccountCatalog.client_id == client_id,
            AccAccountCatalog.import_batch_id == latest_batch_id,
            AccAccountCatalog.account_code == account_code,
        )
        return session.execute(stmt).scalars().first()

    def get_latest_catalog_batch_id(self, session: Session, client_id: int) -> int | None:
        stmt = (
            select(AccImportBatch.id)
            .where(
                AccImportBatch.client_id == client_id,
                AccImportBatch.batch_type == "MAYOR_CONTIFICO",
                AccImportBatch.report_code == "ACCOUNT_CATALOG",
            )
            .order_by(AccImportBatch.id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalars().first()

    def list_account_mappings(self, session: Session, client_id: int) -> list[AccAccountMapping]:
        stmt = (
            select(AccAccountMapping)
            .where(AccAccountMapping.client_id == client_id, AccAccountMapping.status == 1)
            .order_by(AccAccountMapping.retention_percentage.nulls_last(), AccAccountMapping.id)
        )
        return list(session.execute(stmt).scalars().all())

    def get_account_mapping(self, session: Session, client_id: int, tax_type: str | None = None, retention_percentage: Decimal | None = None) -> AccAccountMapping | None:
        stmt = select(AccAccountMapping).where(
            AccAccountMapping.client_id == client_id,
            AccAccountMapping.status == 1,
        )
        if tax_type:
            stmt = stmt.where(AccAccountMapping.tax_type == tax_type)
        if retention_percentage is not None:
            stmt = stmt.where(AccAccountMapping.retention_percentage == retention_percentage)
        stmt = stmt.order_by(AccAccountMapping.id.desc()).limit(1)
        return session.execute(stmt).scalars().first()

    def get_account_mapping_by_target_code(self, session: Session, client_id: int, target_account_code: str) -> AccAccountMapping | None:
        stmt = (
            select(AccAccountMapping)
            .where(
                AccAccountMapping.client_id == client_id,
                AccAccountMapping.status == 1,
                AccAccountMapping.target_account_code == target_account_code,
            )
            .order_by(AccAccountMapping.id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalars().first()

    def list_ledger_rows(self, session: Session, import_batch_id: int) -> list[AccMainLedger]:
        stmt = select(AccMainLedger).where(AccMainLedger.import_batch_id == import_batch_id).order_by(AccMainLedger.source_row, AccMainLedger.id)
        return list(session.execute(stmt).scalars().all())

    def list_validation_rows(self, session: Session, import_batch_id: int, scope: str | None = None) -> list[AccValidationResult]:
        stmt = select(AccValidationResult).where(AccValidationResult.import_batch_id == import_batch_id)
        if scope:
            stmt = stmt.where(AccValidationResult.validation_scope == scope)
        stmt = stmt.order_by(AccValidationResult.source_row, AccValidationResult.id)
        return list(session.execute(stmt).scalars().all())

    def delete_validation_rows(self, session: Session, import_batch_id: int, scope: str | None = None) -> int:
        stmt = AccValidationResult.__table__.delete().where(AccValidationResult.import_batch_id == import_batch_id)
        if scope:
            stmt = stmt.where(AccValidationResult.validation_scope == scope)
        result = session.execute(stmt)
        session.flush()
        return int(result.rowcount or 0)

    def clear_account_mappings(self, session: Session, client_id: int) -> int:
        stmt = AccAccountMapping.__table__.delete().where(AccAccountMapping.client_id == client_id)
        result = session.execute(stmt)
        session.flush()
        return int(result.rowcount or 0)

    def save_account_catalog_rows(
        self,
        session: Session,
        client_id: int,
        import_batch_id: int,
        rows: Iterable[dict],
    ) -> int:
        items = []
        for row in rows:
            items.append(
                AccAccountCatalog(
                    client_id=client_id,
                    import_batch_id=import_batch_id,
                    account_code=row["account_code"],
                    account_name=row["account_name"],
                    parent_account_code=row.get("parent_account_code"),
                    account_level=row.get("account_level"),
                    account_path=row.get("account_path"),
                    sort_order=row.get("sort_order"),
                    source_sheet=row.get("source_sheet"),
                    source_row=row.get("source_row"),
                    is_group=bool(row.get("is_group", False)),
                    source_file=row.get("source_file"),
                    tax_category=row.get("tax_category"),
                    tax_type=row.get("tax_type"),
                )
            )
        session.add_all(items)
        session.flush()
        return len(items)

    def save_main_ledger_rows(
        self,
        session: Session,
        client_id: int,
        import_batch_id: int,
        fiscal_period: str | None,
        rows: Iterable[dict],
    ) -> int:
        items = []
        for row in rows:
            items.append(
                AccMainLedger(
                    client_id=client_id,
                    import_batch_id=import_batch_id,
                    fiscal_period=fiscal_period,
                    account_code=row["account_code"],
                    account_name=row.get("account_name"),
                    transaction_date=row.get("transaction_date"),
                    description=row.get("description"),
                    debit=row.get("debit"),
                    credit=row.get("credit"),
                    balance=row.get("balance"),
                    related_document=row.get("related_document"),
                    cost_center=row.get("cost_center"),
                    project=row.get("project"),
                    person_name=row.get("person_name"),
                    cross_ref_person=row.get("cross_ref_person"),
                    tax_category=row.get("tax_category"),
                    journal_entry=row.get("journal_entry"),
                    tax_id=row.get("tax_id"),
                    source_file=row.get("source_file"),
                    row_type=row.get("row_type", "MOVEMENT"),
                    source_sheet=row.get("source_sheet"),
                    source_row=row.get("source_row"),
                )
            )
        session.add_all(items)
        session.flush()
        return len(items)

    def save_validation_results(
        self,
        session: Session,
        client_id: int,
        import_batch_id: int | None,
        rows: Iterable[dict],
    ) -> int:
        items = []
        for row in rows:
            items.append(
                AccValidationResult(
                    client_id=client_id,
                    import_batch_id=import_batch_id,
                    validation_code=row["validation_code"],
                    validation_name=row.get("validation_name"),
                    validation_scope=row.get("validation_scope", "MAYOR"),
                    source_account_code=row.get("source_account_code"),
                    source_row=row.get("source_row"),
                    expected_value=row.get("expected_value"),
                    actual_value=row.get("actual_value"),
                    difference_value=row.get("difference_value"),
                    result_status=row.get("result_status", "PASS"),
                    detail_json=row.get("detail_json"),
                )
            )
        session.add_all(items)
        session.flush()
        return len(items)

    def save_account_mappings(self, session: Session, client_id: int, rows: Iterable[dict]) -> int:
        items = []
        for row in rows:
            items.append(
                AccAccountMapping(
                    client_id=client_id,
                    retention_percentage=row.get("retention_percentage"),
                    target_account_code=row.get("target_account_code"),
                    tax_type=row.get("tax_type"),
                    status=row.get("status", 1),
                )
            )
        if not items:
            return 0
        session.add_all(items)
        session.flush()
        return len(items)
