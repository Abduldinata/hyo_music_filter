"""
MusicBrainz & Cover Art Archive Client untuk Hyo Music Filter.
Database musik open-source gratis, tanpa perlu API Key.

Dokumentasi:
- MusicBrainz API: https://musicbrainz.org/doc/MusicBrainz_API
- Cover Art Archive: https://coverartarchive.org/
"""

import requests
import time

# MusicBrainz mewajibkan User-Agent khusus agar tidak di-banned
HEADERS = {
    "User-Agent": "HyoMusicFilter/1.5 ( https://github.com/Abduldinata/hyo_music_filter )"
}

def search_track(artist, title):
    """
    Mencari lagu di MusicBrainz dan Cover Art Archive.
    
    Args:
        artist (str): Nama artis
        title (str): Judul lagu

    Returns:
        dict: Metadata lagu (artist, title, album, year, genre, cover_url)
              atau None jika tidak ditemukan.
    """
    try:
        # 1. Cari Recording di MusicBrainz
        query = f'recording:"{title}"'
        if artist:
            query += f' AND artist:"{artist}"'
            
        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        recordings = data.get("recordings", [])
        
        if not recordings:
            return None
            
        track = recordings[0]
        
        # Ekstrak data dasar
        track_title = track.get("title", title)
        
        # Ekstrak Artist
        track_artist = artist
        artist_credit = track.get("artist-credit", [])
        if artist_credit:
            track_artist = artist_credit[0].get("name", artist)
            
        # Ekstrak Album & Year (Release)
        album_name = ""
        year = ""
        release_id = ""
        
        releases = track.get("releases", [])
        if releases:
            # Cari release yang statusnya Official jika memungkinkan
            best_release = releases[0]
            for r in releases:
                if r.get("status") == "Official":
                    best_release = r
                    break
                    
            album_name = best_release.get("title", "")
            date = best_release.get("date", "")
            year = date[:4] if date else ""
            release_id = best_release.get("id", "")
            
        # Ekstrak Genre (MusicBrainz menyebutnya tags)
        genre = ""
        tags = track.get("tags", [])
        if tags:
            # Ambil tag dengan count tertinggi (paling relevan)
            tags.sort(key=lambda x: x.get("count", 0), reverse=True)
            genre = tags[0].get("name", "").title()
            
        # 2. Ambil Cover Art dari Cover Art Archive berdasarkan Release ID
        cover_url = ""
        if release_id:
            cover_api_url = f"https://coverartarchive.org/release/{release_id}"
            try:
                cover_resp = requests.get(cover_api_url, headers=HEADERS, timeout=5)
                if cover_resp.status_code == 200:
                    images = cover_resp.json().get("images", [])
                    if images:
                        # Ambil gambar pertama (biasanya front cover)
                        # Tersedia ukuran: "250", "500", "1200", atau url asli
                        thumbnails = images[0].get("thumbnails", {})
                        cover_url = thumbnails.get("500") or thumbnails.get("large") or images[0].get("image", "")
            except Exception:
                pass # Abaikan jika cover gagal diambil
                
        # MusicBrainz rate limit: 1 request per detik
        time.sleep(1)
        
        return {
            "artist": track_artist,
            "title": track_title,
            "album": album_name,
            "year": year,
            "genre": genre,
            "cover_url": cover_url
        }
        
    except Exception as e:
        print(f"[MusicBrainz] Error: {e}")
        return None
