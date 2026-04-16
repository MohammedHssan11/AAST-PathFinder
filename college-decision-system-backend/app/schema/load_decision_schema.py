import json
from pathlib import Path

from app.domain.entities.decision_schema import DecisionSchema


MASTER_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "decision_schema_v1.json"


def load_master_schema() -> DecisionSchema:
    if not MASTER_SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Master schema contract not found at '{MASTER_SCHEMA_PATH}'."
        )

    payload = json.loads(MASTER_SCHEMA_PATH.read_text(encoding="utf-8"))
    return DecisionSchema.model_validate(payload)
