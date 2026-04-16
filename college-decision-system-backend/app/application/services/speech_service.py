import os
import json
import logging
from typing import Optional

import imageio_ffmpeg
import shutil
import subprocess

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
if not os.path.exists(local_ffmpeg):
    shutil.copy(ffmpeg_exe, local_ffmpeg)

import whisper
import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.config.settings import settings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY.get_secret_value())

class ExtractedProfile(BaseModel):
    intent: str
    reply_message: Optional[str] = None
    student_gpa: Optional[float] = None
    interested_majors: list[str] = []
    preferred_location: Optional[str] = None
    constraints: Optional[str] = None

class SpeechService:
    def __init__(self):
        self._model = None
        self.llm_model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=(
                "You are an expert in information extraction and intention classification. "
                "You will receive a transcript of a student talking. "
                "First, determine the Intent:\n"
                "- 'greeting': If the user is just saying hello, asking how you are, etc.\n"
                "- 'data_entry': If the user is providing scores, majors, or asking for a recommendation.\n"
                "- 'irrelevant': If the user says something totally unrelated.\n\n"
                "Then, extract the following into a JSON object strictly:\n"
                "1. 'intent': (string) 'greeting', 'data_entry', or 'irrelevant'.\n"
                "2. 'reply_message': (string) If intent is 'greeting', output 'أهلاً بك! أنا مساعد الأكاديمية الذكي، قولي حابب تدرس إيه أو مجموعك كام عشان أساعدك؟'. "
                "If intent is 'irrelevant', output 'عفواً، لم أفهم طلبك. هل تود الاستفسار عن الكليات المتاحة؟'. "
                "If intent is 'data_entry', make this null.\n"
                "3. 'student_gpa': (float) try to parse it if they say 'three point eight' -> 3.8. "
                "4. 'interested_majors': (list of strings) e.g. ['computer science', 'engineering']. "
                "5. 'preferred_location': (string) like a city or region. "
                "6. 'constraints': (string) any other constraints like budget or preferences. "
                "If information is missing, use null or empty lists."
            ),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )

    @property
    def whisper_model(self):
        if self._model is None:
            logger.info("Loading Whisper base model...")
            self._model = whisper.load_model("base")
        return self._model

    def transcribe_audio(self, file_path: str) -> str:
        logger.info(f"Transcribing {file_path}")
        
        # Convert to 16kHz mono wav
        wav_path = file_path + ".wav"
        try:
            # Using direct subprocess to avoid pydub's dependency on ffprobe
            subprocess.run([
                ffmpeg_exe, "-y", "-i", file_path, 
                "-ar", "16000", "-ac", "1", wav_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Converted audio specifically for Whisper: {wav_path}")
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            wav_path = file_path # Fallback to original
            
        result = self.whisper_model.transcribe(wav_path)
        text = result.get("text", "").strip()
        logger.info(f"Transcription result: {text}")
        
        # Cleanup temp wav
        if wav_path != file_path and os.path.exists(wav_path):
            os.remove(wav_path)
            
        return text

    def extract_profile(self, text: str) -> ExtractedProfile:
        if not text:
            raise ValueError("No text provided for extraction, audio might be unclear or empty.")
            
        logger.info("Extracting profile using Gemini")
        response = self.llm_model.generate_content(text)
        try:
            data = json.loads(response.text)
            profile = ExtractedProfile(**data)
            
            # Simple validation on GPA
            if profile.student_gpa is not None:
                if profile.student_gpa < 0 or profile.student_gpa > 100:
                     logger.warning(f"Unusual GPA extracted: {profile.student_gpa}")
                     
            return profile
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse Gemini response: {response.text}")
            raise ValueError(f"Could not extract valid profile: {e}")
