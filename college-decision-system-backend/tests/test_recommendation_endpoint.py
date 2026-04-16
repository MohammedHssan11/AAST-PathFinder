from fastapi.testclient import TestClient
from sqlalchemy import event

from app.infrastructure.db.session import engine
from app.main import app


def _build_payload(*, interest: str, budget: float, certificate_type: str = "Egyptian Thanaweya Amma (Science)") -> dict[str, object]:
    return {
        "certificate_type": certificate_type,
        "high_school_percentage": 85,
        "student_group": "other_states",
        "budget": budget,
        "interests": [interest],
        "track_type": "regular",
        "max_results": 5,
    }


def _assert_recommendation_contract(item: dict[str, object]) -> None:
    for field_name in (
        "program_id",
        "program_name",
        "college_name",
        "score",
        "training_intensity",
        "estimated_semester_fee",
        "currency",
        "fee_details",
        "fee_category_confidence",
        "decision_data_completeness",
    ):
        assert field_name in item

    assert item["score"] == item["recommendation_score"]
    assert item["training_intensity"] == item["derived_training_intensity_label"]
    assert item["fee_match_level"] in {"program", "college", "none"}
    assert item["fee_match_source"] in {"program_direct", "program_inferred", "college_fallback", None}
    assert isinstance(item["score_breakdown"], dict)
    assert isinstance(item["fee_details"], dict)
    assert isinstance(item["decision_data_completeness"], dict)


def test_recommend_ai_case_is_stable_and_returns_ai_first() -> None:
    client = TestClient(app)
    payload = _build_payload(interest="AI", budget=5000)

    first_response = client.post("/api/v1/decisions/recommend", json=payload)
    second_response = client.post("/api/v1/decisions/recommend", json=payload)

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text

    first_body = first_response.json()
    second_body = second_response.json()

    assert first_body == second_body
    assert first_body["recommendations"]
    assert "artificial intelligence" in first_body["recommendations"][0]["program_name"].lower()

    for item in first_body["recommendations"]:
        _assert_recommendation_contract(item)
        assert item["estimated_semester_fee"] is not None
        assert item["currency"] == "USD"


def test_recommend_business_case_returns_ranked_budget_aware_results() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/decisions/recommend",
        json=_build_payload(interest="business", budget=3000),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    recommendations = payload["recommendations"]

    assert recommendations
    assert any(
        keyword in item["program_name"].lower()
        for item in recommendations
        for keyword in ("business", "management", "logistics")
    )
    assert any(item["estimated_semester_fee"] is not None for item in recommendations)

    scores = [item["score"] for item in recommendations]
    assert scores == sorted(scores, reverse=True)


def test_recommend_engineering_case_returns_engineering_programs() -> None:
    client = TestClient(app)
    payload = _build_payload(interest="engineering", budget=7000, certificate_type="Egyptian Thanaweya Amma (Math)")
    payload["max_results"] = 25
    response = client.post(
        "/api/v1/decisions/recommend",
        json=payload,
    )

    assert response.status_code == 200, response.text
    recommendations = response.json()["recommendations"]

    assert any(
        "engineering" in item["program_name"].lower()
        or "engineering" in item["college_name"].lower()
        for item in recommendations
    )
    assert all(item["estimated_semester_fee"] is not None for item in recommendations)


def test_legacy_cutover_endpoints_are_removed() -> None:
    client = TestClient(app)

    assert client.get("/api/v1/programs/").status_code == 404
    assert (
        client.post(
            "/api/v1/decisions/evaluate",
            json={
                "student_id": "1",
                "program_id": "1",
                "program_fee_category": "medium",
                "training_intensity": 4,
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/decisions/explain",
            json={
                "decision": {
                    "program_id": "1",
                    "decision": "accept",
                    "final_score": 0.9,
                    "failed_rules": [],
                    "score_breakdown": {},
                    "risks": {},
                }
            },
        ).status_code
        == 404
    )


def test_recommend_endpoint_avoids_n_plus_one_queries() -> None:
    client = TestClient(app)
    executed_queries: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        executed_queries.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.post(
            "/api/v1/decisions/recommend",
            json=_build_payload(interest="AI", budget=5000),
        )
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200, response.text
    assert len(executed_queries) <= 12
