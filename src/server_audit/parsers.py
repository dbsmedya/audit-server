"""
Parsers for extracting structured data from shell command output.
"""

import re
from typing import Any

from server_audit.exceptions import ParseError
from server_audit.models import (
    AuditResult,
    DiskInfo,
    HardwareInfo,
    NetworkInfo,
    OSInfo,
    VMSettings,
)
from server_audit.payload import get_markers


def get_section(raw_text: str, start_marker: str, end_marker: str) -> str:
    """
    Extract a section of text between markers.

    Args:
        raw_text: The full output text
        start_marker: Start delimiter
        end_marker: End delimiter

    Returns:
        Text between markers, stripped of whitespace

    Raises:
        ParseError: If markers are not found
    """
    pattern = re.escape(start_marker) + r"\n?(.*?)\n?" + re.escape(end_marker)
    match = re.search(pattern, raw_text, re.DOTALL)
    if not match:
        raise ParseError(f"Section not found between {start_marker} and {end_marker}")
    return match.group(1).strip()


def parse_os_info(os_section: str, kernel_section: str) -> OSInfo:
    """
    Parse OS information from /etc/os-release or /etc/lsb-release.

    Args:
        os_section: Content of os-release or lsb-release
        kernel_section: Output of uname -r

    Returns:
        OSInfo dataclass with distribution, version, and kernel
    """
    distribution = "Unknown"
    version = "Unknown"

    # Try os-release format first (NAME= or ID=)
    name_match = re.search(r'^NAME="?([^"\n]+)"?', os_section, re.MULTILINE)
    if name_match:
        distribution = name_match.group(1).strip()
    else:
        # Try lsb-release format (DISTRIB_ID=)
        distrib_match = re.search(r'^DISTRIB_ID=(.+)$', os_section, re.MULTILINE)
        if distrib_match:
            distribution = distrib_match.group(1).strip()

    # Try VERSION_ID first (os-release), then DISTRIB_RELEASE (lsb-release)
    version_match = re.search(r'^VERSION_ID="?([^"\n]+)"?', os_section, re.MULTILINE)
    if version_match:
        version = version_match.group(1).strip()
    else:
        distrib_version = re.search(r'^DISTRIB_RELEASE=(.+)$', os_section, re.MULTILINE)
        if distrib_version:
            version = distrib_version.group(1).strip()

    kernel = kernel_section.strip()

    return OSInfo(distribution=distribution, version=version, kernel=kernel)


def parse_memory(mem_section: str) -> tuple[str, list[str]]:
    """
    Parse memory information from /proc/meminfo.

    Args:
        mem_section: Content from /proc/meminfo

    Returns:
        Tuple of (human-readable total memory, list of huge pages info)
    """
    mem_total = "N/A"
    huge_pages_raw = []

    # Parse MemTotal
    mem_match = re.search(r'^MemTotal:\s+(\d+)\s+kB', mem_section, re.MULTILINE)
    if mem_match:
        kb = int(mem_match.group(1))
        gb = kb / (1024 * 1024)
        mem_total = f"{gb:.2f} GB"

    # Extract huge pages info
    huge_patterns = [
        r'^AnonHugePages:\s+.+$',
        r'^ShmemHugePages:\s+.+$',
        r'^FileHugePages:\s+.+$',
        r'^HugePages_Total:\s+.+$',
        r'^HugePages_Free:\s+.+$',
    ]
    for pattern in huge_patterns:
        match = re.search(pattern, mem_section, re.MULTILINE)
        if match:
            huge_pages_raw.append(match.group(0))

    return mem_total, huge_pages_raw


def parse_cpu(cpu_section: str) -> tuple[int, str]:
    """
    Parse CPU information from lscpu or /proc/cpuinfo.

    Args:
        cpu_section: Output of lscpu or content of /proc/cpuinfo

    Returns:
        Tuple of (cpu_count, cpu_model)
    """
    cpu_count = 1
    cpu_model = "Unknown"

    # Try lscpu format first
    cpu_count_match = re.search(r'^CPU\(s\):\s+(\d+)', cpu_section, re.MULTILINE)
    if cpu_count_match:
        cpu_count = int(cpu_count_match.group(1))

    model_match = re.search(r'^Model name:\s+(.+)$', cpu_section, re.MULTILINE)
    if model_match:
        cpu_model = model_match.group(1).strip()
    else:
        # Fallback to /proc/cpuinfo format
        proc_model = re.search(r'^model name\s+:\s+(.+)$', cpu_section, re.MULTILINE)
        if proc_model:
            cpu_model = proc_model.group(1).strip()

        # Count processors in /proc/cpuinfo
        processor_count = len(re.findall(r'^processor\s+:\s+\d+', cpu_section, re.MULTILINE))
        if processor_count > 0:
            cpu_count = processor_count

    return cpu_count, cpu_model


