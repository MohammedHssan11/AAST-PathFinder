from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.routers import decisions as decisions_router
from app.infrastructure.db.models.decision_college import (
    DecisionAcceptedCertificateModel,
    DecisionAdmissionRequirementModel,
    DecisionCollegeLevelProfileModel,
    DecisionCollegeModel,
    DecisionTrainingAndPracticeModel,
)
from app.infrastructure.db.models.decision_fee import (
    DecisionFeeAmountModel,
    DecisionFeeCategoryRuleModel,
    DecisionFeeItemModel,
    DecisionFeeRuleCollegeModel,
    DecisionFeeRuleThresholdModel,
)
from app.infrastructure.db.models.decision_program import (
    DecisionEmploymentOutlookModel,
    DecisionProgramDecisionProfileModel,
    DecisionProgramModel,
)
from app.infrastructure.db.session import Base, configure_sqlite_connection_pragmas
from app.main import app


def _seed_college(
    session: Session,
    *,
    college_id: str,
    college_name: str,
    include_training: bool = True,
) -> None:
    session.add(
        DecisionCollegeModel(
            id=college_id,
            schema_version="1.0",
            entity_type="college",
            college_name=college_name,
            city="Alexandria",
            branch="Main Campus",
        )
    )
    session.add(
        DecisionCollegeLevelProfileModel(
            college_id=college_id,
            career_flexibility=0.62,
            egypt_employability_score=0.66,
            international_employability_score=0.61,
        )
    )
    if include_training:
        session.add(
            DecisionTrainingAndPracticeModel(
                college_id=college_id,
                mandatory_training=True,
                industry_training=True,
                field_or_sea_training=False,
            )
        )

    admission = DecisionAdmissionRequirementModel(
        college_id=college_id,
        entry_exams_required=False,
        medical_fitness_required=False,
    )
    session.add(admission)
    session.flush()
    session.add(
        DecisionAcceptedCertificateModel(
            admission_requirement_id=admission.id,
            certificate_name="Egyptian Thanaweya Amma (Science)",
            sort_order=0,
        )
    )


def _seed_program(
    session: Session,
    *,
    program_id: str,
    college_id: str,
    program_name: str,
    include_profile: bool = True,
    profile_overrides: dict[str, object] | None = None,
    include_employment: bool = True,
    employment_overrides: dict[str, object] | None = None,
) -> None:
    session.add(
        DecisionProgramModel(
            id=program_id,
            college_id=college_id,
            program_name=program_name,
            program_family=program_name.upper().replace(" ", "_"),
            degree_type="Bachelor",
            summary=f"Program summary for {program_name}.",
        )
    )

    if include_profile:
        profile_payload: dict[str, object] = {
            "program_id": program_id,
            "ai_focus": 0.9,
            "data_focus": 0.88,
            "software_focus": 0.86,
            "programming_intensity": 0.9,
            "business_focus": 0.25,
            "finance_focus": 0.25,
            "management_exposure": 0.4,
            "entrepreneurship_focus": 0.42,
            "math_intensity": 0.7,
            "physics_intensity": 0.55,
            "hardware_focus": 0.35,
            "security_focus": 0.55,
            "healthcare_focus": 0.2,
            "lab_intensity": 0.6,
            "field_work_intensity": 0.35,
            "design_creativity": 0.4,
            "creativity_design_focus": 0.38,
            "law_policy_focus": 0.3,
            "language_communication_focus": 0.45,
            "logistics_focus": 0.22,
            "maritime_focus": 0.15,
            "career_flexibility": 0.72,
        }
        profile_payload.update(profile_overrides or {})
        session.add(DecisionProgramDecisionProfileModel(**profile_payload))

    if include_employment:
        employment_payload = {
            "program_id": program_id,
            "egypt_market_score": 0.79,
            "international_market_score": 0.76,
        }
        employment_payload.update(employment_overrides or {})
        session.add(DecisionEmploymentOutlookModel(**employment_payload))


def _seed_rule(session: Session, *, rule_id: str, college_id: str) -> None:
    rule = DecisionFeeCategoryRuleModel(
        rule_id=rule_id,
        certificate_type="egyptian_secondary_or_nile_or_stem_or_azhar",
        branch_scope="all_branches_except_alamein",
        student_group="other_states",
    )
    session.add(rule)
    session.flush()
    session.add(
        DecisionFeeRuleCollegeModel(
            fee_rule_id=rule.id,
            college_id_raw=college_id,
            source_college_match_id=college_id,
            sort_order=0,
        )
    )
    session.add_all(
        [
            DecisionFeeRuleThresholdModel(
                fee_rule_id=rule.id,
                fee_category="A",
                min_percent=80,
                max_percent_exclusive=None,
            ),
            DecisionFeeRuleThresholdModel(
                fee_rule_id=rule.id,
                fee_category="B",
                min_percent=70,
                max_percent_exclusive=80,
            ),
            DecisionFeeRuleThresholdModel(
                fee_rule_id=rule.id,
                fee_category="C",
                min_percent=0,
                max_percent_exclusive=70,
            ),
        ]
    )


