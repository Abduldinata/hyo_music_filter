import os
import glob
import re
import json
import difflib
try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TCON, APIC, TALB, TDRC, error as id3_error
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.flac import FLAC, Picture
except ImportError:
    pass

# ==========================================
# REGEX PATTERNS (SUPERCHARGED)
# ==========================================
PATTERNS = [
    # 01 - Artist - Title (Album, 2020) [JP]
    re.compile(r"^(?P<track>\d{2,3})\s*[-.]\s*(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<album>.+?),\s*(?P<year>\d{4})\)\s*\[(?P<lang>JP|ID|ENG|KOR)\]$", re.I),
    # Artist - Album - Track - Title (year) [LANG]
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<album>.+?)\s*[-.]\s*(?P<track>\d{1,3})\s*[-.]\s*(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    # Artist - Title (feat. Guest) (Year) LANG
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*(?:\(feat\.\s*(?P<feat>.+?)\))?\s*\((?P<year>\d{4})\)\s*\[?(?P<lang>JP|ID|ENG)?\]?$", re.I),
    # Title - Artist [Album] (2020)
    re.compile(r"^(?P<title>.+?)\s*[-.]\s*(?P<artist>.+?)\s*\[(?P<album>.+?)\]\s*\((?P<year>\d{4})\)$", re.I),
    # Artist - Title (Album) [LANG]
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<album>.+?)\)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    # Sederhana: Artist - Title [LANG]
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    # Sederhana: Artist - Title (Year)
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<year>\d{4})\)$", re.I),
    # Paling sederhana yang super aman: Artist - Title
    re.compile(r"^(?P<artist>.+?)\s*[-–_]\s*(?P<title>.+?)$", re.I),
]

