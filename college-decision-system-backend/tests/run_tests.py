import subprocess
with open('test_out9.txt', 'w', encoding='utf-8') as f:
    subprocess.run(['pytest', '-sv', 'tests/test_recommendation_endpoint.py::test_recommend_engineering_case_returns_engineering_programs'], stdout=f, stderr=f)
