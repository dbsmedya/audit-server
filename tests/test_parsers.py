"""Tests for parsers module."""

import pytest

from server_audit.exceptions import ParseError
from server_audit.models import AuditResult, DiskInfo, NetworkInfo
from server_audit.parsers import (
    get_section,
    parse_cpu,
    parse_disk_types,
    parse_disks,
    parse_memory,
    parse_mysql_config_files,
    parse_mysql_runtime,
    parse_networks,
    parse_numa,
    parse_os_info,
    parse_raw_output,
    parse_vm_settings,
)


class TestGetSection:
    """Tests for get_section function."""

    def test_extracts_section(self):
        """Should extract content between markers."""
        raw = "before\n###START###\ncontent here\n###END###\nafter"
        result = get_section(raw, "###START###", "###END###")
        assert result == "content here"

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        raw = "###START###\n  content  \n###END###"
        result = get_section(raw, "###START###", "###END###")
        assert result == "content"

    def test_raises_on_missing_markers(self):
        """Should raise ParseError when markers not found."""
        raw = "no markers here"
        with pytest.raises(ParseError):
            get_section(raw, "###START###", "###END###")


class TestParseOsInfo:
    """Tests for parse_os_info function."""

    def test_parses_ubuntu_os_release(self):
        """Should parse Ubuntu os-release format."""
        os_section = '''NAME="Ubuntu"
VERSION_ID="22.04"
ID=ubuntu'''
        kernel = "5.15.0-160-generic"

        result = parse_os_info(os_section, kernel)

        assert result.distribution == "Ubuntu"
        assert result.version == "22.04"
        assert result.kernel == "5.15.0-160-generic"

    def test_parses_centos_format(self):
        """Should parse CentOS format."""
        os_section = '''NAME="CentOS Linux"
VERSION_ID="7"'''
        kernel = "3.10.0-1160.el7.x86_64"

        result = parse_os_info(os_section, kernel)

        assert result.distribution == "CentOS Linux"
        assert result.version == "7"

    def test_handles_lsb_release_format(self):
        """Should fallback to lsb-release format."""
        os_section = '''DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=18.04'''
        kernel = "4.15.0-generic"

        result = parse_os_info(os_section, kernel)

        assert result.distribution == "Ubuntu"
        assert result.version == "18.04"

    def test_handles_missing_info(self):
        """Should return Unknown for missing info."""
        result = parse_os_info("", "5.0.0")
        assert result.distribution == "Unknown"
        assert result.version == "Unknown"


class TestParseMemory:
    """Tests for parse_memory function."""

    def test_parses_memory_total(self):
        """Should convert KB to human-readable GB."""
        mem_section = "MemTotal:       32922148 kB\nMemFree:       1000000 kB"
        total, _ = parse_memory(mem_section)
        assert total == "31.40 GB"

    def test_extracts_huge_pages(self):
        """Should extract huge pages info."""
        mem_section = """MemTotal:       8000000 kB
AnonHugePages:         0 kB
HugePages_Total:       0"""
        _, huge_pages = parse_memory(mem_section)
        assert len(huge_pages) == 2
        assert "AnonHugePages:         0 kB" in huge_pages


class TestParseCpu:
    """Tests for parse_cpu function."""

    def test_parses_lscpu_format(self):
        """Should parse lscpu output."""
        cpu_section = """CPU(s):                             8
Model name:                         Intel(R) Xeon(R) Gold 6448Y"""
        count, model = parse_cpu(cpu_section)
        assert count == 8
        assert "Intel(R) Xeon(R) Gold 6448Y" in model

    def test_parses_proc_cpuinfo_format(self):
        """Should parse /proc/cpuinfo format."""
        cpu_section = """processor       : 0
model name      : Intel Core i7
processor       : 1
model name      : Intel Core i7"""
        count, model = parse_cpu(cpu_section)
        assert count == 2
        assert "Intel Core i7" in model


class TestParseDiskTypes:
    """Tests for parse_disk_types function."""

    def test_parses_ssd_hdd(self):
        """Should identify SSD (0) and HDD (1)."""
        section = "sda:0\nsdb:1\nsr0:1"
        result = parse_disk_types(section)
        assert result["sda"] == "SSD"
        assert result["sdb"] == "HDD"
        assert result["sr0"] == "HDD"


class TestParseNuma:
    """Tests for parse_numa function."""

    def test_parses_numa_info(self):
        """Should parse NUMA topology."""
        section = "NUMA node(s):                       1\nNUMA node0 CPU(s):                  0-7"
        result = parse_numa(section)
        assert result["NUMA node(s)"] == "1"
        assert result["NUMA node0 CPU(s)"] == "0-7"


