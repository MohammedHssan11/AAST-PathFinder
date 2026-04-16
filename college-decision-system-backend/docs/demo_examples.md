# Demo Examples

These examples were captured from the active Phase 5/6 system against the current `dev.db` after `alembic upgrade head`. Exact scores can change if the database is re-ingested, but the examples reflect the real response contract and the current runtime behavior.

## 1. AI-focused student

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 5000,
  "interests": ["AI"],
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CCIT_ABUKIR__ARTIFICIAL_INTELLIGENCE",
  "program_name": "Artificial Intelligence",
  "college_name": "College of Computing and Information Technology",
  "score": 77.12,
  "estimated_semester_fee": 5165.0,
  "fee_match_level": "program",
  "fee_match_source": "program_inferred",
  "tuition_unavailable": false,
  "affordability_label": "stretch",
  "training_intensity": "high",
  "matched_interests": ["AI"]
}
```

## 2. Business-focused student

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 3000,
  "interests": ["business"],
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CITL_ABUKIR__LOGISTICS_AND_SUPPLY_CHAIN_MANAGEMENT_DEPARTMENT",
  "program_name": "Logistics and Supply Chain Management Department",
  "college_name": "College of International Transport and Logistics",
  "score": 63.19,
  "estimated_semester_fee": 4985.0,
  "affordability_label": "not_affordable",
  "training_intensity": "high",
  "matched_interests": ["business"],
  "warnings": [
    "Training intensity was derived from partial data and blended with neutral defaults.",
    "Recommendation confidence was reduced because decision data was incomplete."
  ]
}
```

## 3. Engineering-focused student

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 7000,
  "interests": ["engineering"],
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CCIT_HELIOPOLIS__SOFTWARE_ENGINEERING",
  "program_name": "Software Engineering",
  "college_name": "College of Computing and Information Technology",
  "score": 83.02,
  "estimated_semester_fee": 5165.0,
  "affordability_label": "affordable",
  "training_intensity": "high",
  "matched_interests": ["engineering"]
}
```

## 4. Budget-sensitive case

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 2200,
  "interests": ["business"],
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CITL_ABUKIR__LOGISTICS_AND_SUPPLY_CHAIN_MANAGEMENT_DEPARTMENT",
  "estimated_semester_fee": 4985.0,
  "affordability_label": "not_affordable",
  "score": 63.19
}
```

## 5. Unknown-fee case

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 7000,
  "interests": ["engineering"],
  "preferred_city": "New Alamein",
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CET_ALAMEIN__COMPUTER_ENGINEERING",
  "program_name": "Computer Engineering",
  "college_name": "College of Engineering & Technology Alamein",
  "score": 62.7,
  "estimated_semester_fee": null,
  "fee_match_level": "none",
  "fee_match_source": null,
  "tuition_unavailable": true,
  "affordability_label": "unknown",
  "warnings": [
    "No confident fee item matched this program, and no conservative college-level fallback was available.",
    "Fee-category rule carries data-quality status source_indicates_single_cutoff_only."
  ]
}
```

## 6. Incomplete-data warning case

Request:

```json
{
  "certificate_type": "Egyptian Thanaweya Amma (Science)",
  "high_school_percentage": 85,
  "student_group": "other_states",
  "budget": 5000,
  "interests": ["logistics"],
  "preferred_city": "El Alamein",
  "track_type": "regular",
  "max_results": 1
}
```

Response excerpt:

```json
{
  "program_id": "CITL_EL_ALAMEIN__LOGISTICS_AND_SUPPLY_CHAIN_MANAGEMENT",
  "program_name": "Logistics and Supply Chain Management",
  "score": 85.92,
  "estimated_semester_fee": 4985.0,
  "fee_match_level": "college",
  "fee_match_source": "college_fallback",
  "training_intensity": "medium",
  "decision_data_completeness": {
    "has_profile": true,
    "has_training_data": false,
    "has_employment_data": true,
    "has_admission_data": true,
    "completeness_score": 75.0
  },
  "warnings": [
    "Used a college-level fallback because no confident program-level fee item was available.",
    "Training and practice metadata was missing, so training intensity is reported conservatively.",
    "Recommendation confidence was reduced because decision data was incomplete."
  ]
}
```
