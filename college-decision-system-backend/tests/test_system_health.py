import pytest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.session import Base
from app.infrastructure.db.models.decision_college import DecisionCollegeModel
from app.infrastructure.db.models.decision_program import DecisionProgramModel
from app.infrastructure.db.models.decision_fee import (
    DecisionFeeItemModel,
    DecisionFeeAmountModel,
    DecisionFeeCategoryRuleModel,
    DecisionFeeRuleCollegeModel,
    DecisionFeeRuleThresholdModel,
)
from app.api.v1.schemas.decision import RecommendProgramsRequestSchema
from app.api.v1.routers.decisions import recommend_programs


@pytest.fixture
def db_session_integration(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Mock the router db SessionLocal
    class MockSessionLocal:
        def __init__(self):
            pass
        def __new__(cls):
            return session

    monkeypatch.setattr("app.api.v1.routers.decisions.SessionLocal", MockSessionLocal)
    
    # Pre-seed minimal DB Data for test
    college1 = DecisionCollegeModel(
        id="college_alex", schema_version="v2", entity_type="college",
        college_name="Alexandria Tech", city="Alexandria", branch="Main"
    )
    college2 = DecisionCollegeModel(
        id="college_cairo", schema_version="v2", entity_type="college",
        college_name="Cairo Institute", city="Cairo", branch="Downtown"
    )
    session.add_all([college1, college2])
    
    prog1 = DecisionProgramModel(
        id="prog1", college_id="college_alex", program_name="AI Engineering",
        program_family="Engineering"
    )
    prog2 = DecisionProgramModel(
        id="prog2", college_id="college_cairo", program_name="Software Eng",
        program_family="Engineering"
    )
    prog3 = DecisionProgramModel(
        id="prog3", college_id="college_cairo", program_name="Cybersecurity",
        program_family="Computing"
    )
    session.add_all([prog1, prog2, prog3])
    
    fee_item1 = DecisionFeeItemModel(
        fee_id="fee_1", academic_year="2024", currency="USD", fee_mode="per_semester",
        branch_scope="all", college_id_raw="college_alex", track_type="regular",
        source_college_match_id="college_alex", source_program_match_id="prog1"
    )
    fee_item2 = DecisionFeeItemModel(
        fee_id="fee_2", academic_year="2024", currency="USD", fee_mode="per_semester",
        branch_scope="all", college_id_raw="college_cairo", track_type="regular",
        source_college_match_id="college_cairo", source_program_match_id="prog2"
    )
    fee_item3 = DecisionFeeItemModel(
        fee_id="fee_3", academic_year="2024", currency="USD", fee_mode="per_semester",
        branch_scope="all", college_id_raw="college_cairo", track_type="regular",
        source_college_match_id="college_cairo", source_program_match_id="prog3"
    )
    session.add_all([fee_item1, fee_item2, fee_item3])
    session.flush() # flush to get IDs

    fee_amt1 = DecisionFeeAmountModel(
        fee_item_id=fee_item1.id, student_group="other_states",
        fee_category="A", amount_usd=Decimal("1000.0")
    )
    fee_amt2 = DecisionFeeAmountModel(
        fee_item_id=fee_item2.id, student_group="other_states",
        fee_category="A", amount_usd=Decimal("1100.0") # Stretch
    )
    fee_amt3 = DecisionFeeAmountModel(
        fee_item_id=fee_item3.id, student_group="other_states",
        fee_category="A", amount_usd=Decimal("2000.0") # Alternative
    )
    # Manually append relationships so SQLAlchemy caching in SQLite works properly.
    fee_item1.amounts.append(fee_amt1)
    fee_item2.amounts.append(fee_amt2)
    fee_item3.amounts.append(fee_amt3)

    session.add_all([fee_amt1, fee_amt2, fee_amt3])
    # We need to map the student's certificate to Fee Category A
    rule = DecisionFeeCategoryRuleModel(
        rule_id="rule_A", certificate_type="egyptian_secondary_or_nile_or_stem_or_azhar",
        branch_scope="all", student_group="other_states"
    )
    session.add(rule)
    session.flush()

    rule_col1 = DecisionFeeRuleCollegeModel(fee_rule_id=rule.id, college_id_raw="college_alex", source_college_match_id="college_alex")
    rule_col2 = DecisionFeeRuleCollegeModel(fee_rule_id=rule.id, college_id_raw="college_cairo", source_college_match_id="college_cairo")
    
    threshold = DecisionFeeRuleThresholdModel(
        fee_rule_id=rule.id, fee_category="A", min_percent=Decimal("50.0"), max_percent_exclusive=Decimal("101.0")
    )
    
    session.add_all([rule_col1, rule_col2, threshold])
    
    session.commit()
    session.expunge_all() # Ensure fresh pull from DB for the API requests

    yield session
    session.close()


def test_system_health_e2e(db_session_integration):
    print()
    for item in db_session_integration.query(DecisionFeeItemModel).all():
        print(f"Item: {item.fee_id}, Prog: {item.source_program_match_id}, Amounts: {[a.amount_usd for a in item.amounts]}")
        for amt in item.amounts:
            print(f" -> Amt: group={amt.student_group}, cat={amt.fee_category}, usd={amt.amount_usd}")

    # User strictly requests Alexandria with a budget of 1000. 
    # But min_results=3 should force relaxation to Cairo programs as well.
    request = RecommendProgramsRequestSchema(
        certificate_type="Egyptian Thanaweya Amma (Science)",
        high_school_percentage=90.0,
        student_group="other_states",
        preferred_city="Alexandria",
        budget=1000.0,
        min_results=3,
        interests=["Engineering", "Computing"]
    )
    
    response = recommend_programs(request)
    
    # Assert Constraint Relaxation worked (pulled Cairo programs due to < 3 results in Alex)
    assert len(response.recommendations) == 3
    
    # Assert Top Match (Exact match in Alexandria for 1000)
    exact_match = next(r for r in response.recommendations if r.program_name == "AI Engineering")
    assert exact_match.match_type == "Exact"
    
    # Assert Stretch / Partial Match (Cairo is relaxed location. 1100 is Stretch budget!)
    # stretch + location miss means it should map to Partial or Stretch based on precedence (Stretch won't override Partial or vice versa, logic prioritizes Partial if missed location)
    stretch_match = next(r for r in response.recommendations if r.program_name == "Software Eng")
    assert stretch_match.match_type in ["Partial", "Stretch"] # location relaxed = Partial
    
    # Assert Alternative Match (2000 budget is fully failed)
    print([(r.program_name, r.match_type, r.estimated_semester_fee, r.fee_resolution_note, r.fee_resolution_reason) for r in response.recommendations])
    alt_match = next(r for r in response.recommendations if r.program_name == "Cybersecurity")
    assert alt_match.match_type == "Alternative"