class TestParseDisks:
    """Tests for parse_disks function."""

    def test_parses_df_output(self):
        """Should parse df output into DiskInfo list."""
        df_section = """Filesystem                      Type  1K-blocks      Avail Mounted on
/dev/mapper/vg01-lv--root       ext4  144274320   75304168 /
/dev/sda3                       ext4   16337788   15224372 /boot"""
        result = parse_disks(df_section)

        assert len(result) == 2
        assert result[0].mount == "/"
        assert result[0].device == "/dev/mapper/vg01-lv--root"
        assert result[0].fstype == "ext4"
        assert result[0].size_total == 144274320 * 1024
        assert result[0].size_available == 75304168 * 1024


class TestParseNetworks:
    """Tests for parse_networks function."""

    def test_parses_ip_addr_output(self):
        """Should parse ip addr output."""
        section = """1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
2: ens160: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    link/ether 00:50:56:a8:11:ed brd ff:ff:ff:ff:ff:ff
    inet 192.168.121.45/24 scope global ens160"""

        result = parse_networks(section)

        assert "lo" not in result  # Should exclude loopback
        assert "ens160" in result
        assert result["ens160"].ipv4 == "192.168.121.45"
        assert result["ens160"].mac == "00:50:56:a8:11:ed"


class TestParseVmSettings:
    """Tests for parse_vm_settings function."""

    def test_parses_vm_settings(self):
        """Should parse VM settings."""
        section = """swappiness:60
overcommit_memory:0
dirty_ratio:20
dirty_background_ratio:10
transparent_hugepages:madvise
semaphores:32000:1024000000:500:32000"""
        huge_pages = ["AnonHugePages:         0 kB"]

        result = parse_vm_settings(section, huge_pages)

        assert result.swappiness == "60"
        assert result.overcommit_memory == "0"
        assert result.dirty_ratio == "20"
        assert result.dirty_background_ratio == "10"
        assert result.transparent_hugepages == "madvise"
        assert result.semaphores["semmsl"] == "32000"
        assert result.semaphores["semmns"] == "1024000000"
        assert result.huge_pages_raw == huge_pages


class TestParseMySQLConfigFiles:
    """Tests for parse_mysql_config_files function."""

    def test_last_value_wins_and_conflict_is_reported(self):
        """A later line overrides an earlier one; differing values are a conflict."""
        section = """--user=mysql
--explicit_defaults_for_timestamp=OFF
--max_connections=4096
--explicit_defaults_for_timestamp=1"""

        result = parse_mysql_config_files(section)

        assert result.status == "ok"
        assert result.effective["explicit_defaults_for_timestamp"] == "1"
        assert result.duplicates["explicit_defaults_for_timestamp"] == ["OFF", "1"]
        assert result.conflicts == ["explicit_defaults_for_timestamp"]
        assert result.options == section.split("\n")

    def test_repeated_equal_values_are_not_a_conflict(self):
        """The same value set twice, including ON versus 1, is a duplicate only."""
        section = """--log_bin_trust_function_creators=ON
--log_bin_trust_function_creators=ON
--event_scheduler=ON
--event_scheduler=1"""

        result = parse_mysql_config_files(section)

        assert result.duplicates["log_bin_trust_function_creators"] == ["ON", "ON"]
        assert result.duplicates["event_scheduler"] == ["ON", "1"]
        assert result.conflicts == []

    def test_option_names_are_normalized(self):
        """Dashes, underscores and the loose- prefix name the same option."""
        section = """--collation-server=utf8_unicode_ci
--loose-audit_log_filter_file=/var/log/mysql/audit.log
--collation_server=utf8mb4_0900_ai_ci"""

        result = parse_mysql_config_files(section)

        assert result.effective["collation_server"] == "utf8mb4_0900_ai_ci"
        assert result.effective["audit_log_filter_file"] == "/var/log/mysql/audit.log"
        assert result.conflicts == ["collation_server"]

    def test_value_may_contain_equals_sign(self):
        """Only the first equals sign separates the name from the value."""
        result = parse_mysql_config_files("--early-plugin-load=keyring_vault=keyring_vault.so")

        assert result.effective["early_plugin_load"] == "keyring_vault=keyring_vault.so"

    def test_flag_without_value(self):
        """An option without a value is recorded with no value."""
        result = parse_mysql_config_files("--skip-log-bin\n--sql_mode=")

        assert result.effective["skip_log_bin"] is None
        assert result.effective["sql_mode"] == ""

    def test_password_values_are_masked(self):
        """A password printed by an old my_print_defaults never reaches the output."""
        result = parse_mysql_config_files("--password=secret\n--user=mysql")

        assert result.effective["password"] == "*****"
        assert "secret" not in "\n".join(result.options)

    def test_mysql_not_installed(self):
        """A host without my_print_defaults reports not_installed."""
        result = parse_mysql_config_files("MYSQL_NOT_INSTALLED")

        assert result.status == "not_installed"
        assert result.effective == {}

    def test_error_output_without_options(self):
        """Lines that are not options are kept as messages."""
        result = parse_mysql_config_files("my_print_defaults: [ERROR] Found option without preceding group")

        assert result.status == "error"
        assert result.messages == ["my_print_defaults: [ERROR] Found option without preceding group"]

    def test_no_mysqld_group(self):
        """Empty output means no option file has a [mysqld] group."""
        result = parse_mysql_config_files("")

        assert result.status == "empty"


