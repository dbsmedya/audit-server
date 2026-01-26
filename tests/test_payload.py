"""Tests for payload module."""

import pytest

from server_audit.payload import build_payload, get_markers


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_returns_string(self):
        """Payload should return a string."""
        payload = build_payload()
        assert isinstance(payload, str)

    def test_contains_all_markers(self):
        """Payload should contain all section markers."""
        payload = build_payload()
        markers = get_markers()

        for section, (start, end) in markers.items():
            assert start in payload, f"Missing start marker for {section}"
            assert end in payload, f"Missing end marker for {section}"

    def test_sets_locale(self):
        """Payload should set LC_ALL=C for consistent output."""
        payload = build_payload()
        assert "LC_ALL=C" in payload

    def test_collects_os_info(self):
        """Payload should collect OS information."""
        payload = build_payload()
        assert "/etc/os-release" in payload
        assert "/etc/lsb-release" in payload

    def test_collects_kernel_version(self):
        """Payload should collect kernel version."""
        payload = build_payload()
        assert "uname -r" in payload

    def test_collects_memory_info(self):
        """Payload should collect memory information."""
        payload = build_payload()
        assert "/proc/meminfo" in payload

    def test_collects_cpu_info(self):
        """Payload should collect CPU information with fallback."""
        payload = build_payload()
        assert "lscpu" in payload
        assert "/proc/cpuinfo" in payload

    def test_collects_disk_type(self):
        """Payload should check disk rotational status."""
        payload = build_payload()
        assert "rotational" in payload

    def test_collects_df_output(self):
        """Payload should collect disk space information."""
        payload = build_payload()
        assert "df" in payload

    def test_collects_network_info(self):
        """Payload should collect network information with fallback."""
        payload = build_payload()
        assert "ip addr" in payload
        assert "ifconfig" in payload

    def test_collects_vm_settings(self):
        """Payload should collect VM settings."""
        payload = build_payload()
        assert "swappiness" in payload
        assert "overcommit_memory" in payload
        assert "dirty_ratio" in payload
        assert "transparent_hugepage" in payload


class TestGetMarkers:
    """Tests for get_markers function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        markers = get_markers()
        assert isinstance(markers, dict)

    def test_all_sections_present(self):
        """Should have all expected sections."""
        markers = get_markers()
        expected = {"os", "kernel", "memory", "cpu", "disk_type", "df", "network", "vm", "numa"}
        assert set(markers.keys()) == expected

    def test_marker_format(self):
        """Each marker should be a tuple of (start, end)."""
        markers = get_markers()
        for section, pair in markers.items():
            assert isinstance(pair, tuple), f"{section} should be tuple"
            assert len(pair) == 2, f"{section} should have 2 elements"
            assert "START" in pair[0], f"{section} start marker invalid"
            assert "END" in pair[1], f"{section} end marker invalid"