def clean_filename(filename):
    """Membersihkan karakter ilegal pada OS Windows untuk nama file baru."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def is_similar(str1, str2, threshold=0.75):
    """Cek apakah dua string mirip (fuzzy match)."""
    if not str1 or not str2:
        return False
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio() >= threshold

def parse_filename(filename):
    """Mengekstrak data dari nama file menggunakan daftar Regex bertingkat (Top-Down)."""
    # Ambil HANYA NAMA tanpa ekstensinya (karena regex kita sekarang berakhiran $ tanpa .mp3)
    name = os.path.splitext(os.path.basename(filename))[0]
    
    # 1. Bersihkan nama file dari tag-tag sampah SEBELUM diparse oleh Regex
    junk_words = ["official music video", "official video", "official audio", "lyric", "lyrics", "320kbps", "mp3"]
    cleaned_name = name
    
    # Buang teks di dalam kurung yang mengandung kata-kata junk
    cleaned_name = re.sub(r'\((.*?)(official|lyric|audio|video|kbps)(.*?)\)', '', cleaned_name, flags=re.IGNORECASE)
    cleaned_name = re.sub(r'\[(.*?)(official|lyric|audio|video|kbps)(.*?)\]', '', cleaned_name, flags=re.IGNORECASE)
    
    # Ganti underscore dengan spasi agar pemotong kata (word boundary \b) berfungsi
    cleaned_name = cleaned_name.replace('_', ' ')
    
    # Buang kata junk yang berdiri sendiri
    for j in junk_words:
        cleaned_name = re.sub(r'\b' + j + r'\b', "", cleaned_name, flags=re.IGNORECASE)
        
    # Rapikan spasi berlebih akibat penghapusan teks
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    cleaned_name = re.sub(r'\s+\.', '.', cleaned_name)
    
    # 2. Parse menggunakan Regex pada nama yang sudah bersih
    for pattern in PATTERNS:
        m = pattern.match(cleaned_name)
        if m:
            data = m.groupdict()
            clean = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if v is not None}
            if 'year' in clean:
                clean['year'] = int(clean['year'])
            if 'track' in clean:
                clean['track'] = int(clean['track'])
            if 'feat' in clean:
                clean['featured_artists'] = [a.strip() for a in clean.pop('feat').split(',')]
            else:
                clean['featured_artists'] = []
            return clean
            
    # FALLBACK: Jika tidak ada pola regex yang cocok
    # Asumsikan seluruh teks yang tersisa adalah Title.
    if cleaned_name and len(cleaned_name) > 2:
        return {
            "artist": "",
            "title": cleaned_name
        }
            
    # Jika gagal total
    return None

def process_file(filepath, metadata_db):
    """Memproses file secara FULL OFFLINE: Parsing, Lookup Database Lokal, ID3 Inject, Rename."""
    directory = os.path.dirname(filepath)
    raw_filename = os.path.basename(filepath)
    ext = os.path.splitext(raw_filename)[1].lower()
    
    print(f"\n[>] Memproses: '{raw_filename}'")
    
    # CEK METADATA LAMA: Jika Artist, Title, dan Cover sudah ada, lewati.
    has_title = False
    has_artist = False
    has_cover = False
    
    try:
        if ext == ".mp3":
            audio = MP3(filepath, ID3=ID3)
            if audio.tags:
                has_title = 'TIT2' in audio
                has_artist = 'TPE1' in audio
                has_cover = len(audio.tags.getall('APIC')) > 0
        elif ext == ".m4a":
            audio = MP4(filepath)
            if audio.tags:
                has_title = '\xa9nam' in audio.tags
                has_artist = '\xa9ART' in audio.tags
                has_cover = 'covr' in audio.tags
        elif ext == ".flac":
            audio = FLAC(filepath)
            if audio.tags:
                has_title = 'title' in audio.tags
                has_artist = 'artist' in audio.tags
            if audio.pictures:
                has_cover = True
    except Exception:
        pass
        
    if has_title and has_artist and has_cover:
        print("    [✅] File sudah memiliki metadata dan cover art yang lengkap. Dilewati.")
        return
    
    parsed = parse_filename(filepath)
    if not parsed:
        print("    [!] Gagal mem-parsing format penamaan. File ini dilewati.")
        return

    artist = parsed.get("artist", "Unknown Artist")
    title = parsed.get("title", "Unknown Title")
    album = parsed.get("album")
    year = parsed.get("year")
    lang = parsed.get("language")

    print(f"    [REGEX] Artis: '{artist}' | Judul: '{title}'")

    # 1. Lookup ke Database Lokal
    key = f"{artist.lower()}||{title.lower()}"
    db_meta = metadata_db.get(key)
    
    # AUTO-CORRECT TYPO
    final_artist = artist
    final_title = title
    
    if db_meta:
        genre = db_meta.get("genre")
        cover_path = db_meta.get("local_cover")
        
        # Validasi sebelum Auto-Correct
        db_artist = db_meta.get("artist")
        db_title = db_meta.get("title")
        if db_artist and is_similar(artist, db_artist): final_artist = db_artist
        if db_title and is_similar(title, db_title): final_title = db_title
        
        if not album and db_meta.get("album"):
            album = db_meta["album"]
        if not year and db_meta.get("year"):
            try: year = int(str(db_meta["year"])[:4])
            except ValueError: pass
        print(f"    [DB] Data ditemukan! Auto-correct: {final_artist} - {final_title}")
    else:
        genre = None
        cover_path = None
        print("    [DB] Data TIDAK ditemukan. Melanjutkan dengan ejaan awal.")

    # 2. Injeksi ID3 Tag (Mutagen)
    try:
        if ext == ".mp3":
            audio = MP3(filepath, ID3=ID3)
            try: audio.delete()
            except id3_error: pass
            
            audio.tags = ID3()
            if final_title: audio.tags.add(TIT2(encoding=3, text=final_title))
            if final_artist: audio.tags.add(TPE1(encoding=3, text=final_artist))
            if album: audio.tags.add(TALB(encoding=3, text=album))
            if year: audio.tags.add(TDRC(encoding=3, text=str(year)))
            if genre: audio.tags.add(TCON(encoding=3, text=genre))
            
            cover_injected = False
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, "rb") as img:
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()))
                    cover_injected = True
            audio.save(v2_version=3)
            
        elif ext == ".m4a":
            audio = MP4(filepath)
            audio.delete()
            if final_title: audio.tags['\xa9nam'] = [final_title]
            if final_artist: audio.tags['\xa9ART'] = [final_artist]
            if album: audio.tags['\xa9alb'] = [album]
            if year: audio.tags['\xa9day'] = [str(year)]
            if genre: audio.tags['\xa9gen'] = [genre]
            
            cover_injected = False
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, "rb") as img:
                    audio.tags['covr'] = [MP4Cover(img.read(), imageformat=MP4Cover.FORMAT_JPEG)]
                    cover_injected = True
            audio.save()
            
        elif ext == ".flac":
            audio = FLAC(filepath)
            audio.delete()
            if final_title: audio["title"] = final_title
            if final_artist: audio["artist"] = final_artist
            if album: audio["album"] = album
            if year: audio["date"] = str(year)
            if genre: audio["genre"] = genre
            
            cover_injected = False
            if cover_path and os.path.exists(cover_path):
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                with open(cover_path, "rb") as img:
                    pic.data = img.read()
                audio.add_picture(pic)
                cover_injected = True
            audio.save()
        else:
            print(f"    [-] Ekstensi {ext} tidak didukung untuk injeksi tag.")
            return

        if cover_injected:
            print("    [TAG] Berhasil menginjeksi Metadata & Cover Art.")
        else:
            print("    [TAG] Berhasil menginjeksi Metadata (Tanpa Cover Art).")
    except PermissionError:
        print("    [-] Akses ditolak. File mungkin sedang diputar di aplikasi lain.")
        return
    except Exception as e:
        print(f"    [-] Gagal menginjeksi tag: {e}")
        return
            
    # 3. Rename File Fisik
    new_filename = clean_filename(f"{final_artist} - {final_title}{ext}")
    new_filepath = os.path.join(directory, new_filename)
    
    try:
        if filepath != new_filepath:
            if os.path.exists(new_filepath):
                # Tangani duplikasi nama agar tidak tertimpa
                new_filename = clean_filename(f"{artist} - {title} (1){ext}")
                new_filepath = os.path.join(directory, new_filename)
            os.rename(filepath, new_filepath)
            print(f"    [REN] File berhasil di-rename menjadi: '{new_filename}'")
        else:
            print("    [REN] Nama file sudah bersih, tidak perlu diubah.")
    except Exception as e:
        print(f"    [-] Gagal melakukan rename: {e}")

# ==========================================
# CLI RUNNER
# ==========================================
def main():
    print("=" * 60)
    print(" 🎵 HYO MUSIC FILTER - OFFLINE PROCESSOR 🎵")
    print("=" * 60)
    
    target_dir = input("\n[?] Masukkan path direktori / folder musik Anda:\n>>> ").strip()
    if target_dir.startswith('"') and target_dir.endswith('"'):
        target_dir = target_dir[1:-1]
        
    if not os.path.isdir(target_dir):
        print("[-] Folder tidak ditemukan!")
        return
        
    music_files = []
    for ext in ("*.mp3", "*.m4a", "*.flac"):
        search_pattern = os.path.join(target_dir, "**", ext)
        music_files.extend(glob.glob(search_pattern, recursive=True))
    
    if not music_files:
        print("[-] Tidak ada file musik (.mp3, .m4a, .flac) di dalam folder tersebut (atau subfoldernya).")
        return
        
    print(f"\n[+] Ditemukan {len(music_files)} file lagu.")
    
    # Memuat Cache Database LOKAL
    cache_file = os.path.join(target_dir, "music_metadata.json")
    metadata_db = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            metadata_db = json.load(f)
        print(f"[+] Berhasil memuat Database Lokal! ({len(metadata_db)} lagu ter-cache).")
    else:
        print("\n[!] Peringatan: music_metadata.json tidak ditemukan!")
        print("[!] Script tetap berjalan (offline), namun tanpa info Genre dan Cover.")
        print("[!] Anda bisa menekan Ctrl+C lalu jalankan 'fetch_metadata.py' jika butuh cover.")
        print("-" * 60)
        
    # Mulai proses filter
    for filepath in music_files:
        process_file(filepath, metadata_db)
        
    print("\n" + "=" * 60)
    print(" [V] SEMUA PROSES SELESAI!")
    print("=" * 60)

if __name__ == "__main__":
    main()
