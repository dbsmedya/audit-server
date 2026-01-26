"""
Ansible runner orchestration for executing audit payloads.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ansible_runner

from server_audit.exceptions import ConnectionError, PayloadError
from server_audit.models import AuditResult
from server_audit.parsers import parse_raw_output
from server_audit.payload import build_payload


def run_audit(
    inventory_path: str | Path,
    hosts: str = "all",
    output_dir: str | Path | None = None,
) -> dict[str, AuditResult]:
    """
    Run audit against hosts in the inventory.

    Args:
        inventory_path: Path to Ansible inventory file
        hosts: Host pattern to audit (default: "all")
        output_dir: Optional directory for ansible_runner artifacts

    Returns:
        Dictionary mapping hostnames to AuditResult objects

    Raises:
        ConnectionError: If connection to a host fails
        PayloadError: If payload execution fails
    """
    inventory_path = Path(inventory_path)
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

    payload = build_payload()

    # Create temporary directory for artifacts if not specified
    if output_dir is None:
        artifact_dir = tempfile.mkdtemp(prefix="server_audit_")
    else:
        artifact_dir = str(output_dir)

    # Run ansible ad-hoc command with raw module (no Python required on remote)
    result = ansible_runner.run(
        private_data_dir=artifact_dir,
        inventory=str(inventory_path),
        host_pattern=hosts,
        module="raw",
        module_args=payload,
        quiet=True,
    )

    results: dict[str, AuditResult] = {}

    # Process results for each host
    for event in result.events:
        if event.get("event") == "runner_on_ok":
            event_data = event.get("event_data", {})
            host = event_data.get("host")
            res = event_data.get("res", {})
            stdout = res.get("stdout", "")

            if host and stdout:
                try:
                    audit_result = parse_raw_output(stdout, host)
                    results[host] = audit_result
                except Exception as e:
                    raise PayloadError(f"Failed to parse output: {e}", host=host) from e

        elif event.get("event") == "runner_on_failed":
            event_data = event.get("event_data", {})
            host = event_data.get("host")
            res = event_data.get("res", {})
            msg = res.get("msg", "Unknown error")
            raise PayloadError(f"Payload execution failed: {msg}", host=host)

        elif event.get("event") == "runner_on_unreachable":
            event_data = event.get("event_data", {})
            host = event_data.get("host")
            res = event_data.get("res", {})
            msg = res.get("msg", "Host unreachable")
            raise ConnectionError(f"Cannot connect: {msg}", host=host)

    return results


def run_audit_to_json(
    inventory_path: str | Path,
    output_path: str | Path,
    hosts: str = "all",
) -> list[Path]:
    """
    Run audit and save results to JSON files.

    Args:
        inventory_path: Path to Ansible inventory file
        output_path: Path for output (directory or file)
        hosts: Host pattern to audit (default: "all")

    Returns:
        List of paths to created JSON files
    """
    results = run_audit(inventory_path, hosts)
    output_path = Path(output_path)
    created_files: list[Path] = []

    # If output_path is a file, write all results to one file
    if output_path.suffix == ".json":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        all_results = {
            host: result.to_dict() for host, result in results.items()
        }
        output_path.write_text(json.dumps(all_results, indent=4))
        created_files.append(output_path)
    else:
        # Write individual files per host
        output_path.mkdir(parents=True, exist_ok=True)
        for host, result in results.items():
            # Sanitize hostname for filename
            safe_host = host.replace("/", "_").replace(":", "_")
            file_path = output_path / f"audit_{safe_host}.json"
            file_path.write_text(json.dumps(result.to_dict(), indent=4))
            created_files.append(file_path)

    return created_files


def get_host_list(inventory_path: str | Path, hosts: str = "all") -> list[str]:
    """
    Get list of hosts from inventory matching the pattern.

    Args:
        inventory_path: Path to Ansible inventory file
        hosts: Host pattern (default: "all")

    Returns:
        List of hostnames matching the pattern
    """
    inventory_path = Path(inventory_path)
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

    with tempfile.TemporaryDirectory(prefix="server_audit_") as tmpdir:
        result = ansible_runner.run(
            private_data_dir=tmpdir,
            inventory=str(inventory_path),
            host_pattern=hosts,
            module="ping",
            quiet=True,
        )

        host_list = []
        for event in result.events:
            event_data = event.get("event_data", {})
            host = event_data.get("host")
            if host and host not in host_list:
                host_list.append(host)

        return host_list
