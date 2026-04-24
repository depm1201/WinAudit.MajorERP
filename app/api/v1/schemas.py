from pydantic import BaseModel, Field


class MajorImportResponse(BaseModel):
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


class MajorBatchResponse(BaseModel):
    id: int
    client_id: int
    batch_type: str
    source_system: str
    report_code: str | None = None
    report_name: str | None = None
    fiscal_period: str | None = None
    sheet_name: str | None = None
    row_count: int = 0
    debit_total: float = 0
    credit_total: float = 0
    balance_total: float = 0
    validation_status: str
    validation_message: str | None = None
    stored_file_path: str
    original_file_name: str


class MajorEntryResponse(BaseModel):
    id: int
    source_row: int | None = None
    account_code: str
    account_name: str | None = None
    row_type: str | None = None
    transaction_date: str | None = None
    description: str | None = None
    debit: float | None = None
    credit: float | None = None
    balance: float | None = None
    related_document: str | None = None
    cost_center: str | None = None
    project: str | None = None
    person_name: str | None = None
    cross_ref_person: str | None = None
    validation_status: str | None = None


class MajorValidationResponse(BaseModel):
    id: int
    validation_code: str
    validation_name: str | None = None
    validation_scope: str
    source_account_code: str | None = None
    source_row: int | None = None
    expected_value: float | None = None
    actual_value: float | None = None
    difference_value: float | None = None
    result_status: str
    detail_json: dict | None = None


class MajorValidationRunResponse(BaseModel):
    batch_id: int
    validation_status: str
    issues: int
    warnings: int
    errors: int
    message: str


class MajorReconciliationRunResponse(BaseModel):
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


class MajorMappingResponse(BaseModel):
    id: int
    retention_percentage: float | None = None
    target_account_code: str | None = None
    tax_type: str | None = None
    status: int


class MajorMappingSyncResponse(BaseModel):
    client_id: int
    source: str
    created: int
    message: str
