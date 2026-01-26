# Server Audit

A Python tool for collecting operating system and hardware information from Linux servers using Ansible in ad-hoc mode.

## Features

- **Zero dependencies on remote hosts** - Uses Ansible's `raw` module, no Python required on target servers
- **Supports older Linux distributions** - Works with Ubuntu 18.04+ and other legacy systems
- **Comprehensive data collection**:
  - OS distribution and version
  - Kernel version
  - CPU information (model, count, NUMA topology)
  - Memory (total, available, huge pages)
  - Disk information (mounts, capacity, SSD/HDD detection)
  - Network interfaces (IPv4, MAC addresses)
  - VM tuning settings (swappiness, overcommit, transparent hugepages)
- **JSON output** - Structured output for easy integration with other tools
- **Library and CLI** - Use programmatically or from the command line

## Requirements

- Python 3.9+
- SSH access to target hosts
- Ansible Runner (`ansible-runner>=2.3.0`)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd audit

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

```bash
# Audit all hosts in inventory, output to directory (one file per host)
server-audit -i inventory/hosts -o output/

# Audit specific host group
server-audit -i inventory/hosts -o output/ --hosts webservers

# Audit with host pattern
server-audit -i inventory/hosts -o output/ --hosts "db*"

# Output to single combined JSON file
server-audit -i inventory/hosts -o audit_results.json

# Verbose mode
server-audit -i inventory/hosts -o output/ -v
```

#### CLI Options

| Option | Description |
|--------|-------------|
| `-i, --inventory PATH` | Path to Ansible inventory file (required) |
| `-o, --output PATH` | Output path - directory for per-host files, or `.json` file for combined output (required) |
| `--hosts PATTERN` | Host pattern to audit (default: `all`) |
| `-v, --verbose` | Enable verbose output |
| `-V, --version` | Show version |

### Library Usage

```python
from server_audit import run_audit, AuditResult

# Run audit and get results as AuditResult objects
results = run_audit("inventory/hosts", hosts="all")

for hostname, result in results.items():
    print(f"{hostname}: {result.os_info.distribution} {result.os_info.version}")
    print(f"  CPU: {result.hardware.cpu_count} cores")
    print(f"  Memory: {result.hardware.memory_total}")
```

```python
from server_audit.runner import run_audit_to_json

# Run audit and save directly to JSON files
files = run_audit_to_json(
    inventory_path="inventory/hosts",
    output_path="output/",
    hosts="webservers"
)

print(f"Created {len(files)} audit files")
```

## Inventory File

Use standard Ansible inventory format:

```ini
[webservers]
web1 ansible_host=192.168.1.10 ansible_user=admin
web2 ansible_host=192.168.1.11 ansible_user=admin

[databases]
db1 ansible_host=192.168.1.20 ansible_user=dba

[all:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

For password authentication, add `ansible_password`:

```ini
[servers]
server1 ansible_host=192.168.1.10 ansible_user=test ansible_password=secret
```

## Output Format

Each audit produces a JSON file with the following structure:

```json
{
    "hostname": "web1",
    "audit_timestamp": "2026-01-24T10:30:00+00:00",
    "os_info": {
        "distribution": "Ubuntu",
        "version": "24.04",
        "kernel": "6.8.0-45-generic"
    },
    "hardware": {
        "memory_total": "15.6 GB",
        "cpu_count": 8,
        "cpu_model": "Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz",
        "disk_types": {
            "sda": "SSD",
            "sdb": "HDD"
        },
        "numa": {
            "NUMA node(s)": "2",
            "NUMA node0 CPU(s)": "0-3",
            "NUMA node1 CPU(s)": "4-7"
        }
    },
    "disks": [
        {
            "mount": "/",
            "device": "/dev/sda1",
            "size_total": 107374182400,
            "size_available": 53687091200,
            "fstype": "ext4"
        }
    ],
    "networks": {
        "eth0": {
            "ipv4": "192.168.1.10",
            "mac": "00:11:22:33:44:55"
        }
    },
    "vm_settings": {
        "swappiness": "60",
        "overcommit_memory": "0",
        "dirty_ratio": "20",
        "dirty_background_ratio": "10",
        "transparent_hugepages": "always",
        "huge_pages_raw": ["HugePages_Total: 0", "HugePages_Free: 0"],
        "semaphores": {
            "semmsl": "32000",
            "semmns": "1024000000",
            "semopm": "500",
            "semmni": "32000"
        }
    }
}
```

## Project Structure

```
audit/
├── src/server_audit/
│   ├── __init__.py      # Public API exports
│   ├── cli.py           # Command-line interface
│   ├── exceptions.py    # Custom exceptions
│   ├── models.py        # Data models (AuditResult, etc.)
│   ├── parsers.py       # Output parsing logic
│   ├── payload.py       # Shell command payload
│   └── runner.py        # Ansible runner orchestration
├── tests/               # Test suite
├── inventory/           # Sample inventory files
├── output/              # Default output directory
└── docker/              # Docker test environment
```

## License

MIT
