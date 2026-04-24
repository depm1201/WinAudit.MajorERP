from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.major_reconciliation_service import MajorReconciliationService


class FakeRepo:
    def __init__(self, batch, ledger_rows=None, catalog_rows=None, mapping_rows=None):
        self.batch = batch
        self.ledger_rows = ledger_rows or []
        self.catalog_rows = catalog_rows or []
        self.mapping_rows = mapping_rows or []
        self.saved_rows = []
        self.deleted_scope = None

    def get_import_batch(self, session, batch_id):
        return self.batch if self.batch and self.batch.id == batch_id else None

    def delete_validation_rows(self, session, import_batch_id, scope=None):
        self.deleted_scope = scope
        return 0

    def list_ledger_rows(self, session, batch_id):
        return self.ledger_rows

    def list_catalog_accounts(self, session, client_id):
        return self.catalog_rows

    def list_account_mappings(self, session, client_id):
        return self.mapping_rows

    def save_validation_results(self, session, client_id, import_batch_id, rows):
        self.saved_rows.extend(rows)
        return len(rows)


def test_reconcile_batch_classifies_catalog_mapping_and_missing_accounts():
    batch = SimpleNamespace(id=20, client_id=1, report_code="LEDGER")
    rows = [
        SimpleNamespace(id=1, account_code="1.1.1", source_row=1, balance=Decimal("0.00")),
        SimpleNamespace(id=2, account_code="1.1.2", source_row=2, balance=Decimal("0.00")),
        SimpleNamespace(id=3, account_code="1.1.3", source_row=3, balance=Decimal("0.00")),
        SimpleNamespace(id=4, account_code="9.9.9", source_row=4, balance=Decimal("0.00")),
    ]
    catalog_rows = [
        SimpleNamespace(account_code="1.1.1"),
        SimpleNamespace(account_code="1.1.2"),
    ]
    mapping_rows = [
        SimpleNamespace(target_account_code="1.1.1"),
        SimpleNamespace(target_account_code="1.1.3"),
    ]
    service = MajorReconciliationService()
    service._repo = FakeRepo(batch, ledger_rows=rows, catalog_rows=catalog_rows, mapping_rows=mapping_rows)

    summary = service.reconcile_batch(session=None, batch_id=20)

    assert summary.reconciliation_status == "RECONCILED_WITH_ERRORS"
    assert summary.total_accounts == 4
    assert summary.matched_accounts == 1
    assert summary.catalog_only_accounts == 1
    assert summary.mapping_only_accounts == 1
    assert summary.missing_accounts == 1
    assert summary.warnings == 2
    assert summary.errors == 1
    assert len(service._repo.saved_rows) == 4
    assert service._repo.deleted_scope == "RECONCILIATION"
    assert batch.report_code == "LEDGER"
