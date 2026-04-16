import httpx

url = "http://localhost:8001/api/v1/decisions/recommend"
payload = {
    "student_group": "supportive_states",
    "track_type": "regular",
    "max_results": 10,
    "min_results": 3,
    "interests": [],
    "certificate_type": "Egyptian Thanaweya Amma (Science)"
}

try:
    response = httpx.post(url, json=payload, timeout=20.0)
    print("Status:", response.status_code)
    print(response.text)
except Exception as e:
    print("Error:", str(e))