def _seed_program_fee(
    session: Session,
    *,
    fee_id: str,
    college_id: str,
    program_id: str,
    program_name: str,
    amount_a: float = 3500,
) -> None:
    item = DecisionFeeItemModel(
        fee_id=fee_id,
        academic_year="2025/2026",
        currency="USD",
        fee_mode="per_semester",
        branch_scope="all_branches_except_alamein",
        college_id_raw=college_id,
        college_name=college_id,
        program_name=program_name,
        track_type="regular",
        source_college_match_id=college_id,
        source_program_match_id=program_id,
    )
    session.add(item)
    session.flush()
    session.add(
        DecisionFeeAmountModel(
            fee_item_id=item.id,
            student_group="other_states",
            fee_category="A",
            amount_usd=amount_a,
        )
    )


def _seed_phase3_dataset(session: Session) -> None:
    _seed_college(session, college_id="COMPLETE_COLLEGE", college_name="Complete College")
    _seed_college(
        session,
        college_id="MISSING_TRAINING_COLLEGE",
        college_name="Missing Training College",
        include_training=False,
    )

    _seed_program(
        session,
        program_id="COMPLETE_AI",
        college_id="COMPLETE_COLLEGE",
        program_name="Applied AI Complete",
    )
    _seed_program(
        session,
        program_id="MISSING_PROFILE_AI",
        college_id="COMPLETE_COLLEGE",
        program_name="Applied AI Missing Profile",
        include_profile=False,
    )
    _seed_program(
        session,
        program_id="PARTIAL_AI",
        college_id="COMPLETE_COLLEGE",
        program_name="Applied AI Partial",
        profile_overrides={
            "data_focus": None,
            "software_focus": None,
            "programming_intensity": None,
        },
        employment_overrides={"international_market_score": None},
    )
    _seed_program(
        session,
        program_id="MALFORMED_AI",
        college_id="COMPLETE_COLLEGE",
        program_name="Applied AI Malformed",
    )
    _seed_program(
        session,
        program_id="MISSING_EMPLOYMENT_ANALYTICS",
        college_id="COMPLETE_COLLEGE",
        program_name="Missing Employment Analytics",
        include_employment=False,
    )
    _seed_program(
        session,
        program_id="MISSING_TRAINING_LOGISTICS",
        college_id="MISSING_TRAINING_COLLEGE",
        program_name="Missing Training Logistics",
    )

    _seed_rule(session, rule_id="RULE_COMPLETE_COLLEGE", college_id="COMPLETE_COLLEGE")
    _seed_rule(
        session,
        rule_id="RULE_MISSING_TRAINING_COLLEGE",
        college_id="MISSING_TRAINING_COLLEGE",
    )
    for program_id, college_id, program_name in (
        ("COMPLETE_AI", "COMPLETE_COLLEGE", "Applied AI Complete"),
        ("MISSING_PROFILE_AI", "COMPLETE_COLLEGE", "Applied AI Missing Profile"),
        ("PARTIAL_AI", "COMPLETE_COLLEGE", "Applied AI Partial"),
        ("MALFORMED_AI", "COMPLETE_COLLEGE", "Applied AI Malformed"),
        (
            "MISSING_EMPLOYMENT_ANALYTICS",
            "COMPLETE_COLLEGE",
            "Missing Employment Analytics",
        ),
        (
            "MISSING_TRAINING_LOGISTICS",
            "MISSING_TRAINING_COLLEGE",
            "Missing Training Logistics",
        ),
    ):
        _seed_program_fee(
            session,
            fee_id=f"FEE_{program_id}",
            college_id=college_id,
            program_id=program_id,
            program_name=program_name,
        )

    session.commit()
    session.execute(
        text(
            "update decision_program_decision_profiles set ai_focus = 'bad' "
            "where program_id = 'MALFORMED_AI'"
        )
    )
    session.execute(
        text(
            "update decision_employment_outlooks set egypt_market_score = 'bad' "
            "where program_id = 'MALFORMED_AI'"
        )
    )
    session.commit()


