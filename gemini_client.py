"""
Gemini AI Client untuk Hyo Music Filter.
Berfungsi sebagai 'Otak' untuk mem-parsing nama file kotor, memperbaiki typo,
dan mengembalikan tebakan Artist, Title, Album, dan Genre yang sangat akurat.
"""

import os
import json

# Gunakan library google.generativeai yang lama sementara karena lebih stabil di environment ini
import google.generativeai as genai

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Flag inisialisasi agar tidak berulang
_IS_SETUP = False

def is_configured():
    """Cek apakah Gemini API Key sudah diset."""
    return bool(GEMINI_API_KEY) and GEMINI_API_KEY != "your_gemini_api_key_here"

def _setup_model():
    global _IS_SETUP
    if not _IS_SETUP:
        genai.configure(api_key=GEMINI_API_KEY)
        _IS_SETUP = True
        
    system_instruction = (
        "Kamu adalah asisten pakar metadata musik. "
        "Tugasmu adalah menganalisis nama file musik yang berantakan dan menemukan Artist, Title, Album, dan Genre aslinya.\n"
        "Perbaiki typo atau salah eja (misal: 'Hindiya - Kita ke dana' menjadi 'Hindia - Kita ke sana', atau 'dongker - di bandung' menjadi judul yang benar jika memang beda).\n"
        "Keluarkan output HANYA dalam format JSON dengan key berikut: 'artist', 'title', 'album', 'genre'. "
        "Gunakan string kosong ('') jika kamu tidak bisa menemukan album atau genre-nya. "
        "Jangan tambahkan markdown seperti ```json, cukup JSON murni."
    )
    
    # Gunakan gemini-1.5-pro karena ini yang memiliki fitur GOOGLE SEARCH GROUNDING secara default di API v1beta
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=system_instruction,
        tools="google_search_retrieval", # MENGAKTIFKAN GOOGLE SEARCH!
        generation_config={
            "temperature": 0.1,
        }
    )
    return model

def parse_filename_with_ai(filename):
    """
    Menggunakan Gemini untuk mem-parsing nama file musik (dengan kemampuan Google Search).
    """
    if not is_configured():
        return None
        
    try:
        model = _setup_model()
        prompt = f"Analisis dan cari fakta tentang nama file musik ini: '{filename}'. Berikan output JSON murni."
        
        response = model.generate_content(prompt)
        text_output = response.text.strip()
        
        # Bersihkan jika Gemini membandel dan memberi markdown
        if text_output.startswith("```json"):
            text_output = text_output.replace("```json", "").replace("```", "").strip()
        
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
