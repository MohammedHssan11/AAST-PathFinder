from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.routers import decisions as decisions_router
from app.infrastructure.db.models.decision_college import (
    DecisionAcceptedCertificateModel,
    DecisionAdmissionRequirementModel,
    DecisionCollegeModel,
    DecisionTrainingAndPracticeModel,
)
from app.infrastructure.db.models.decision_fee import (
    DecisionFeeAdditionalFeeModel,
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
) -> None:
    session.add(
        DecisionCollegeModel(
            id=college_id,
            schema_version="1.0",
            entity_type="college",
            college_name=college_name,
            city="Test City",
            branch="Main Campus",
        )
    )
    session.add(
        DecisionTrainingAndPracticeModel(
            college_id=college_id,
            mandatory_training=False,
            industry_training=False,
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
    ai_focus: float = 0.2,
    data_focus: float = 0.2,
    software_focus: float = 0.2,
    business_focus: float = 0.2,
    math_intensity: float = 0.4,
    physics_intensity: float = 0.3,
    career_flexibility: float = 0.5,
    egypt_market_score: float = 0.6,
    international_market_score: float = 0.6,
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
    session.add(
        DecisionProgramDecisionProfileModel(
            program_id=program_id,
            ai_focus=ai_focus,
            data_focus=data_focus,
            software_focus=software_focus,
            business_focus=business_focus,
            math_intensity=math_intensity,
            physics_intensity=physics_intensity,
            career_flexibility=career_flexibility,
            lab_intensity=0.3,
            field_work_intensity=0.1,
        )
    )
    session.add(
        DecisionEmploymentOutlookModel(
            program_id=program_id,
            egypt_market_score=egypt_market_score,
            international_market_score=international_market_score,
        )
    )


def _seed_rule(
    session: Session,
    *,
    rule_id: str,
    college_id: str,
    student_group: str | None,
) -> None:
    rule = DecisionFeeCategoryRuleModel(
        rule_id=rule_id,
        certificate_type="egyptian_secondary_or_nile_or_stem_or_azhar",
        branch_scope="all_branches_except_alamein",
        student_group=student_group,
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


def _seed_fee_item(
    session: Session,
    *,
    fee_id: str,
    college_raw: str,
    college_match_id: str,
    academic_year: str,
    track_type: str,
    program_name: str | None,
    source_program_match_id: str | None,
    amount_a: float,
    recurring_fees: list[tuple[str, float, str | None]] | None = None,
    one_time_fees: list[tuple[str, float, str | None]] | None = None,
) -> None:
    item = DecisionFeeItemModel(
        fee_id=fee_id,
        academic_year=academic_year,
        currency="USD",
        fee_mode="per_semester",
        branch_scope="all_branches_except_alamein",
        college_id_raw=college_raw,
        college_name=college_match_id,
        program_name=program_name,
        track_type=track_type,
        source_college_match_id=college_match_id,
        source_program_match_id=source_program_match_id,
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
    for fee_type, amount, note in recurring_fees or []:
        session.add(
            DecisionFeeAdditionalFeeModel(
                fee_item_id=item.id,
                fee_type=fee_type,
                amount_usd=amount,
                frequency="per_semester",
                note=note,
            )
        )
    for fee_type, amount, note in one_time_fees or []:
        session.add(
            DecisionFeeAdditionalFeeModel(
                fee_item_id=item.id,
                fee_type=fee_type,
                amount_usd=amount,
                frequency="one_time",
                note=note,
            )
        )


def _seed_fee_test_data(session: Session) -> None:
    _seed_college(session, college_id="TEST_COLLEGE_A", college_name="Test College A")
    _seed_college(session, college_id="TEST_COLLEGE_B", college_name="Test College B")

    _seed_program(
        session,
        program_id="TEST_COLLEGE_A__ROBOTICS",
        college_id="TEST_COLLEGE_A",
        program_name="Robotics",
        ai_focus=0.75,
        data_focus=0.55,
        software_focus=0.65,
        math_intensity=0.85,
        physics_intensity=0.8,
        career_flexibility=0.65,
        egypt_market_score=0.82,
        international_market_score=0.79,
    )
    _seed_program(
        session,
        program_id="TEST_COLLEGE_A__GENERAL_STUDIES",
        college_id="TEST_COLLEGE_A",
        program_name="General Studies",
        business_focus=0.55,
        math_intensity=0.3,
        physics_intensity=0.2,
        career_flexibility=0.6,
        egypt_market_score=0.55,
        international_market_score=0.5,
    )
    _seed_program(
        session,
        program_id="TEST_COLLEGE_A__DATA_SCIENCE",
        college_id="TEST_COLLEGE_A",
        program_name="Data Science",
        ai_focus=0.9,
        data_focus=0.95,
        software_focus=0.8,
        math_intensity=0.7,
        career_flexibility=0.75,
        egypt_market_score=0.78,
        international_market_score=0.76,
    )
    _seed_program(
        session,
        program_id="TEST_COLLEGE_B__UNKNOWN_FEES",
        college_id="TEST_COLLEGE_B",
        program_name="Unknown Fees",
        ai_focus=0.2,
        data_focus=0.2,
        software_focus=0.2,
        business_focus=0.2,
        math_intensity=0.25,
        physics_intensity=0.2,
        career_flexibility=0.4,
        egypt_market_score=0.35,
        international_market_score=0.3,
    )
    _seed_college(session, college_id="TEST_COLLEGE_ALAMEIN", college_name="Test College Alamein")
    _seed_program(
        session,
        program_id="TEST_COLLEGE_ALAMEIN__UNKNOWN_FEES",
        college_id="TEST_COLLEGE_ALAMEIN",
        program_name="Alamein Unknown Fees",
        ai_focus=0.2,
        data_focus=0.2,
        software_focus=0.2,
        business_focus=0.2,
        math_intensity=0.25,
        physics_intensity=0.2,
        career_flexibility=0.4,
        egypt_market_score=0.35,
        international_market_score=0.3,
    )

    _seed_rule(
        session,
        rule_id="TEST_RULE_A",
        college_id="TEST_COLLEGE_A",
        student_group="other_states",
    )
    _seed_rule(
        session,
        rule_id="TEST_RULE_B",
        college_id="TEST_COLLEGE_B",
        student_group="other_states",
    )

    _seed_fee_item(
        session,
        fee_id="ROBOTICS_2024",
        college_raw="TEST_A",
        college_match_id="TEST_COLLEGE_A",
        academic_year="2024/2025",
        track_type="regular",
        program_name="Robotics",
        source_program_match_id="TEST_COLLEGE_A__ROBOTICS",
        amount_a=3200,
        recurring_fees=[("lab_fee", 50, "legacy year")],
        one_time_fees=[("registration_fee", 200, "legacy year")],
    )
    _seed_fee_item(
        session,
        fee_id="ROBOTICS_2025",
        college_raw="TEST_A",
        college_match_id="TEST_COLLEGE_A",
        academic_year="2025/2026",
        track_type="regular",
        program_name="Robotics",
        source_program_match_id="TEST_COLLEGE_A__ROBOTICS",
        amount_a=3500,
        recurring_fees=[("lab_fee", 150, "latest year")],
        one_time_fees=[("registration_fee", 500, "latest year")],
    )
    _seed_fee_item(
        session,
        fee_id="COLLEGE_GENERIC_2025",
        college_raw="TEST_A",
        college_match_id="TEST_COLLEGE_A",
        academic_year="2025/2026",
        track_type="regular",
        program_name=None,
        source_program_match_id=None,
        amount_a=2800,
        recurring_fees=[("services_fee", 100, "college-wide recurring")],
    )
    _seed_fee_item(
        session,
        fee_id="DATA_SCIENCE_AMBIG_A",
        college_raw="TEST_A",
        college_match_id="TEST_COLLEGE_A",
        academic_year="2025/2026",
        track_type="regular",
        program_name="Data Science / Artificial Intelligence",
        source_program_match_id=None,
        amount_a=4100,
    )
    _seed_fee_item(
        session,
        fee_id="DATA_SCIENCE_AMBIG_B",
        college_raw="TEST_A",
        college_match_id="TEST_COLLEGE_A",
        academic_year="2025/2026",
        track_type="regular",
        program_name="Data Science / Machine Learning",
        source_program_match_id=None,
        amount_a=4200,
    )
    session.commit()


@pytest.fixture()
def fee_test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "fee-system.db"
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
        _seed_fee_test_data(session)

    monkeypatch.setattr(decisions_router, "SessionLocal", TestingSessionLocal)
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        engine.dispose()


def _payload(*, interest: str, budget: float | None = None) -> dict[str, object]:
    return {
        "certificate_type": "Egyptian Thanaweya Amma (Science)",
        "high_school_percentage": 85,
        "student_group": "other_states",
        "budget": budget,
        "interests": [interest],
        "track_type": "regular",
        "max_results": 4,
    }


def test_exact_program_fee_match_uses_latest_academic_year(fee_test_client: TestClient) -> None:
    response = fee_test_client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interest="Robotics", budget=5000),
    )

    assert response.status_code == 200, response.text
    first = response.json()["recommendations"][0]

    assert first["program_id"] == "TEST_COLLEGE_A__ROBOTICS"
    assert first["fee_match_level"] == "program"
    assert first["fee_match_source"] == "program_direct"
    assert first["academic_year"] == "2025/2026"
    assert first["estimated_semester_fee"] == 3650.0
    assert first["additional_one_time_fees_total"] == 500.0
    assert first["additional_one_time_fees_breakdown"][0]["fee_type"] == "registration_fee"
    assert first["fee_details"]["additional_recurring_fees_total"] == 150.0


def test_college_fallback_fee_match_is_explicit(fee_test_client: TestClient) -> None:
    response = fee_test_client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interest="General Studies", budget=4000),
    )

    assert response.status_code == 200, response.text
    first = response.json()["recommendations"][0]

    assert first["program_id"] == "TEST_COLLEGE_A__GENERAL_STUDIES"
    assert first["fee_match_level"] == "college"
    assert first["used_college_fallback"] is True
    assert first["estimated_semester_fee"] == 2900.0
    assert first["additional_one_time_fees_total"] == 0.0
    assert first["fee_details"]["warnings"]
    assert "college-level fallback" in " ".join(first["fee_details"]["warnings"]).lower()


