"""
Gemini AI Client untuk Hyo Music Filter.
Berfungsi sebagai 'Otak' untuk mem-parsing nama file kotor, memperbaiki typo,
dan mengembalikan tebakan Artist, Title, Album, dan Genre yang sangat akurat.
"""

import os
import json
from google import genai
from google.genai import types

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Flag inisialisasi agar tidak berulang
_IS_SETUP = False
_CLIENT = None

def is_configured():
    """Cek apakah Gemini API Key sudah diset."""
    return bool(GEMINI_API_KEY) and GEMINI_API_KEY != "your_gemini_api_key_here"

def _get_client():
    global _IS_SETUP, _CLIENT
    if not _IS_SETUP:
        _CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        _IS_SETUP = True
    return _CLIENT

def parse_filename_with_ai(filename):
    """
    Menggunakan Gemini untuk mem-parsing nama file musik (dengan kemampuan Google Search).
    """
    if not is_configured():
        return None
        
    try:
        client = _get_client()
        
        system_instruction = (
            "Kamu adalah asisten pakar metadata musik. "
            "Tugasmu adalah menganalisis nama file musik yang berantakan dan menemukan Artist, Title, Album, dan Genre aslinya.\n"
            "Gunakan GOOGLE SEARCH untuk memvalidasi nama file tersebut di internet jika kamu ragu! Cari liriknya atau info lagunya agar akurat.\n"
            "Perbaiki typo atau salah eja (misal: 'Hindiya - Kita ke dana' menjadi 'Hindia - Kita ke sana', atau 'dongker - di bandung' menjadi judul yang benar jika memang beda).\n"
            "Keluarkan output HANYA dalam format JSON dengan key berikut: 'artist', 'title', 'album', 'genre'. "
            "Gunakan string kosong ('') jika kamu tidak bisa menemukan album atau genre-nya. "
            "Jangan tambahkan markdown seperti ```json, cukup JSON murni."
        )
        
        # Konfigurasi tools pencarian
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            tools=[{"google_search": {}}] # MENGAKTIFKAN GOOGLE SEARCH!
        )
        
        prompt = f"Analisis dan cari fakta tentang nama file musik ini: '{filename}'. Berikan output JSON murni."
        
        # Gunakan gemini-2.5-flash yang support JSON dan tools terbaru
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        
        text_output = response.text.strip()
        
        # Bersihkan jika Gemini membandel dan memberi markdown
        if text_output.startswith("```json"):
            text_output = text_output.replace("```json", "").replace("```", "").strip()
        elif text_output.startswith("```"):
            text_output = text_output.replace("```", "").strip()
            
        # Parse JSON
        data = json.loads(text_output)
        
        # Validasi output dasar
        artist = data.get("artist", "").strip()
        title = data.get("title", "").strip()
        
        if not artist or not title:
            return None
            
        return {
            "artist": artist,
            "title": title,
            "album": data.get("album", "").strip(),
            "genre": data.get("genre", "").strip()
        }
        
    except Exception as e:
        print(f"[Gemini] Error mem-parsing '{filename}': {e}")
        return None
