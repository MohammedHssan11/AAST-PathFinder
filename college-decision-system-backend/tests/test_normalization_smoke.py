import json
import shutil
from pathlib import Path

from app.domain.entities.decision_schema import DecisionSchema
from app.schema.normalize_colleges import normalize_all_colleges


def test_normalization_smoke_subset(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[2] / "colleges"
    input_dir = tmp_path / "input_colleges"
    output_dir = tmp_path / "normalized_colleges"

    input_dir.mkdir(parents=True, exist_ok=True)

    sample_files = [
        "CCIT_HELIOPOLIS.json",
        "PHARM_ABUKIR.json",
    ]

    for file_name in sample_files:
        shutil.copy2(source_root / file_name, input_dir / file_name)

    normalize_all_colleges(input_dir, output_dir)

    outputs = sorted(output_dir.glob("*.normalized.json"))
    assert len(outputs) == len(sample_files)

    for output_path in outputs:
        assert output_path.exists()
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        validated = DecisionSchema.model_validate(payload)
        assert validated.version == "decision_schema_v1"
