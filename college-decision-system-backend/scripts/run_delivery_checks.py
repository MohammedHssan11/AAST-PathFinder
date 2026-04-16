from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402


def run_command(args: list[str]) -> None:
    print(f"$ {' '.join(args)}", flush=True)
    subprocess.run(args, cwd=ROOT_DIR, check=True)


def run_smoke_checks() -> None:
    client = TestClient(app)
    cases = [
        (
            "ai_budgeted",
            {
                "certificate_type": "Egyptian Thanaweya Amma (Science)",
                "high_school_percentage": 85,
                "student_group": "other_states",
                "budget": 5000,
                "interests": ["AI"],
                "track_type": "regular",
                "max_results": 1,
            },
        ),
        (
            "budget_sensitive",
            {
                "certificate_type": "Egyptian Thanaweya Amma (Science)",
                "high_school_percentage": 85,
                "student_group": "other_states",
                "budget": 2200,
                "interests": ["business"],
                "track_type": "regular",
                "max_results": 1,
            },
        ),
        (
            "incomplete_data",
            {
                "certificate_type": "Egyptian Thanaweya Amma (Science)",
                "high_school_percentage": 85,
                "student_group": "other_states",
                "budget": 5000,
                "interests": ["logistics"],
                "preferred_city": "El Alamein",
                "track_type": "regular",
                "max_results": 1,
            },
        ),
        (
            "unknown_fee",
            {
                "certificate_type": "Egyptian Thanaweya Amma (Science)",
                "high_school_percentage": 85,
                "student_group": "other_states",
                "budget": 7000,
                "interests": ["engineering"],
                "preferred_city": "New Alamein",
                "track_type": "regular",
                "max_results": 1,
            },
        ),
    ]

    for name, payload in cases:
        response = client.post("/api/v1/decisions/recommend", json=payload)
        response.raise_for_status()
        body = response.json()
        assert body["recommendations"], f"{name}: expected at least one recommendation"
        top = body["recommendations"][0]
        print(
            json.dumps(
                {
                    "case": name,
                    "program_id": top["program_id"],
                    "score": top["score"],
                    "estimated_semester_fee": top["estimated_semester_fee"],
                    "tuition_unavailable": top["tuition_unavailable"],
                    "warnings": top["warnings"][:3],
                },
                indent=2,
            )
        )


def main() -> int:
    run_command([sys.executable, "-m", "alembic", "upgrade", "head"])
    run_command([sys.executable, "-m", "pytest", "-q"])
    run_command([sys.executable, "scripts/audit_decision_db_integrity.py", "--format", "text"])
    run_smoke_checks()
    print("Delivery checks completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
