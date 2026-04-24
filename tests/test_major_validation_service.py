from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.major_validation_service import MajorValidationService


class FakeRepo:
    def __init__(self, batch, account_rows=None, ledger_rows=None, catalog_rows=None):
        self.batch = batch
        self.account_rows = account_rows or []
        self.ledger_rows = ledger_rows or []
        self.catalog_rows = catalog_rows or []
        self.saved_rows = []
        self.updated_batch = None
        self.deleted = None
        self.deleted_scope = None

    def get_import_batch(self, session, batch_id):
        return self.batch if self.batch and self.batch.id == batch_id else None

    def delete_validation_rows(self, session, import_batch_id, scope=None):
        self.deleted = import_batch_id
        self.deleted_scope = scope
        return 0

    def list_account_rows(self, session, batch_id):
        return self.account_rows

    def list_ledger_rows(self, session, batch_id):
        return self.ledger_rows

    def list_catalog_accounts(self, session, client_id):
        return self.catalog_rows

    def save_validation_results(self, session, client_id, import_batch_id, rows):
        self.saved_rows.extend(rows)
        return len(rows)

    def update_import_batch(self, session, batch, **payload):
        self.updated_batch = payload
        for key, value in payload.items():
            setattr(batch, key, value)
        return batch


def test_validate_account_catalog_detects_duplicate_and_orphan():
    batch = SimpleNamespace(id=10, client_id=1, report_code="ACCOUNT_CATALOG", validation_status="LOADED")
    rows = [
        SimpleNamespace(id=1, account_code="1.1.1", source_row=1, parent_account_code=None),
        SimpleNamespace(id=2, account_code="1.1.1", source_row=2, parent_account_code=None),
        SimpleNamespace(id=3, account_code="1.1.2", source_row=3, parent_account_code="9.9.9"),
    ]
    service = MajorValidationService()
    service._repo = FakeRepo(batch, account_rows=rows)

    summary = service.validate_batch(session=None, batch_id=10)

    assert summary.validation_status == "VALIDATED_WITH_ERRORS"
    assert summary.errors == 2
    assert summary.warnings == 0
    assert len(service._repo.saved_rows) == 2
    assert batch.validation_status == "VALIDATED_WITH_ERRORS"


def test_validate_ledger_detects_unknown_account_and_balance_gap():
    batch = SimpleNamespace(id=11, client_id=1, report_code="LEDGER", validation_status="LOADED")
    rows = [
        SimpleNamespace(id=1, account_code="1.1.1", source_row=1, row_type="OPENING", balance=Decimal("100.00"), debit=None, credit=None),
        SimpleNamespace(id=2, account_code="1.1.1", source_row=2, row_type="MOVEMENT", balance=Decimal("110.00"), debit=Decimal("5.00"), credit=Decimal("0.00")),
        SimpleNamespace(id=3, account_code="9.9.9", source_row=3, row_type="MOVEMENT", balance=Decimal("10.00"), debit=Decimal("10.00"), credit=Decimal("0.00")),
    ]
    catalog_rows = [SimpleNamespace(account_code="1.1.1")]
    service = MajorValidationService()
    service._repo = FakeRepo(batch, ledger_rows=rows, catalog_rows=catalog_rows)

    summary = service.validate_batch(session=None, batch_id=11)

    assert summary.validation_status == "VALIDATED_WITH_ERRORS"
    assert summary.errors == 2
    assert summary.warnings == 1
    assert len(service._repo.saved_rows) == 2
    assert batch.validation_status == "VALIDATED_WITH_ERRORS"
    assert service._repo.deleted_scope == "MAYOR"