def test_ambiguous_inferred_program_match_falls_back_conservatively(fee_test_client: TestClient) -> None:
    response = fee_test_client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interest="Data Science", budget=4500),
    )

    assert response.status_code == 200, response.text
    first = response.json()["recommendations"][0]

    assert first["program_id"] == "TEST_COLLEGE_A__DATA_SCIENCE"
    assert first["fee_match_level"] == "college"
    assert first["fee_match_source"] == "college_fallback"
    warning_text = " ".join(first["warnings"]).lower()
    assert "multiple inferred program-level fee items matched" in warning_text


def test_no_fee_match_keeps_recommendation_safe(fee_test_client: TestClient) -> None:
    payload = _payload(interest="Alamein Unknown Fees", budget=3000)
    response = fee_test_client.post(
        "/api/v1/decisions/recommend",
        json=payload,
    )

    assert response.status_code == 200, response.text
    recommendations = response.json()["recommendations"]
    unknown_fee_entry = next(
        item for item in recommendations if item["program_id"] == "TEST_COLLEGE_ALAMEIN__UNKNOWN_FEES"
    )

    assert unknown_fee_entry["fee_match_level"] == "none"
    assert unknown_fee_entry["tuition_unavailable"] is True
    assert unknown_fee_entry["estimated_semester_fee"] is None
    assert unknown_fee_entry["affordability_label"] == "unknown"


