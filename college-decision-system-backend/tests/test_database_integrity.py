from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.integrity import (
    ACTIVE_DECISION_TABLES,
    collect_decision_schema_drift,
    collect_decision_table_inventory,
    collect_duplicate_counts,
    collect_integrity_counts,
    collect_runtime_index_status,
    get_sqlite_foreign_keys_enabled,
)
from app.infrastructure.db.models.decision_college import DecisionCollegeModel
from app.infrastructure.db.models.decision_fee import (
    DecisionFeeAdditionalFeeModel,
    DecisionFeeAmountModel,
    DecisionFeeItemModel,
)
from app.infrastructure.db.models.decision_program import (
    DecisionProgramDecisionProfileModel,
    DecisionProgramModel,
)
from app.infrastructure.db.repositories.decision_fee_repo import DecisionFeeRepository
from app.infrastructure.db.session import (
    Base,
    SessionLocal,
    configure_sqlite_connection_pragmas,
    engine,
)

LEGACY_MVP_TABLES = {
    "campus_colleges",
    "campuses",
    "colleges",
    "programs",
    "students",
    "tuition_fees",
}


def test_live_sqlite_engine_enables_foreign_keys() -> None:
    with SessionLocal() as session:
        assert get_sqlite_foreign_keys_enabled(session) is True


def test_live_decision_schema_has_no_orphans_or_duplicate_key_violations() -> None:
    with SessionLocal() as session:
        integrity_counts = collect_integrity_counts(session)
        duplicate_counts = collect_duplicate_counts(session)

    assert all(value == 0 for value in integrity_counts.values()), integrity_counts
    assert all(value == 0 for value in duplicate_counts.values()), duplicate_counts


def test_live_active_decision_schema_matches_orm_and_has_critical_indexes() -> None:
    drift = collect_decision_schema_drift(engine)
    index_status = collect_runtime_index_status(engine)
    inventory = collect_decision_table_inventory(engine)

    assert drift["missing_tables_in_db"] == []
    assert drift["unexpected_decision_tables"] == []
    assert drift["column_drift"] == {}
    assert drift["missing_runtime_indexes"] == {}
    assert {item["table_name"] for item in inventory} >= set(ACTIVE_DECISION_TABLES)
    assert all(all(status.values()) for status in index_status.values()), index_status


def test_live_legacy_mvp_tables_are_removed_from_schema() -> None:
    assert LEGACY_MVP_TABLES.isdisjoint(set(inspect(engine).get_table_names()))


def test_sqlite_fk_and_uniqueness_constraints_are_enforced_in_temp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "integrity-enforcement.db"
    local_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    configure_sqlite_connection_pragmas(local_engine)
    TestingSessionLocal = sessionmaker(
        bind=local_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(local_engine)

    try:
        with TestingSessionLocal() as session:
            assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

            session.add(
                DecisionCollegeModel(
                    id="TEMP_COLLEGE",
                    schema_version="1.0",
                    entity_type="college",
                    college_name="Temporary College",
                )
            )
            session.add(
                DecisionProgramModel(
                    id="TEMP_PROGRAM",
                    college_id="TEMP_COLLEGE",
                    program_name="Temporary Program",
                )
            )
            session.add(
                DecisionProgramDecisionProfileModel(
                    program_id="TEMP_PROGRAM",
                    ai_focus=0.5,
                    data_focus=0.5,
                    software_focus=0.5,
                    programming_intensity=0.5,
                    business_focus=0.5,
                    finance_focus=0.5,
                    management_exposure=0.5,
                    entrepreneurship_focus=0.5,
                    math_intensity=0.5,
                    physics_intensity=0.5,
                    hardware_focus=0.5,
                    security_focus=0.5,
                    healthcare_focus=0.5,
                    lab_intensity=0.5,
                    field_work_intensity=0.5,
                    design_creativity=0.5,
                    creativity_design_focus=0.5,
                    law_policy_focus=0.5,
                    language_communication_focus=0.5,
                    logistics_focus=0.5,
                    maritime_focus=0.5,
                    career_flexibility=0.5,
                )
            )
            session.commit()

            session.add(
                DecisionFeeAdditionalFeeModel(
                    fee_item_id=999999,
                    fee_type="orphan_fee",
                    amount_usd=100,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                DecisionProgramDecisionProfileModel(
                    program_id="TEMP_PROGRAM",
                    ai_focus=0.4,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        local_engine.dispose()


def test_duplicate_college_fallback_fee_items_are_selected_deterministically(tmp_path: Path) -> None:
    db_path = tmp_path / "deterministic-fees.db"
    local_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    configure_sqlite_connection_pragmas(local_engine)
    TestingSessionLocal = sessionmaker(
        bind=local_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(local_engine)

    try:
        with TestingSessionLocal() as session:
            session.add(
                DecisionCollegeModel(
                    id="DETERMINISTIC_COLLEGE",
                    schema_version="1.0",
                    entity_type="college",
                    college_name="Deterministic College",
                )
            )
            session.add(
                DecisionProgramModel(
                    id="DETERMINISTIC_PROGRAM",
                    college_id="DETERMINISTIC_COLLEGE",
                    program_name="Deterministic Program",
                )
            )
            session.add_all(
                [
                    DecisionFeeItemModel(
                        fee_id="AAA_GENERIC",
                        academic_year="2025/2026",
                        currency="USD",
                        fee_mode="per_semester",
                        branch_scope="all_branches_except_alamein",
                        college_id_raw="DETERMINISTIC_COLLEGE",
                        college_name="Deterministic College",
                        program_name=None,
                        track_type="regular",
                        source_college_match_id="DETERMINISTIC_COLLEGE",
                    ),
                    DecisionFeeItemModel(
                        fee_id="ZZZ_GENERIC",
                        academic_year="2025/2026",
                        currency="USD",
                        fee_mode="per_semester",
                        branch_scope="all_branches_except_alamein",
                        college_id_raw="DETERMINISTIC_COLLEGE",
                        college_name="Deterministic College",
                        program_name=None,
                        track_type="regular",
                        source_college_match_id="DETERMINISTIC_COLLEGE",
                    ),
                ]
            )
            session.flush()

            fee_items = session.query(DecisionFeeItemModel).order_by(DecisionFeeItemModel.fee_id).all()
            session.add_all(
                [
                    DecisionFeeAmountModel(
                        fee_item_id=fee_items[0].id,
                        student_group="other_states",
                        fee_category="A",
                        amount_usd=3000,
                    ),
                    DecisionFeeAmountModel(
                        fee_item_id=fee_items[1].id,
                        student_group="other_states",
                        fee_category="A",
                        amount_usd=3200,
                    ),
                ]
            )
            session.commit()

        with TestingSessionLocal() as session:
            repo = DecisionFeeRepository(session)
            first = repo.get_effective_fee_for_program(
                program_id="DETERMINISTIC_PROGRAM",
                resolved_fee_category="A",
                student_group="other_states",
                track_type="regular",
            )
            second = repo.get_effective_fee_for_program(
                program_id="DETERMINISTIC_PROGRAM",
                resolved_fee_category="A",
                student_group="other_states",
                track_type="regular",
            )

            assert first is not None
            assert second is not None
            assert first.fee_id == "AAA_GENERIC"
            assert second.fee_id == "AAA_GENERIC"
            assert first.selection_reason == second.selection_reason
    finally:
        local_engine.dispose()
