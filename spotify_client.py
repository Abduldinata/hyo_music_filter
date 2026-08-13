"""
Spotify Web API Client untuk Hyo Music Filter.
Menggunakan Client Credentials Flow untuk mencari metadata lagu.

Konfigurasi:
    Isi SPOTIFY_CLIENT_ID dan SPOTIFY_CLIENT_SECRET di file .env
    Dapatkan dari https://developer.spotify.com/dashboard
"""

import os
import time
import base64
import requests

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# ==========================================
# KONFIGURASI
# ==========================================
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

# Cache token di memory
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


def is_configured():
    """Cek apakah Spotify API sudah dikonfigurasi dengan benar."""
    return (
        bool(SPOTIFY_CLIENT_ID)
        and bool(SPOTIFY_CLIENT_SECRET)
        and SPOTIFY_CLIENT_ID != "your_client_id_here"
        and SPOTIFY_CLIENT_SECRET != "your_client_secret_here"
    )


def _get_access_token():
    """
    Mendapatkan access token dari Spotify menggunakan Client Credentials Flow.
    Token di-cache dan otomatis di-refresh jika sudah expired.
    """
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    if not is_configured():
        return None

    try:
        credentials = base64.b64encode(
            f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()

        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials"},
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            _token_cache["access_token"] = data["access_token"]
            # Refresh 60 detik sebelum expired untuk safety margin
            _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
            return _token_cache["access_token"]
        else:
            print(f"[Spotify] Gagal mendapatkan token: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"[Spotify] Error saat request token: {e}")
        return None


def _get_artist_genres(artist_id, token):
    """Mengambil genre dari profil artis Spotify."""
    try:
        resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code == 200:
            genres = resp.json().get("genres", [])
            return genres[0] if genres else None
    except Exception:
        pass
    return None


def search_track(artist, title):
    """
    Mencari lagu di Spotify dan mengembalikan metadata-nya.

    Args:
        artist (str): Nama artis
        title (str): Judul lagu

    Returns:
        dict: Metadata lagu (artist, title, album, year, genre, cover_url)
              atau None jika tidak ditemukan / error.
    """
    token = _get_access_token()
    if not token:
        return None

    try:
        # Bangun query pencarian
        if artist:
            query = f"artist:{artist} track:{title}"
        else:
            query = title

        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": query,
                "type": "track",
                "limit": 1
            },
            timeout=10
        )

        if resp.status_code != 200:
            print(f"[Spotify] Search error: {resp.status_code}")
            return None

        data = resp.json()
        tracks = data.get("tracks", {}).get("items", [])

        if not tracks:
            return None

        track = tracks[0]

        # Ambil info dasar
        track_artist = track["artists"][0]["name"] if track.get("artists") else artist
        artist_id = track["artists"][0]["id"] if track.get("artists") else None
        track_title = track.get("name", title)
        album_name = track.get("album", {}).get("name", "")
        release_date = track.get("album", {}).get("release_date", "")
        year = release_date[:4] if release_date else ""

        # Ambil cover art resolusi tertinggi (biasanya 640x640)
        images = track.get("album", {}).get("images", [])
        cover_url = images[0]["url"] if images else ""

        # Ambil genre dari profil artis
        genre = None
        if artist_id:
            genre = _get_artist_genres(artist_id, token)

        return {
            "artist": track_artist,
            "title": track_title,
            "album": album_name,
            "year": year,
            "genre": genre,
            "cover_url": cover_url
        }

    except Exception as e:
        print(f"[Spotify] Error saat mencari '{artist} - {title}': {e}")
        return None
