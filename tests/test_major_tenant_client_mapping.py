from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.core.exceptions import ClientNotFoundError
from app.repositories.major_repository import MajorRepository
from app.services.major_import_service import MajorImportService


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, obj):
        self.added.append(obj)

    def add_all(self, objs):
        self.added.extend(objs)

    def flush(self):
        self.flushed += 1

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class MajorTenantClientMappingTests(TestCase):
    def test_repository_propagates_client_id_into_major_tables(self):
        repo = MajorRepository()
        session = FakeSession()

        catalog_count = repo.save_account_catalog_rows(
            session,
            client_id=99,
            import_batch_id=10,
            rows=[
                {
                    "account_code": "1.1.1",
                    "account_name": "Caja",
                    "source_file": "plan.xlsx",
                }
            ],
        )
        ledger_count = repo.save_main_ledger_rows(
            session,
            client_id=99,
            import_batch_id=11,
            fiscal_period="2025-11",
            rows=[
                {
                    "account_code": "1.1.1",
                    "account_name": "Caja",
                    "debit": 10,
                    "credit": 0,
                    "balance": 10,
                    "source_file": "mayor.xlsx",
                }
            ],
        )
        validation_count = repo.save_validation_results(
            session,
            client_id=99,
            import_batch_id=12,
            rows=[
                {
                    "validation_code": "OK",
                    "validation_name": "Prueba",
                    "validation_scope": "MAYOR",
                    "result_status": "PASS",
                }
            ],
        )
        mapping_count = repo.save_account_mappings(
            session,
            client_id=99,
            rows=[
                {
                    "retention_percentage": 30,
                    "target_account_code": "1.1.1",
                    "tax_type": "IVA",
                }
            ],
        )

        self.assertEqual(catalog_count, 1)
        self.assertEqual(ledger_count, 1)
        self.assertEqual(validation_count, 1)
        self.assertEqual(mapping_count, 1)
        self.assertEqual(session.flushed, 4)
        self.assertTrue(all(getattr(obj, "client_id", None) == 99 for obj in session.added))
        self.assertTrue(any(getattr(obj, "import_batch_id", None) == 10 for obj in session.added))
        self.assertTrue(any(getattr(obj, "import_batch_id", None) == 11 for obj in session.added))
        self.assertTrue(any(getattr(obj, "import_batch_id", None) == 12 for obj in session.added))

    def test_import_major_workbook_uses_tenant_and_client_to_persist_batch(self):
        service = MajorImportService()
        fake_session = FakeSession()
        fake_client = SimpleNamespace(id=77, ruc="0993198676001")
        created_batches = []
        persisted_rows = []

        class FakeRepo:
            def get_client_by_ruc(self, session, ruc):
                self.last_ruc = ruc
                return fake_client

            def create_import_batch(self, session, **payload):
                created_batches.append(payload)
                batch = SimpleNamespace(id=123, client_id=payload["client_id"], validation_status="PENDING", report_code=None)
                self.batch = batch
                return batch

            def update_import_batch(self, session, batch, **payload):
                batch.validation_status = payload.get("validation_status", batch.validation_status)
                batch.report_code = payload.get("report_code", batch.report_code)
                return batch

            def save_account_catalog_rows(self, session, client_id, import_batch_id, rows):
                persisted_rows.append(("catalog", client_id, import_batch_id, rows))
                return len(rows)

            def save_main_ledger_rows(self, session, client_id, import_batch_id, fiscal_period, rows):
                persisted_rows.append(("ledger", client_id, import_batch_id, fiscal_period, rows))
                return len(rows)

            def save_validation_results(self, session, client_id, import_batch_id, rows):
                persisted_rows.append(("validation", client_id, import_batch_id, rows))
                return len(rows)

        class FakeParser:
            def parse(self, parsed_file_path, fiscal_period_hint=None):
                return SimpleNamespace(
                    report_type="LEDGER",
                    report_name="Mayor",
                    sheet_name="Consulta Cuentas",
                    fiscal_period="2025-11",
                    row_count=1,
                    warnings=[],
                    account_rows=[],
                    ledger_rows=[
                        SimpleNamespace(
                            row_type="OPENING",
                            account_code="1.1.1",
                            account_name="Caja",
                            transaction_date=None,
                            description="Saldo inicial",
                            debit=None,
                            credit=None,
                            balance=0,
                            related_document=None,
                            cost_center=None,
                            project=None,
                            person_name=None,
                            cross_ref_person=None,
                            tax_category=None,
                            journal_entry=None,
                            tax_id=None,
                            source_sheet="Consulta Cuentas",
                            source_row=1,
                        )
                    ],
                    ledger_totals=lambda: (0, 0, 0),
                )

        class FakeValidator:
            def validate_batch(self, session, batch_id):
                return SimpleNamespace(batch_id=batch_id, validation_status="VALIDATED", issues=0, warnings=0, errors=0, message="OK")

        service._repo = FakeRepo()
        service._parser = FakeParser()
        service._validator = FakeValidator()
        service._storage = SimpleNamespace(
            ensure_paths=lambda tenant_code, ruc, fiscal_period: Path(r"C:/tmp/majorerp"),
        )
        service._resolve_tenant_code = lambda tenant_id: "Finanzburo"
        service._persist_raw_file = lambda **kwargs: Path(r"C:/tmp/majorerp/raw/mayor.xlsx")

        with patch("app.services.major_import_service.get_tenant_session", return_value=fake_session) as tenant_session_patch:
            result = service.import_major_workbook(
                tenant_id=2,
                client_ruc="0993198676001",
                file_name="Mayor.xlsx",
                file_bytes=b"fake-bytes",
                fiscal_period_hint="2025-11",
            )

        self.assertEqual(tenant_session_patch.call_count, 1)
        self.assertEqual(result.client_id, 77)
        self.assertEqual(result.tenant_id, 2)
        self.assertEqual(created_batches[0]["client_id"], 77)
        self.assertEqual(created_batches[0]["validation_status"], "PENDING")
        self.assertTrue(any(item[0] == "ledger" and item[1] == 77 for item in persisted_rows))
        self.assertTrue(all(row[1] == 77 for row in persisted_rows))

    def test_import_major_workbook_returns_error_when_client_is_missing(self):
        service = MajorImportService()
        fake_session = FakeSession()

        class FakeRepo:
            def get_client_by_ruc(self, session, ruc):
                return None

        service._repo = FakeRepo()
        service._parser = SimpleNamespace()
        service._validator = SimpleNamespace()
        service._storage = SimpleNamespace()
        service._resolve_tenant_code = lambda tenant_id: "Finanzburo"
        service._persist_raw_file = lambda **kwargs: Path(r"C:/tmp/majorerp/raw/mayor.xlsx")

        with patch("app.services.major_import_service.get_tenant_session", return_value=fake_session):
            result = service.import_major_workbook(
                tenant_id=2,
                client_ruc="0000000000000",
                file_name="Mayor.xlsx",
                file_bytes=b"fake-bytes",
                fiscal_period_hint="2025-11",
            )

        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.tenant_id, 2)
        self.assertIsNone(result.client_id)
        self.assertIn("No se encontro cliente", result.message)
