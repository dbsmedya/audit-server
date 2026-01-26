"""
Custom exceptions for the server audit tool.
"""


class AuditError(Exception):
    """Base exception for all audit-related errors."""

    def __init__(self, message: str, host: str | None = None):
        self.host = host
        super().__init__(message)

    def __str__(self) -> str:
        if self.host:
            return f"[{self.host}] {super().__str__()}"
        return super().__str__()


class ConnectionError(AuditError):
    """Raised when connection to a host fails."""

    pass


class PayloadError(AuditError):
    """Raised when payload execution fails on the remote host."""

    pass


class ParseError(AuditError):
    """Raised when parsing of audit output fails."""

    def __init__(self, message: str, section: str | None = None, host: str | None = None):
        self.section = section
        super().__init__(message, host)

    def __str__(self) -> str:
        base = super().__str__()
        if self.section:
            return f"{base} (section: {self.section})"
        return base


class InventoryError(AuditError):
    """Raised when inventory file is invalid or not found."""

    pass
