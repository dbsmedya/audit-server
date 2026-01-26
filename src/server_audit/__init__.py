"""
Server Audit - Linux server information collection tool.

A Python tool for collecting operating system and hardware information
from Linux distributions using ansible_runner in Ad-Hoc mode.
"""

__version__ = "0.1.0"

from server_audit.exceptions import (
    AuditError,
    ConnectionError,
    ParseError,
    PayloadError,
)
from server_audit.models import AuditResult, DiskInfo, NetworkInfo
from server_audit.runner import run_audit

__all__ = [
    "__version__",
    "AuditError",
    "ConnectionError",
    "ParseError",
    "PayloadError",
    "AuditResult",
    "DiskInfo",
    "NetworkInfo",
    "run_audit",
]
