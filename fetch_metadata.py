import os
import glob
import json
import time
import requests
from main import parse_filename # Menggunakan fungsi parser pintar yang sama dengan main.py agar 100% sinkron!

def main():
    print("="*60)
    print(" 📡 ITUNES METADATA FETCHER (ONLINE)")
    print("="*60)
    
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
    print("    Script akan mengunduh metadata dan cover art dari iTunes.")
    print("    Proses ini diberi jeda 2 detik per lagu agar server iTunes tidak memblokir IP Anda.\n")
    
    cache_file = os.path.join(target_dir, "music_metadata.json")
    cover_dir = os.path.join(target_dir, "covers")
    os.makedirs(cover_dir, exist_ok=True)
    
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)
            
    failed = []
    missing_covers = []
    
    for idx, filepath in enumerate(music_files, 1):
        filename = os.path.basename(filepath)
        
        # Ekstrak artis dan judul menggunakan logika Regex yang SAMA PERSIS dengan main.py
        parsed = parse_filename(filepath)
        if parsed:
            artist = parsed.get("artist", "")
            title = parsed.get("title", "")
        else:
            # Fallback jika Regex gagal total
            artist = ""
            title = os.path.splitext(filename)[0]
        
        if not title:
            continue
            
        print(f"[{idx}/{len(music_files)}] Mencari: {artist} - {title}" if artist else f"[{idx}/{len(music_files)}] Mencari: {title}")
        
        # Buat key pencarian unik (HARUS SAMA PERSIS DENGAN YANG DICARI main.py NANTI)
        key_artist = (artist or "unknown").lower()
        key_title = title.lower()
        key = f"{key_artist}||{key_title}"
        
        if key in cache:
            # Jika sudah di cache, cek apakah cover-nya ada. Jika tidak ada, catat.
            if not cache[key].get("local_cover") or not os.path.exists(cache[key]["local_cover"]):
                missing_covers.append(filename)
            print("    -> Sudah ada di cache lokal. Dilewati.")
            continue
            
        try:
            # Bangun keyword pencarian
            search_artist = artist if artist else ""
            term = f"{search_artist} {title}".strip().replace(' ', '+')
            url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=1"
            
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data['resultCount'] > 0:
                    item = data['results'][0]
                    fetched_artist = item.get("artistName")
                    fetched_title = item.get("trackName")
                    
                    # Ubah cover jadi HD (resolusi tinggi)
                    cover_url = item.get("artworkUrl100", "").replace("100x100bb.jpg", "600x600bb.jpg")
                    
                    cache_entry = {
                        "artist": fetched_artist,
                        "title": fetched_title,
                        "album": item.get("collectionName"),
                        "year": item.get("releaseDate", "")[:4],
                        "genre": item.get("primaryGenreName"),
                        "cover_url": cover_url,
                        "local_cover": None
                    }
                    
                    # Simpan Cover Art ke direktori lokal
                    if cover_url:
                        safe_filename = "".join([c for c in f"{fetched_artist} - {fetched_title}" if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                        cover_filename = safe_filename + ".jpg"
                        cover_path = os.path.join(cover_dir, cover_filename)
                        
                        if not os.path.exists(cover_path):
                            img_data = requests.get(cover_url, timeout=10).content
                            with open(cover_path, "wb") as img_file:
                                img_file.write(img_data)
                                
                        cache_entry["local_cover"] = cover_path
                        print(f"    -> [SUKSES] Ditemukan & Cover Diunduh: {fetched_artist} - {fetched_title}")
                    else:
                        print(f"    -> [SUKSES SEBAGIAN] Ditemukan, TAPI COVER TIDAK ADA: {fetched_artist} - {fetched_title}")
                        missing_covers.append(filename)
                        
                    cache[key] = cache_entry
                else:
                    print("    -> [GAGAL] Tidak ditemukan di iTunes sama sekali.")
                    failed.append(filename)
            else:
                 print(f"    -> [GAGAL] API Error: {resp.status_code}")
                 failed.append(filename)
                 
        except Exception as e:
            print(f"    -> [ERROR] {e}")
            failed.append(filename)
            
        time.sleep(2) # Sopan santun rate limit
        
    # Tulis hasil akhirnya ke file JSON secara Real-Time setelah loop selesai
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)
        
    if failed:
        failed_path = os.path.join(target_dir, "failed.txt")
        with open(failed_path, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n[!] Terdapat {len(failed)} lagu yang gagal ditemukan (Dicatat di failed.txt)")
        
    if missing_covers:
        missing_covers_path = os.path.join(target_dir, "missing_covers.txt")
        with open(missing_covers_path, "w", encoding="utf-8") as f:
            f.write("\n".join(missing_covers))
        print(f"[!] Terdapat {len(missing_covers)} lagu yang ditemukan, TAPI TIDAK ADA FOTO COVER (Dicatat di missing_covers.txt)")
        print("    -> Anda bisa men-download gambar cover secara manual dari Google dan menaruhnya di folder 'covers/'.")
        
    print("\n[V] SELESAI! Semua proses fetching telah selesai dijalankan!")

if __name__ == "__main__":
    main()
