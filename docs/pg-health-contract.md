# Data Contract: server-audit → pg-health

**Version:** 1.0
**Date:** 2026-03-24

## Overview

The `pg-health` reporting tool optionally consumes `server-audit` JSON output to generate hardware profile sections and PostgreSQL tuning recommendations in health reports.

The canonical contract is maintained at:
**`healthcheck_project/docs/api/contract.md`**

## Fields consumed by pg-health

### Required top-level keys
`os_info`, `hardware`, `disks`, `vm_settings`

### Critical field formats

| Field | Type | Format | Notes |
|-------|------|--------|-------|
| `hardware.memory_total` | string | `"N.NN GB"` | Parsed by pg-health for tuning calculations. MUST be `"<number> <unit>"` |
| `hardware.cpu_count` | int | flat integer | Used for `max_parallel_workers` recommendation |
| `hardware.disk_types` | dict | `{"device": "SSD"\|"HDD"}` | Used for `random_page_cost` + `effective_io_concurrency` |
| `disk.size_total` | int | bytes | Template divides by 1073741824 for GB display |
| `disk.size_available` | int | bytes | Same |
| `vm_settings.*` | string | all strings | Template uses `\| int` Jinja2 filter for numeric comparisons |

### Fields NOT consumed by pg-health
`networks`, `hostname`, `audit_timestamp`, `hardware.cpu_model`, `hardware.numa`, `vm_settings.huge_pages_raw`

## Breaking changes

Any rename or type change to consumed fields requires coordinated updates in both projects. See the full contract in `healthcheck_project/docs/api/contract.md` for the complete specification.
