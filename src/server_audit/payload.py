"""
Shell command payloads for collecting system information.

Uses delimited sections for reliable parsing of stdout.
All commands use LC_ALL=C for consistent output format.
"""

# Section markers for parsing
MARKER_OS_START = "###MARKER_OS_START###"
MARKER_OS_END = "###MARKER_OS_END###"
MARKER_KERNEL_START = "###MARKER_KERNEL_START###"
MARKER_KERNEL_END = "###MARKER_KERNEL_END###"
MARKER_MEM_START = "###MARKER_MEM_START###"
MARKER_MEM_END = "###MARKER_MEM_END###"
MARKER_CPU_START = "###MARKER_CPU_START###"
MARKER_CPU_END = "###MARKER_CPU_END###"
MARKER_DISK_TYPE_START = "###MARKER_DISK_TYPE_START###"
MARKER_DISK_TYPE_END = "###MARKER_DISK_TYPE_END###"
MARKER_DF_START = "###MARKER_DF_START###"
MARKER_DF_END = "###MARKER_DF_END###"
MARKER_NET_START = "###MARKER_NET_START###"
MARKER_NET_END = "###MARKER_NET_END###"
MARKER_VM_START = "###MARKER_VM_START###"
MARKER_VM_END = "###MARKER_VM_END###"
MARKER_NUMA_START = "###MARKER_NUMA_START###"
MARKER_NUMA_END = "###MARKER_NUMA_END###"
MARKER_MYSQL_DEFAULTS_START = "###MARKER_MYSQL_DEFAULTS_START###"
MARKER_MYSQL_DEFAULTS_END = "###MARKER_MYSQL_DEFAULTS_END###"
MARKER_MYSQL_VARS_START = "###MARKER_MYSQL_VARS_START###"
MARKER_MYSQL_VARS_END = "###MARKER_MYSQL_VARS_END###"

# Variables that change what the application sees. A replacement host must
# carry them over from the source; they are compared, never recalculated.
MYSQL_BEHAVIOUR_VARIABLES = (
    "version",
    "explicit_defaults_for_timestamp",
    "sql_mode",
    "character_set_server",
    "collation_server",
    "lower_case_table_names",
    "time_zone",
    "system_time_zone",
    "transaction_isolation",
    "auto_increment_increment",
    "auto_increment_offset",
)


def build_payload() -> str:
    """
    Build the complete shell command payload.

    Returns:
        Shell command string that collects all system information
        with delimited sections for parsing.
    """
    mysql_variables = ", ".join(f"'{name}'" for name in MYSQL_BEHAVIOUR_VARIABLES)
    return f"""export LC_ALL=C

# OS Information
echo '{MARKER_OS_START}'
if [ -f /etc/os-release ]; then
    cat /etc/os-release
elif [ -f /etc/lsb-release ]; then
    cat /etc/lsb-release
else
    echo 'DISTRIB_ID=Unknown'
    echo 'DISTRIB_RELEASE=Unknown'
fi
echo '{MARKER_OS_END}'

# Kernel version
echo '{MARKER_KERNEL_START}'
uname -r
echo '{MARKER_KERNEL_END}'

# Memory information
echo '{MARKER_MEM_START}'
cat /proc/meminfo | grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree|AnonHugePages|ShmemHugePages|FileHugePages|HugePages_Total|HugePages_Free):'
echo '{MARKER_MEM_END}'

# CPU information
echo '{MARKER_CPU_START}'
if command -v lscpu >/dev/null 2>&1; then
    lscpu
else
    cat /proc/cpuinfo
fi
echo '{MARKER_CPU_END}'

# Disk type detection (SSD vs HDD)
echo '{MARKER_DISK_TYPE_START}'
for disk in /sys/block/*/queue/rotational; do
    if [ -f "$disk" ]; then
        device=$(echo "$disk" | cut -d'/' -f4)
        rotational=$(cat "$disk" 2>/dev/null || echo "1")
        echo "$device:$rotational"
    fi
done
echo '{MARKER_DISK_TYPE_END}'

# Disk space (df)
echo '{MARKER_DF_START}'
df -BK --output=source,fstype,size,avail,target 2>/dev/null || df -k
echo '{MARKER_DF_END}'

# Network interfaces
echo '{MARKER_NET_START}'
if command -v ip >/dev/null 2>&1; then
    ip addr
else
    ifconfig -a 2>/dev/null || echo "NO_NETWORK_CMD"
fi
echo '{MARKER_NET_END}'

# VM settings
echo '{MARKER_VM_START}'
echo "swappiness:$(cat /proc/sys/vm/swappiness 2>/dev/null || echo 'N/A')"
echo "overcommit_memory:$(cat /proc/sys/vm/overcommit_memory 2>/dev/null || echo 'N/A')"
echo "dirty_ratio:$(cat /proc/sys/vm/dirty_ratio 2>/dev/null || echo 'N/A')"
echo "dirty_background_ratio:$(cat /proc/sys/vm/dirty_background_ratio 2>/dev/null || echo 'N/A')"
echo "transparent_hugepages:$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null | grep -oP '\\[\\K[^\\]]+' || echo 'N/A')"
echo "semaphores:$(cat /proc/sys/kernel/sem 2>/dev/null | tr '\\t' ':' || echo 'N/A')"
echo '{MARKER_VM_END}'

# NUMA information
echo '{MARKER_NUMA_START}'
if command -v lscpu >/dev/null 2>&1; then
    lscpu | grep -E '^NUMA'
else
    echo "NUMA_NOT_AVAILABLE"
fi
echo '{MARKER_NUMA_END}'

# MySQL option files, as mysqld reads them (my_print_defaults masks passwords)
echo '{MARKER_MYSQL_DEFAULTS_START}'
if command -v my_print_defaults >/dev/null 2>&1; then
    my_print_defaults mysqld 2>&1
else
    echo 'MYSQL_NOT_INSTALLED'
fi
echo '{MARKER_MYSQL_DEFAULTS_END}'

# MySQL behaviour variables from the running server; credentials come from the
# executing user's option files (for example root's socket login under become)
echo '{MARKER_MYSQL_VARS_START}'
if command -v mysql >/dev/null 2>&1; then
    mysql --connect-timeout=5 -NB -e "SHOW GLOBAL VARIABLES WHERE Variable_name IN ({mysql_variables})" 2>&1 || echo 'MYSQL_QUERY_FAILED'
else
    echo 'MYSQL_NOT_INSTALLED'
fi
echo '{MARKER_MYSQL_VARS_END}'
"""


def get_markers() -> dict[str, tuple[str, str]]:
    """
    Get all marker pairs for section extraction.

    Returns:
        Dictionary mapping section names to (start, end) marker tuples.
    """
    return {
        "os": (MARKER_OS_START, MARKER_OS_END),
        "kernel": (MARKER_KERNEL_START, MARKER_KERNEL_END),
        "memory": (MARKER_MEM_START, MARKER_MEM_END),
        "cpu": (MARKER_CPU_START, MARKER_CPU_END),
        "disk_type": (MARKER_DISK_TYPE_START, MARKER_DISK_TYPE_END),
        "df": (MARKER_DF_START, MARKER_DF_END),
        "network": (MARKER_NET_START, MARKER_NET_END),
        "vm": (MARKER_VM_START, MARKER_VM_END),
        "numa": (MARKER_NUMA_START, MARKER_NUMA_END),
        "mysql_defaults": (MARKER_MYSQL_DEFAULTS_START, MARKER_MYSQL_DEFAULTS_END),
        "mysql_vars": (MARKER_MYSQL_VARS_START, MARKER_MYSQL_VARS_END),
    }