class TestParseMySQLRuntime:
    """Tests for parse_mysql_runtime function."""

    def test_parses_variables(self):
        """Tab-separated rows become variables; an empty value is preserved."""
        section = (
            "explicit_defaults_for_timestamp\tON\n"
            "sql_mode\t\n"
            "time_zone\tSYSTEM\n"
            "version\t8.0.42-33"
        )

        result = parse_mysql_runtime(section)

        assert result.status == "ok"
        assert result.variables == {
            "explicit_defaults_for_timestamp": "ON",
            "sql_mode": "",
            "time_zone": "SYSTEM",
            "version": "8.0.42-33",
        }

    def test_empty_value_on_the_last_line(self):
        """A trailing empty value survives the section's whitespace stripping."""
        result = parse_mysql_runtime("version\t8.0.42-33\nsql_mode")

        assert result.variables["sql_mode"] == ""

    def test_access_denied(self):
        """A failed login is reported as unavailable with the server's message."""
        section = (
            "ERROR 1045 (28000): Access denied for user 'ubuntu'@'localhost' (using password: NO)\n"
            "MYSQL_QUERY_FAILED"
        )

        result = parse_mysql_runtime(section)

        assert result.status == "unavailable"
        assert result.variables == {}
        assert result.messages[0].startswith("ERROR 1045")

    def test_mysql_not_installed(self):
        """A host without the mysql client reports not_installed."""
        result = parse_mysql_runtime("MYSQL_NOT_INSTALLED")

        assert result.status == "not_installed"


class TestParseRawOutput:
    """Tests for parse_raw_output function."""

    def test_parses_complete_output(self, sample_output: str):
        """Should parse complete sample output."""
        result = parse_raw_output(sample_output, "testhost")

        assert isinstance(result, AuditResult)
        assert result.hostname == "testhost"

        # OS info
        assert result.os_info.distribution == "Ubuntu"
        assert result.os_info.version == "22.04"
        assert result.os_info.kernel == "5.15.0-160-generic"

        # Hardware
        assert result.hardware.cpu_count == 8
        assert "Intel" in result.hardware.cpu_model
        assert "GB" in result.hardware.memory_total
        assert result.hardware.disk_types["sda"] == "SSD"
        assert result.hardware.disk_types["sr0"] == "HDD"

        # Disks
        assert len(result.disks) > 0
        root_disk = next((d for d in result.disks if d.mount == "/"), None)
        assert root_disk is not None
        assert root_disk.fstype == "ext4"

        # Networks
        assert "ens160" in result.networks
        assert result.networks["ens160"].ipv4 == "192.168.121.45"

        # VM settings
        assert result.vm_settings.swappiness == "60"
        assert result.vm_settings.transparent_hugepages == "madvise"

    def test_to_dict_serialization(self, sample_output: str):
        """Result should serialize to dict properly."""
        result = parse_raw_output(sample_output, "testhost")
        data = result.to_dict()

        assert isinstance(data, dict)
        assert "os_info" in data
        assert "hardware" in data
        assert "disks" in data
        assert "networks" in data
        assert "vm_settings" in data
        assert data["hostname"] == "testhost"

    def test_output_without_mysql_sections(self, sample_output: str):
        """Output from a payload without MySQL sections parses with mysql set to None."""
        result = parse_raw_output(sample_output, "testhost")

        assert result.mysql is None
        assert result.to_dict()["mysql"] is None

    def test_output_with_mysql_sections(self, sample_output: str):
        """MySQL sections are parsed and serialized under the mysql key."""
        raw = sample_output + (
            "###MARKER_MYSQL_DEFAULTS_START###\n"
            "--explicit_defaults_for_timestamp=OFF\n"
            "--explicit_defaults_for_timestamp=1\n"
            "###MARKER_MYSQL_DEFAULTS_END###\n"
            "###MARKER_MYSQL_VARS_START###\n"
            "explicit_defaults_for_timestamp\tON\n"
            "version\t8.0.42-33\n"
            "###MARKER_MYSQL_VARS_END###\n"
        )

        data = parse_raw_output(raw, "testhost").to_dict()

        assert data["mysql"]["config_files"]["effective"]["explicit_defaults_for_timestamp"] == "1"
        assert data["mysql"]["config_files"]["conflicts"] == ["explicit_defaults_for_timestamp"]
        assert data["mysql"]["runtime"]["variables"]["explicit_defaults_for_timestamp"] == "ON"
        assert data["mysql"]["runtime"]["status"] == "ok"
