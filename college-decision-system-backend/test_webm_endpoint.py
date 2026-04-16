import os
import json
import subprocess
from gtts import gTTS
from fastapi.testclient import TestClient
from app.main import app

import imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

print("1. Generating MP3 with gTTS...")
text = "My name is Amina. I have a 3.8 GPA in high school. I am very interested in studying computer science. I prefer to study in Cairo. I have no budget constraints."
tts = gTTS(text, lang='en')
tts.save("test_student.mp3")

print("2. Converting MP3 to WEBM (Simulating browser MediaRecorder)...")
subprocess.run([ffmpeg_exe, "-y", "-i", "test_student.mp3", "-c:v", "libvpx", "-c:a", "libvorbis", "test_student.webm"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if not os.path.exists("test_student.webm"):
    # Fallback if vorbis implies issue, try simple copy or opus
    subprocess.run([ffmpeg_exe, "-y", "-i", "test_student.mp3", "test_student.webm"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


print("3. Testing /api/v1/voice-entry with test_student.webm using TestClient...")
client = TestClient(app)

with open("test_student.webm", "rb") as f:
    response = client.post("/api/v1/voice-entry", files={"file": ("test_student.webm", f, "audio/webm")})

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS: 200 OK received for .webm file!")
else:
    print("FAILED: Endpoint returned an error.")
    print(response.text)

try:
    data = response.json()
    print("Response JSON snippet:")
    print(json.dumps(data, indent=2)[:500] + "...")
except:
    pass

# Cleanup
for f in ["test_student.mp3", "test_student.webm", "temp_test_student.webm", "temp_test_student.webm.wav"]:
    if os.path.exists(f):
         try:
             os.remove(f)
         except:
             pass