def parse_disk_types(disk_type_section: str) -> dict[str, str]:
    """
    Parse disk type information (SSD vs HDD).

    Args:
        disk_type_section: Output of rotational check

    Returns:
        Dictionary mapping device names to "SSD" or "HDD"
    """
    disk_types = {}

    for line in disk_type_section.strip().split("\n"):
        if ":" in line:
            parts = line.split(":")
            if len(parts) == 2:
                device = parts[0].strip()
                rotational = parts[1].strip()
                # rotational=0 means SSD, rotational=1 means HDD
                disk_types[device] = "SSD" if rotational == "0" else "HDD"

    return disk_types


def parse_numa(numa_section: str) -> dict[str, str]:
    """
    Parse NUMA information from lscpu output.

    Args:
        numa_section: NUMA-related lines from lscpu

    Returns:
        Dictionary with NUMA topology information
    """
    numa = {}

    for line in numa_section.strip().split("\n"):
        if line.startswith("NUMA") and ":" in line:
            key, value = line.split(":", 1)
            numa[key.strip()] = value.strip()

    return numa


def parse_hardware(
    mem_section: str,
    cpu_section: str,
    disk_type_section: str,
    numa_section: str,
) -> tuple[HardwareInfo, list[str]]:
    """
    Parse all hardware information.

    Args:
        mem_section: Memory info from /proc/meminfo
        cpu_section: CPU info from lscpu or /proc/cpuinfo
        disk_type_section: Disk type rotational info
        numa_section: NUMA info from lscpu

    Returns:
        Tuple of (HardwareInfo, huge_pages_raw list)
    """
    memory_total, huge_pages_raw = parse_memory(mem_section)
    cpu_count, cpu_model = parse_cpu(cpu_section)
    disk_types = parse_disk_types(disk_type_section)
    numa = parse_numa(numa_section)

    hardware = HardwareInfo(
        memory_total=memory_total,
        cpu_count=cpu_count,
        cpu_model=cpu_model,
        disk_types=disk_types,
        numa=numa,
    )

    return hardware, huge_pages_raw


def parse_disks(df_section: str) -> list[DiskInfo]:
    """
    Parse disk space information from df output.

    Args:
        df_section: Output of df command

    Returns:
        List of DiskInfo objects for each mounted filesystem
    """
    disks = []
    lines = df_section.strip().split("\n")

    # Skip header line
    for line in lines[1:]:
        if not line.strip():
            continue

        # Handle wrapped lines (long device names)
        parts = line.split()
        if len(parts) < 5:
            continue

        # df -BK format: Filesystem Type 1K-blocks Avail Mounted
        # or standard df -k: Filesystem 1K-blocks Used Available Use% Mounted
        try:
            device = parts[0]

            # Detect if we have fstype in output (df --output format)
            # Check if second column looks like a filesystem type
            if parts[1] in ("ext4", "xfs", "btrfs", "nfs", "nfs4", "tmpfs", "squashfs", "vfat", "devtmpfs", "overlay"):
                fstype = parts[1]
                size_str = parts[2].rstrip("K")
                avail_str = parts[3].rstrip("K")
                mount = parts[4] if len(parts) > 4 else "/"
            else:
                # Standard df -k format (no fstype column)
                fstype = "unknown"
                size_str = parts[1].rstrip("K")
                avail_str = parts[3].rstrip("K")
                mount = parts[5] if len(parts) > 5 else "/"

            # Convert KB to bytes
            size_total = int(size_str) * 1024
            size_available = int(avail_str) * 1024

            disks.append(
                DiskInfo(
                    mount=mount,
                    device=device,
                    size_total=size_total,
                    size_available=size_available,
                    fstype=fstype,
                )
            )
        except (ValueError, IndexError):
            # Skip malformed lines
            continue

    return disks


