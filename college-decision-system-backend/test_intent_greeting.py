import os
import json
import subprocess
from gtts import gTTS
from fastapi.testclient import TestClient
from app.main import app

import imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

print("1. Generating MP3 with gTTS (Greeting Intent)...")
text = "Hello there! How represent you doing today? I just wanted to say hi!"
tts = gTTS(text, lang='en')
tts.save("test_greeting.mp3")

print("2. Converting MP3 to WEBM...")
subprocess.run([ffmpeg_exe, "-y", "-i", "test_greeting.mp3", "-c:v", "libvpx", "-c:a", "libvorbis", "test_greeting.webm"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if not os.path.exists("test_greeting.webm"):
    subprocess.run([ffmpeg_exe, "-y", "-i", "test_greeting.mp3", "test_greeting.webm"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("3. Testing /api/v1/voice-entry with test_greeting.webm using TestClient...")
client = TestClient(app)

with open("test_greeting.webm", "rb") as f:
    response = client.post("/api/v1/voice-entry", files={"file": ("test_greeting.webm", f, "audio/webm")})

print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print("Response JSON snippet:")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
except:
    print(response.text)

# Cleanup
for f in ["test_greeting.mp3", "test_greeting.webm", "temp_test_greeting.webm", "temp_test_greeting.webm.wav"]:
    if os.path.exists(f):
         try:
             os.remove(f)
         except:
             pass