@pytest.fixture()
def decision_data_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    db_path = tmp_path / "phase3-decision-data.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    configure_sqlite_connection_pragmas(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        _seed_phase3_dataset(session)

    monkeypatch.setattr(decisions_router, "SessionLocal", TestingSessionLocal)
    client = TestClient(app)
    try:
        yield {"client": client, "engine": engine}
    finally:
        client.close()
        engine.dispose()


def _payload(*, interests: list[str], budget: float = 5000, max_results: int = 10) -> dict[str, object]:
    return {
        "certificate_type": "Egyptian Thanaweya Amma (Science)",
        "high_school_percentage": 85,
        "student_group": "other_states",
        "budget": budget,
        "interests": interests,
        "track_type": "regular",
        "max_results": max_results,
    }


def _get_program(payload: dict[str, object], program_id: str) -> dict[str, object]:
    recommendations = payload["recommendations"]
    return next(item for item in recommendations if item["program_id"] == program_id)


def test_complete_decision_data_program_reports_full_completeness(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post("/api/v1/decisions/recommend", json=_payload(interests=["AI"]))

    assert response.status_code == 200, response.text
    payload = response.json()
    first = payload["recommendations"][0]

    assert first["program_id"] == "COMPLETE_AI"
    assert first["decision_data_completeness"]["completeness_score"] == 100.0
    assert first["decision_data_completeness"]["missing_fields"] == []
    assert first["decision_data_completeness"]["warnings"] == []


def test_missing_profile_row_is_penalized_and_reported(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post("/api/v1/decisions/recommend", json=_payload(interests=["AI"]))

    assert response.status_code == 200, response.text
    payload = response.json()
    complete = _get_program(payload, "COMPLETE_AI")
    missing_profile = _get_program(payload, "MISSING_PROFILE_AI")

    assert missing_profile["decision_data_completeness"]["has_profile"] is False
    assert "decision_program_decision_profiles" in " ".join(
        missing_profile["decision_data_completeness"]["missing_fields"]
    )
    assert missing_profile["score"] < complete["score"]
    assert missing_profile["score_breakdown"]["missing_data_penalty"] > 0


def test_missing_training_row_remains_successful_and_visible(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interests=["Missing Training Logistics"]),
    )

    assert response.status_code == 200, response.text
    entry = response.json()["recommendations"][0]

    assert entry["program_id"] == "MISSING_TRAINING_LOGISTICS"
    assert entry["decision_data_completeness"]["has_training_data"] is False
    assert entry["training_intensity"] in {"medium", "high", "unknown"}
    assert "training and practice metadata was missing" in " ".join(entry["warnings"]).lower()


def test_missing_employment_row_uses_conservative_fallback(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interests=["Missing Employment Analytics"]),
    )

    assert response.status_code == 200, response.text
    entry = response.json()["recommendations"][0]

    assert entry["program_id"] == "MISSING_EMPLOYMENT_ANALYTICS"
    assert entry["decision_data_completeness"]["has_employment_data"] is False
    assert entry["score_breakdown"]["employment_outlook"] <= 70.0
    assert "college-level employability context was used" in " ".join(entry["warnings"]).lower()


def test_partial_null_numeric_fields_reduce_completeness_without_crashing(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post("/api/v1/decisions/recommend", json=_payload(interests=["AI"]))

    assert response.status_code == 200, response.text
    payload = response.json()
    complete = _get_program(payload, "COMPLETE_AI")
    partial = _get_program(payload, "PARTIAL_AI")

    assert partial["decision_data_completeness"]["completeness_score"] < 100.0
    assert partial["score"] < complete["score"]
    assert "neutral defaults for missing profile dimensions" in " ".join(partial["warnings"]).lower()


def test_malformed_numeric_value_is_ignored_safely(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    response = client.post("/api/v1/decisions/recommend", json=_payload(interests=["AI"]))

    assert response.status_code == 200, response.text
    malformed = _get_program(response.json(), "MALFORMED_AI")

    warning_text = " ".join(malformed["warnings"]).lower()
    assert "malformed numeric value" in warning_text
    assert malformed["decision_data_completeness"]["completeness_score"] < 100.0


def test_identical_requests_with_missing_data_remain_deterministic(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    payload = _payload(interests=["AI"])

    first = client.post("/api/v1/decisions/recommend", json=payload)
    second = client.post("/api/v1/decisions/recommend", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()


def test_completeness_features_do_not_add_n_plus_one_queries(
    decision_data_env: dict[str, object],
) -> None:
    client = decision_data_env["client"]
    engine = decision_data_env["engine"]
    executed_queries: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        executed_queries.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.post("/api/v1/decisions/recommend", json=_payload(interests=["AI"]))
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200, response.text
    assert len(executed_queries) <= 12