def parse_networks(net_section: str) -> dict[str, NetworkInfo]:
    """
    Parse network interface information from ip addr or ifconfig.

    Args:
        net_section: Output of ip addr or ifconfig

    Returns:
        Dictionary mapping interface names to NetworkInfo
    """
    networks: dict[str, NetworkInfo] = {}

    # Try ip addr format first
    # Pattern: "2: eth0: <BROADCAST..." followed by lines with inet/ether
    interface_pattern = r'^\d+:\s+(\S+):'
    current_interface = None
    current_ipv4 = None
    current_mac = None

    for line in net_section.split("\n"):
        # Check for interface line
        iface_match = re.match(interface_pattern, line)
        if iface_match:
            # Save previous interface if exists
            if current_interface and current_interface != "lo":
                networks[current_interface] = NetworkInfo(
                    ipv4=current_ipv4,
                    mac=current_mac,
                )
            current_interface = iface_match.group(1).rstrip(":")
            current_ipv4 = None
            current_mac = None
            continue

        # Check for MAC address (link/ether)
        mac_match = re.search(r'link/ether\s+([0-9a-fA-F:]{17})', line)
        if mac_match and current_interface:
            current_mac = mac_match.group(1)

        # Check for IPv4 address
        ipv4_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
        if ipv4_match and current_interface:
            current_ipv4 = ipv4_match.group(1)

    # Don't forget the last interface
    if current_interface and current_interface != "lo":
        networks[current_interface] = NetworkInfo(
            ipv4=current_ipv4,
            mac=current_mac,
        )

    # If no interfaces found, try ifconfig format
    if not networks and "inet " in net_section:
        # ifconfig format parsing
        iface_blocks = re.split(r'(?=^\S)', net_section, flags=re.MULTILINE)
        for block in iface_blocks:
            if not block.strip():
                continue

            iface_match = re.match(r'^(\S+):', block)
            if not iface_match:
                iface_match = re.match(r'^(\S+)\s+', block)

            if iface_match:
                iface_name = iface_match.group(1)
                if iface_name == "lo":
                    continue

                ipv4 = None
                mac = None

                ipv4_match = re.search(r'inet\s+(?:addr:)?(\d+\.\d+\.\d+\.\d+)', block)
                if ipv4_match:
                    ipv4 = ipv4_match.group(1)

                mac_match = re.search(r'(?:ether|HWaddr)\s+([0-9a-fA-F:]{17})', block)
                if mac_match:
                    mac = mac_match.group(1)

                if ipv4 or mac:
                    networks[iface_name] = NetworkInfo(ipv4=ipv4, mac=mac)

    return networks


def parse_vm_settings(vm_section: str, huge_pages_raw: list[str]) -> VMSettings:
    """
    Parse virtual memory settings.

    Args:
        vm_section: Output of VM settings collection
        huge_pages_raw: List of huge pages info from meminfo

    Returns:
        VMSettings dataclass
    """
    settings: dict[str, str] = {}
    semaphores: dict[str, str] = {}

    for line in vm_section.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key == "semaphores":
                # Parse semaphore values: semmsl:semmns:semopm:semmni
                sem_parts = value.split(":")
                if len(sem_parts) >= 4:
                    semaphores = {
                        "semmsl": sem_parts[0],
                        "semmns": sem_parts[1],
                        "semopm": sem_parts[2],
                        "semmni": sem_parts[3],
                    }
            else:
                settings[key] = value

    return VMSettings(
        swappiness=settings.get("swappiness", "N/A"),
        overcommit_memory=settings.get("overcommit_memory", "N/A"),
        dirty_ratio=settings.get("dirty_ratio", "N/A"),
        dirty_background_ratio=settings.get("dirty_background_ratio", "N/A"),
        transparent_hugepages=settings.get("transparent_hugepages", "N/A"),
        huge_pages_raw=huge_pages_raw,
        semaphores=semaphores,
    )


def parse_raw_output(raw_text: str, hostname: str) -> AuditResult:
    """
    Parse complete raw output into structured AuditResult.

    Args:
        raw_text: Complete output from shell payload
        hostname: Name or IP of the host

    Returns:
        AuditResult with all parsed information

    Raises:
        ParseError: If required sections cannot be parsed
    """
    markers = get_markers()

    # Extract all sections
    os_section = get_section(raw_text, *markers["os"])
    kernel_section = get_section(raw_text, *markers["kernel"])
    mem_section = get_section(raw_text, *markers["memory"])
    cpu_section = get_section(raw_text, *markers["cpu"])
    disk_type_section = get_section(raw_text, *markers["disk_type"])
    df_section = get_section(raw_text, *markers["df"])
    net_section = get_section(raw_text, *markers["network"])
    vm_section = get_section(raw_text, *markers["vm"])
    numa_section = get_section(raw_text, *markers["numa"])

    # Parse each section
    os_info = parse_os_info(os_section, kernel_section)
    hardware, huge_pages_raw = parse_hardware(
        mem_section, cpu_section, disk_type_section, numa_section
    )
    disks = parse_disks(df_section)
    networks = parse_networks(net_section)
    vm_settings = parse_vm_settings(vm_section, huge_pages_raw)

    return AuditResult(
        hostname=hostname,
        os_info=os_info,
        hardware=hardware,
        disks=disks,
        networks=networks,
        vm_settings=vm_settings,
    )
