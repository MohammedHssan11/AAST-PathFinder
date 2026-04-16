import subprocess
with open('test_out_all.txt', 'w', encoding='utf-8') as f:
    res = subprocess.run(['pytest', 'tests/test_recommendation_endpoint.py', 'tests/test_fee_system_hardening.py'], stdout=f, stderr=f)
    print("EXIT CODE:", res.returncode)
