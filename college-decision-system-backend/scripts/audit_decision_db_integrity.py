from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.db.integrity import (  # noqa: E402
    collect_decision_schema_drift,
    collect_decision_table_inventory,
    collect_duplicate_counts,
    collect_integrity_counts,
    collect_mapping_gap_counts,
    collect_runtime_index_status,
    get_sqlite_foreign_keys_enabled,
)
from app.infrastructure.db.session import SessionLocal, engine  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the active decision_* database schema for integrity and cutover readiness."
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def build_report() -> dict[str, object]:
    with SessionLocal() as session:
        return {
            "sqlite_foreign_keys_enabled": get_sqlite_foreign_keys_enabled(session),
            "table_inventory": collect_decision_table_inventory(engine),
            "integrity_counts": collect_integrity_counts(session),
            "duplicate_counts": collect_duplicate_counts(session),
            "mapping_gap_counts": collect_mapping_gap_counts(session),
            "runtime_index_status": {
                table_name: {
                    ",".join(columns): present
                    for columns, present in status.items()
                }
                for table_name, status in collect_runtime_index_status(engine).items()
            },
            "schema_drift": collect_decision_schema_drift(engine),
        }


def print_text_report(report: dict[str, object]) -> None:
    print(f"sqlite_foreign_keys_enabled: {report['sqlite_foreign_keys_enabled']}")
    print("integrity_counts:")
    for name, value in report["integrity_counts"].items():
        print(f"  {name}: {value}")
    print("duplicate_counts:")
    for name, value in report["duplicate_counts"].items():
        print(f"  {name}: {value}")
    print("mapping_gap_counts:")
    for name, value in report["mapping_gap_counts"].items():
        print(f"  {name}: {value}")
    print("schema_drift:")
    for name, value in report["schema_drift"].items():
        print(f"  {name}: {value}")


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
