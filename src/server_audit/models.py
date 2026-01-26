"""
Data models for audit results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DiskInfo:
    """Information about a mounted filesystem."""

    mount: str
    device: str
    size_total: int
    size_available: int
    fstype: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mount": self.mount,
            "device": self.device,
            "size_total": self.size_total,
            "size_available": self.size_available,
            "fstype": self.fstype,
        }


@dataclass
class NetworkInfo:
    """Information about a network interface."""

    ipv4: str | None
    mac: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ipv4": self.ipv4,
            "mac": self.mac,
        }


@dataclass
class OSInfo:
    """Operating system information."""

    distribution: str
    version: str
    kernel: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "distribution": self.distribution,
            "version": self.version,
            "kernel": self.kernel,
        }


@dataclass
class HardwareInfo:
    """Hardware information."""

    memory_total: str
    cpu_count: int
    cpu_model: str
    disk_types: dict[str, str]
    numa: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "memory_total": self.memory_total,
            "cpu_count": self.cpu_count,
            "cpu_model": self.cpu_model,
            "disk_types": self.disk_types,
            "numa": self.numa,
        }


@dataclass
class VMSettings:
    """Virtual memory settings."""

    swappiness: str
    overcommit_memory: str
    dirty_ratio: str
    dirty_background_ratio: str
    transparent_hugepages: str
    huge_pages_raw: list[str]
    semaphores: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swappiness": self.swappiness,
            "overcommit_memory": self.overcommit_memory,
            "dirty_ratio": self.dirty_ratio,
            "dirty_background_ratio": self.dirty_background_ratio,
            "transparent_hugepages": self.transparent_hugepages,
            "huge_pages_raw": self.huge_pages_raw,
            "semaphores": self.semaphores,
        }


@dataclass
class AuditResult:
    """Complete audit result for a single host."""

    hostname: str
    os_info: OSInfo
    hardware: HardwareInfo
    disks: list[DiskInfo]
    networks: dict[str, NetworkInfo]
    vm_settings: VMSettings
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "os_info": self.os_info.to_dict(),
            "hardware": self.hardware.to_dict(),
            "disks": [disk.to_dict() for disk in self.disks],
            "networks": {name: info.to_dict() for name, info in self.networks.items()},
            "vm_settings": self.vm_settings.to_dict(),
            "hostname": self.hostname,
            "audit_timestamp": self.audit_timestamp.isoformat(),
        }
