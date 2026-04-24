class MajorERPError(Exception):
    """Base exception for the major service."""


class ValidationError(MajorERPError):
    """Raised when a workbook or row fails validation."""


class StorageError(MajorERPError):
    """Raised when file persistence fails."""


class TenantNotFoundError(MajorERPError):
    """Raised when the tenant cannot be resolved from admin DB."""


class ClientNotFoundError(MajorERPError):
    """Raised when the client cannot be resolved for the provided RUC."""

