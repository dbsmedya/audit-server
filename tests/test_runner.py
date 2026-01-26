"""Tests for runner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server_audit.exceptions import ConnectionError, PayloadError
from server_audit.runner import get_host_list, run_audit, run_audit_to_json


class TestRunAudit:
    """Tests for run_audit function."""

    def test_raises_on_missing_inventory(self, tmp_path: Path):
        """Should raise FileNotFoundError for missing inventory."""
        missing_path = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            run_audit(missing_path)

    @patch("server_audit.runner.ansible_runner.run")
    def test_handles_successful_run(self, mock_run, sample_inventory: Path, sample_output: str):
        """Should return parsed results on success."""
        mock_result = MagicMock()
        mock_result.events = [
            {
                "event": "runner_on_ok",
                "event_data": {
                    "host": "testhost",
                    "res": {"stdout": sample_output},
                },
            }
        ]
        mock_run.return_value = mock_result

        results = run_audit(sample_inventory)

        assert "testhost" in results
        assert results["testhost"].hostname == "testhost"

    @patch("server_audit.runner.ansible_runner.run")
    def test_raises_on_unreachable(self, mock_run, sample_inventory: Path):
        """Should raise ConnectionError when host is unreachable."""
        mock_result = MagicMock()
        mock_result.events = [
            {
                "event": "runner_on_unreachable",
                "event_data": {
                    "host": "badhost",
                    "res": {"msg": "Connection refused"},
                },
            }
        ]
        mock_run.return_value = mock_result

        with pytest.raises(ConnectionError) as exc:
            run_audit(sample_inventory)
        assert "badhost" in str(exc.value)

    @patch("server_audit.runner.ansible_runner.run")
    def test_raises_on_failed(self, mock_run, sample_inventory: Path):
        """Should raise PayloadError when command fails."""
        mock_result = MagicMock()
        mock_result.events = [
            {
                "event": "runner_on_failed",
                "event_data": {
                    "host": "failhost",
                    "res": {"msg": "Command not found"},
                },
            }
        ]
        mock_run.return_value = mock_result

        with pytest.raises(PayloadError):
            run_audit(sample_inventory)


class TestRunAuditToJson:
    """Tests for run_audit_to_json function."""

    @patch("server_audit.runner.run_audit")
    def test_writes_individual_files(self, mock_audit, tmp_path: Path, sample_inventory: Path):
        """Should write per-host JSON files to directory."""
        from server_audit.models import (
            AuditResult,
            DiskInfo,
            HardwareInfo,
            NetworkInfo,
            OSInfo,
            VMSettings,
        )

        mock_result = AuditResult(
            hostname="host1",
            os_info=OSInfo("Ubuntu", "22.04", "5.15.0"),
            hardware=HardwareInfo("16 GB", 4, "Intel", {}, {}),
            disks=[],
            networks={},
            vm_settings=VMSettings("60", "0", "20", "10", "madvise", [], {}),
        )
        mock_audit.return_value = {"host1": mock_result}

        output_dir = tmp_path / "output"
        files = run_audit_to_json(sample_inventory, output_dir)

        assert len(files) == 1
        assert files[0].name == "audit_host1.json"
        assert files[0].exists()

    @patch("server_audit.runner.run_audit")
    def test_writes_combined_file(self, mock_audit, tmp_path: Path, sample_inventory: Path):
        """Should write combined JSON when output is .json file."""
        from server_audit.models import (
            AuditResult,
            DiskInfo,
            HardwareInfo,
            NetworkInfo,
            OSInfo,
            VMSettings,
        )

        mock_result = AuditResult(
            hostname="host1",
            os_info=OSInfo("Ubuntu", "22.04", "5.15.0"),
            hardware=HardwareInfo("16 GB", 4, "Intel", {}, {}),
            disks=[],
            networks={},
            vm_settings=VMSettings("60", "0", "20", "10", "madvise", [], {}),
        )
        mock_audit.return_value = {"host1": mock_result}

        output_file = tmp_path / "results.json"
        files = run_audit_to_json(sample_inventory, output_file)

        assert len(files) == 1
        assert files[0] == output_file
        assert output_file.exists()


class TestGetHostList:
    """Tests for get_host_list function."""

    def test_raises_on_missing_inventory(self, tmp_path: Path):
        """Should raise FileNotFoundError for missing inventory."""
        missing_path = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            get_host_list(missing_path)
