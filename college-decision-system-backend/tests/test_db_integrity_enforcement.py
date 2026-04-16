import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.session import SessionLocal, Base, engine
from app.infrastructure.db.models.decision_program import DecisionProgramModel


@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_sqlite_foreign_key_integrity_blocks_orphans(setup_database):
    db = SessionLocal()
    
    orphan_program = DecisionProgramModel(
        id="TEST_ORPHAN_PROGRAM_001",
        college_id="NON_EXISTENT_COLLEGE_ID",
        program_name="Test Orphan Program"
    )

    db.add(orphan_program)
    
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()

    db.rollback()
    
    # Assert the error specifies FOREIGN KEY constraint failure (SQLITE constraint)
    assert "FOREIGN KEY constraint failed" in str(exc_info.value)
