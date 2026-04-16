import os
import json
from gtts import gTTS
from fastapi.testclient import TestClient
from app.main import app

# 1. Generate Audio File
text = "My name is Amina. I got a 3.8 GPA in high school. I am very interested in studying computer science and software engineering. I prefer to study in Cairo, and I do not have a specific budget constraint."
print(f"Generating audio for text: '{text}'")
tts = gTTS(text, lang='en')
test_audio_path = "test_student.mp3"
tts.save(test_audio_path)
print(f"Audio saved to {test_audio_path}")

# 2. Test Endpoint
print("Testing /api/v1/voice-entry using TestClient...")
client = TestClient(app)

with open(test_audio_path, "rb") as f:
    response = client.post("/api/v1/voice-entry", files={"file": ("test_student.mp3", f, "audio/mpeg")})

print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print("Response JSON:")
    print(json.dumps(data, indent=2))
    
    # Save the result as an Artifact manually (for proof of work)
    with open(r"C:\Users\mh978\.gemini\antigravity\brain\bcba6c9b-444e-4567-a3ad-5fa0d474521c\test_execution_result.json", "w") as out:
        json.dumps(data, out, indent=2)
except Exception as e:
    print("Could not parse JSON:", response.text)

# Cleanup
if os.path.exists(test_audio_path):
    os.remove(test_audio_path)
