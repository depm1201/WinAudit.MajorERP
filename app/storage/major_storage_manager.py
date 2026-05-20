from pathlib import Path
from app.core.config import settings

class MajorStorageManager:
    def __init__(self) -> None:
        self.base_path = settings.storage_path
        self._ensure_base_path()

    def _ensure_base_path(self) -> None:
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def ensure_paths(self, tenant_code: str, ruc: str, fiscal_period: str) -> Path:
        """
        Garantiza que existan las rutas para un cliente y periodo específico.
        Retorna la ruta base para ese contexto (donde colgarán 'raw' y 'exports').
        """
        # Limpiar posibles caracteres inválidos en periodos (ej: '2024-01' -> '202401')
        clean_period = fiscal_period.replace("-", "").replace("/", "")
        path = self.base_path / tenant_code / ruc / clean_period
        path.mkdir(parents=True, exist_ok=True)
        return path

    def build_export_path(self, tenant_code: str, ruc: str, fiscal_period: str) -> Path:
        """
        Garantiza que exista la ruta de exportación y la retorna.
        """
        base = self.ensure_paths(tenant_code, ruc, fiscal_period)
        export_path = base / "exports"
        export_path.mkdir(parents=True, exist_ok=True)
        return export_path
