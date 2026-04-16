from typing import List

from pydantic import BaseModel, ConfigDict, Field


class StudentInputSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "certificate_type": "Egyptian Thanaweya Amma (Science)",
                "stream": "science",
                "score": 85,
                "subjects": ["mathematics", "physics", "english"],
                "preferred_locations": ["Alexandria", "New Alamein"],
                "fee_category": "egyptian_secondary_or_nile_or_stem_or_azhar",
            }
        }
    )

    certificate_type: str = Field(
        description="Student certificate label as provided by the client or demo payload."
    )
    stream: str = Field(description="Academic stream or specialization.")
    score: float = Field(description="Student score or percentage value.", ge=0, le=100)
    subjects: List[str] = Field(
        default_factory=list,
        description="Subjects relevant to the student profile.",
    )
    preferred_locations: List[str] = Field(
        default_factory=list,
        description="Preferred study locations supplied by the client.",
    )
    fee_category: str = Field(
        description="Client-side fee category label used for placeholder validation."
    )
