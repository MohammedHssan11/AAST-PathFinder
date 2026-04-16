from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.schema.normalize_colleges import normalize_college_file, summarize_file_flags


def _safe_filename_token(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]+', "_", value).strip()
    return safe or "normalized"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize raw college JSON files to DecisionSchema v1."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=(ROOT_DIR.parent / "colleges"),
        help="Directory containing raw college JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(ROOT_DIR / "normalized_colleges"),
        help="Directory where normalized files will be written.",
    )
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.json"))

    total_files = 0
    success_count = 0
    fail_count = 0
    completeness_counter: Counter[str] = Counter()
    decision_ready_counter: Counter[str] = Counter()
    errors: list[str] = []

    for input_path in files:
        total_files += 1
        try:
            normalized = normalize_college_file(input_path)
            college_id = str(normalized.get("college", {}).get("college_id") or "").strip()
            output_stem = _safe_filename_token(college_id) if college_id else input_path.stem
            output_path = output_dir / f"{output_stem}.normalized.json"
            output_path.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            completeness, decision_ready = summarize_file_flags(normalized)
            completeness_counter[completeness] += 1
            decision_ready_counter["true" if decision_ready else "false"] += 1
            success_count += 1
        except Exception as exc:  # noqa: BLE001
            fail_count += 1
            errors.append(f"{input_path.name}: {exc}")

    print(f"total_files: {total_files}")
    print(f"success_count: {success_count}")
    print(f"fail_count: {fail_count}")
    print(
        "data_completeness_counts: "
        f"high={completeness_counter.get('high', 0)}, "
        f"medium={completeness_counter.get('medium', 0)}, "
        f"low={completeness_counter.get('low', 0)}"
    )
    print(
        "decision_ready_counts: "
        f"true={decision_ready_counter.get('true', 0)}, "
        f"false={decision_ready_counter.get('false', 0)}"
    )

    if errors:
        print("failures:")
        for error in errors:
            print(f"- {error}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