def test_branch_fallback_is_applied_when_college_is_missing(fee_test_client: TestClient) -> None:
    response = fee_test_client.post(
        "/api/v1/decisions/recommend",
        json=_payload(interest="Unknown Fees", budget=3500),
    )

    assert response.status_code == 200, response.text
    recommendations = response.json()["recommendations"]
    branch_fee_entry = next(
        item for item in recommendations if item["program_id"] == "TEST_COLLEGE_B__UNKNOWN_FEES"
    )

    assert branch_fee_entry["fee_match_level"] == "branch_fallback"
    assert branch_fee_entry["tuition_unavailable"] is False
    assert branch_fee_entry["estimated_semester_fee"] == 3620.0
    assert branch_fee_entry["score_breakdown"]["missing_data_penalty"] >= 0.15 # Minimum 15% missing branch penalty



def test_missing_student_inputs_return_unresolved_fee_category(fee_test_client: TestClient) -> None:
    payload = _payload(interest="Robotics", budget=5000)
    payload["high_school_percentage"] = None

    response = fee_test_client.post("/api/v1/decisions/recommend", json=payload)

    assert response.status_code == 200, response.text
    first = response.json()["recommendations"][0]

    assert first["fee_category"] is None
    assert first["fee_category_confidence"] == "unresolved"
    assert first["tuition_unavailable"] is True
    assert "high_school_percentage was missing" in first["fee_resolution_reason"]


def test_stable_identical_output_across_repeated_calls(fee_test_client: TestClient) -> None:
    payload = _payload(interest="Robotics", budget=5000)

    first_response = fee_test_client.post("/api/v1/decisions/recommend", json=payload)
    second_response = fee_test_client.post("/api/v1/decisions/recommend", json=payload)

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    assert first_response.json() == second_response.json()
