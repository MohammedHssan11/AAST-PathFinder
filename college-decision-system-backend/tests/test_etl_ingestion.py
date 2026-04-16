import pytest
from pydantic import ValidationError
from app.api.v1.schemas.normalization import BaseNormalization
from app.application.services.ingestion_service import IngestionService, IngestionIntegrityReport

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    from app.infrastructure.db.session import Base
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_ingestion_pre_flight_report_catches_invalid_json():
    # Arrange
    invalid_data = {
        "entity": {
            # Invalid because entity_type is required to be "college" but missing here won't trigger if it has a default,
            # so we trigger by removing official_data entirely.
            "college_id": "aaast_smart_village"
        }
    }
    
    # Act / Assert
    with pytest.raises(ValidationError):
        BaseNormalization.model_validate(invalid_data)

def test_ingestion_pre_flight_counts_missing_tuition(db_session):
    # Arrange
    valid_data_missing_tuition = {
        "schema_version": "v2",
        "entity": {
            "entity_type": "college",
            "college_id": "test_college",
            "college_name": "Test University"
        },
        "official_data": {
            "degrees_programs": {
                "undergraduate": [
                    {
                        "program_base_id": "cs",
                        "program_name": "Computer Science",
                        "tuition": [] # Missing tuition!
                    },
                    {
                        "program_base_id": "eng",
                        "program_name": "Engineering",
                        "tuition": [{"group": "egyptian", "track": "regular"}]
                    }
                ]
            }
        }
    }
    
    # Act
    service = IngestionService(db_session)
    report = service.pre_flight_check(valid_data_missing_tuition)
    
    # Assert
    assert report.total_programs == 2
    assert report.valid_programs == 2
    assert report.programs_missing_tuition == 1 # The CS program
