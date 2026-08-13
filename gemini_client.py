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

def is_configured():
    """Cek apakah Gemini API Key sudah diset."""
    return bool(GEMINI_API_KEY) and GEMINI_API_KEY != "your_gemini_api_key_here"

def parse_filename_with_ai(filename):
    """
    Menggunakan Gemini untuk mem-parsing nama file musik.
    
    Args:
        filename (str): Nama file musik (contoh: "01. Hindiya - Kita ke dana (official audio).mp3")
        
    Returns:
        dict: Metadata hasil AI (artist, title, album, genre) atau None jika gagal.
    """
    if not is_configured():
        return None
        
    try:
        # Inisiasi Client dengan API Key
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_instruction = (
            "Kamu adalah asisten metadata musik profesional. "
            "Tugasmu adalah menganalisis nama file musik yang berantakan, membersihkannya dari kata-kata sampah, "
            "lalu menebak Artist, Title, Album, dan Genre dari lagu tersebut.\n"
            "Perbaiki typo atau salah eja jika kamu tahu lagu aslinya (misal: 'Hindiya - Kita ke dana' menjadi 'Hindia - Kita ke sana').\n"
            "Keluarkan output HANYA dalam format JSON dengan key berikut: 'artist', 'title', 'album', 'genre'. "
            "Gunakan string kosong ('') jika kamu tidak bisa menebak album atau genre-nya. "
            "Jangan tambahkan teks markdown seperti ```json di awal atau akhir, langsung JSON murni."
        )
        
        # Konfigurasi parameter menggunakan SDK yang baru
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
            response_mime_type="application/json"
        )
        
        prompt = f"Analisis nama file ini: '{filename}'"
        
        # Model default terbaru Google untuk text processing
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )
        
        text_output = response.text.strip()
        
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
