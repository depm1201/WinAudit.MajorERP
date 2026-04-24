from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parser.major_excel_parser import MajorExcelParser


BASE = Path(r"C:\Users\david.palma\Onlysoft-WINAUDIT\WinAudit.Documents\04-COMPARATIVAS-TRIBUTARIAS-Y-ALCANCE-FASE1\Informacion-Soporte-Cliente")


def test_parse_ledger_workbook():
    parser = MajorExcelParser()
    parsed = parser.parse(BASE / "Mayor IVA sobre Compras.xlsx")
    assert parsed.report_type == "LEDGER"
    assert parsed.sheet_name == "Consulta Cuentas"
    assert parsed.fiscal_period == "2025-11"
    assert len(parsed.ledger_rows) > 0


def test_parse_plan_cuentas_workbook():
    parser = MajorExcelParser()
    parsed = parser.parse(BASE / "PlanCuentas.xlsx")
    assert parsed.report_type == "ACCOUNT_CATALOG"
    assert parsed.sheet_name == "PlanCuentas"
    assert len(parsed.account_rows) > 0

