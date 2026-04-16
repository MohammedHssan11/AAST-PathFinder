from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)
payload = {
    "certificate_type": "Egyptian Thanaweya Amma (Science)",
    "high_school_percentage": 85,
    "student_group": "other_states",
    "budget": 20000,
    "interests": ["engineering"],
    "track_type": "regular",
    "max_results": 500,
}

response = client.post("/api/v1/decisions/recommend", json=payload)
data = response.json()
if "recommendations" not in data:
    print("ERROR RESPONSE:", json.dumps(data, indent=2))
else:
    recs = data["recommendations"]
    print(f"Total returned: {len(recs)}")
    for i, r in enumerate(recs):
        if "engineering" in r["college_name"].lower() or "engineering" in r["program_name"].lower() or "cet" in r["college_id"].lower():
            print(f"Rank {i+1}: {r['score']:.2f} | {r['college_id']} - {r['program_name']}")
            print(f"   Fee: {r['estimated_semester_fee']} ({r['fee_match_level']}) | Penalty: {r['score_breakdown']['missing_data_penalty']}")
            print(f"   Tuition Unavailable: {r['fee_details'].get('tuition_unavailable', True)}")
            print(f"   Budget Valid: {r['estimated_semester_fee'] <= 7000 if r['estimated_semester_fee'] else False}")
