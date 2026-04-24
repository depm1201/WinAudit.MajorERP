from sqlalchemy import Boolean, Column, Date, DateTime, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AdmTenant(Base):
    __tablename__ = "adm_Tenant"

    Id = Column("Id", Integer, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=True)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)


class AdmClient(Base):
    __tablename__ = "adm_Client"

    id = Column(Integer, primary_key=True)
    holding_id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    ruc = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=True, default=True)
    is_real_estate = Column(Boolean, nullable=False, default=False)
    notification_email = Column(String, nullable=True)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)


class AccImportBatch(Base):
    __tablename__ = "acc_ImportBatch"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=False)
    batch_type = Column(String(30), nullable=False)
    source_system = Column(String(30), nullable=False, default="CONTIFICO")
    report_code = Column(String(50), nullable=True)
    report_name = Column(String(200), nullable=True)
    fiscal_period = Column(String(7), nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    original_file_name = Column(String(255), nullable=False)
    stored_file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    sheet_name = Column(String(100), nullable=True)
    row_count = Column(Integer, nullable=False, default=0)
    debit_total = Column(Numeric(18, 2), nullable=False, default=0)
    credit_total = Column(Numeric(18, 2), nullable=False, default=0)
    balance_total = Column(Numeric(18, 2), nullable=False, default=0)
    validation_status = Column(String(50), nullable=False, default="PENDING")
    validation_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    status = Column(Integer, nullable=False, default=1)


class AccAccountCatalog(Base):
    __tablename__ = "acc_AccountCatalog"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=False)
    account_code = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    tax_category = Column(String(255), nullable=True)
    tax_type = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    parent_account_code = Column(String, nullable=True)
    account_level = Column(Integer, nullable=True)
    account_path = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=True)
    import_batch_id = Column(Integer, nullable=True)
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    is_group = Column(Boolean, nullable=False, default=False)
    source_file = Column(String(255), nullable=True)


class AccMainLedger(Base):
    __tablename__ = "acc_MainLedger"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=True)
    fiscal_period = Column(String(7), nullable=True)
    account_code = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    debit = Column(Numeric(18, 2), nullable=True)
    credit = Column(Numeric(18, 2), nullable=True)
    balance = Column(Numeric(18, 2), nullable=True)
    related_document = Column(String, nullable=True)
    cost_center = Column(String, nullable=True)
    project = Column(String, nullable=True)
    person_name = Column(String, nullable=True)
    cross_ref_person = Column(String, nullable=True)
    tax_category = Column(String(255), nullable=True)
    import_batch_id = Column(Integer, nullable=True)
    journal_entry = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    source_file = Column(String, nullable=True)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    row_type = Column(String(20), nullable=False, default="MOVEMENT")
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)


class AccAccountMapping(Base):
    __tablename__ = "acc_AccountMapping"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=False)
    retention_percentage = Column(Numeric(18, 2), nullable=True)
    target_account_code = Column(String(50), nullable=True)
    tax_type = Column(String(20), nullable=True)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)


class AccValidationResult(Base):
    __tablename__ = "acc_ValidationResult"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=False)
    import_batch_id = Column(Integer, nullable=True)
    validation_code = Column(String(50), nullable=False)
    validation_name = Column(String(200), nullable=True)
    validation_scope = Column(String(30), nullable=False, default="MAYOR")
    source_account_code = Column(String(20), nullable=True)
    source_row = Column(Integer, nullable=True)
    expected_value = Column(Numeric(18, 2), nullable=True)
    actual_value = Column(Numeric(18, 2), nullable=True)
    difference_value = Column(Numeric(18, 2), nullable=True)
    result_status = Column(String(20), nullable=False)
    detail_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    status = Column(Integer, nullable=False, default=1)
