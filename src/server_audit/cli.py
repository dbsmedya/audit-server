"""
Command-line interface for server-audit.
"""

import argparse
import sys
from pathlib import Path

from server_audit import __version__
from server_audit.exceptions import AuditError
from server_audit.runner import run_audit_to_json


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="server-audit",
        description="Collect OS and hardware information from Linux servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  server-audit -i inventory/hosts -o output/
  server-audit --inventory hosts --output audit.json --hosts webservers
  server-audit -i hosts -o results/ --hosts "db*"
        """,
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-i", "--inventory",
        required=True,
        type=Path,
        metavar="PATH",
        help="Path to Ansible inventory file",
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        type=Path,
        metavar="PATH",
        help="Output path (directory for per-host files, or .json file for combined)",
    )

    parser.add_argument(
        "--hosts",
        default="all",
        metavar="PATTERN",
        help="Host pattern to audit (default: all)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        print(f"server-audit v{__version__}")
        print(f"Inventory: {args.inventory}")
        print(f"Output: {args.output}")
        print(f"Hosts: {args.hosts}")
        print()

    try:
        if not args.inventory.exists():
            print(f"Error: Inventory file not found: {args.inventory}", file=sys.stderr)
            return 1

        if args.verbose:
            print("Running audit...")

        created_files = run_audit_to_json(
            inventory_path=args.inventory,
            output_path=args.output,
            hosts=args.hosts,
        )

        if args.verbose:
            print(f"\nAudit complete. Created {len(created_files)} file(s):")
            for f in created_files:
                print(f"  - {f}")
        else:
            for f in created_files:
                print(f)

        return 0

    except AuditError as e:
        print(f"Audit error: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
