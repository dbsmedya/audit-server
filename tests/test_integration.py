"""Integration tests for server_audit.

These tests require Docker containers to be running.
Run with: docker-compose -f docker/docker-compose.yml up -d
"""

import json
from pathlib import Path

import pytest

# Skip all tests in this module if Docker containers are not available
pytestmark = pytest.mark.skipif(
    False,  # Set to False when running with Docker
    reason="Docker containers not available. Run: docker-compose up -d",
)


class TestIntegration:
    """Integration tests against Docker containers."""

    @pytest.fixture
    def docker_inventory(self, tmp_path: Path) -> Path:
        """Create inventory for Docker test containers."""
        inventory = tmp_path / "hosts"
        inventory.write_text("""[docker_test]
ubuntu24 ansible_host=localhost ansible_port=2224 ansible_user=test ansible_password=test
ubuntu18 ansible_host=localhost ansible_port=2218 ansible_user=test ansible_password=test

[all:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
""")
        return inventory

    def test_audit_ubuntu24(self, docker_inventory: Path, tmp_path: Path):
        """Should successfully audit Ubuntu 24.04 container."""
        from server_audit.runner import run_audit_to_json

        output_dir = tmp_path / "output"
        files = run_audit_to_json(
            docker_inventory,
            output_dir,
            hosts="ubuntu24",
        )

        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["os_info"]["distribution"] == "Ubuntu"
        assert "24" in data["os_info"]["version"]

    def test_audit_ubuntu18(self, docker_inventory: Path, tmp_path: Path):
        """Should successfully audit Ubuntu 18.04 container."""
        from server_audit.runner import run_audit_to_json

        output_dir = tmp_path / "output"
        files = run_audit_to_json(
            docker_inventory,
            output_dir,
            hosts="ubuntu18",
        )

        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["os_info"]["distribution"] == "Ubuntu"
        assert "18" in data["os_info"]["version"]

    def test_audit_all_hosts(self, docker_inventory: Path, tmp_path: Path):
        """Should audit all hosts in inventory."""
        from server_audit.runner import run_audit_to_json

        output_dir = tmp_path / "output"
        files = run_audit_to_json(docker_inventory, output_dir)

        assert len(files) == 2

    def test_json_output_schema(self, docker_inventory: Path, tmp_path: Path):
        """Output should match expected JSON schema."""
        from server_audit.runner import run_audit_to_json

        output_dir = tmp_path / "output"
        files = run_audit_to_json(docker_inventory, output_dir, hosts="ubuntu24")

        data = json.loads(files[0].read_text())

        # Verify required fields
        assert "os_info" in data
        assert "hardware" in data
        assert "disks" in data
        assert "networks" in data
        assert "vm_settings" in data
        assert "hostname" in data
        assert "audit_timestamp" in data

        # Verify nested structure
        assert "distribution" in data["os_info"]
        assert "version" in data["os_info"]
        assert "kernel" in data["os_info"]

        assert "memory_total" in data["hardware"]
        assert "cpu_count" in data["hardware"]
        assert "cpu_model" in data["hardware"]

        assert isinstance(data["disks"], list)
        if data["disks"]:
            assert "mount" in data["disks"][0]
            assert "device" in data["disks"][0]
            assert "size_total" in data["disks"][0]
