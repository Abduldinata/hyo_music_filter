A. Ringkasan Produk
Hyo Music Filter adalah utility tool berbasis AI yang mengotomatisasi proses perapian file musik unduhan. Aplikasi ini membaca file lokal, memanfaatkan AI untuk membersihkan nama file (ekstraksi artis, judul, dan kategori bahasa), mengambil metadata resmi (genre, cover art) dari database pihak ketiga, dan menyuntikkannya langsung ke dalam ID3 Tags file audio.

B. Objektif

Menghilangkan kebutuhan rename manual dan pencarian cover album satu per satu.

Menyediakan manajemen file system yang rapi untuk perpustakaan musik luring (offline).

C. Fitur Utama (Core Features)

Directory Scanner: Membaca semua file audio (MP3, M4A, dll) di dalam folder yang dipilih pengguna.

AI Parsing Engine: Menggunakan LLM (Gemini) untuk mengekstrak data terstruktur (Artis, Judul, Kategori JP/ID/ENG) dari nama file acak.

Metadata Fetcher: Terhubung dengan API Database Musik (seperti iTunes Search API atau Spotify API) untuk mengunduh cover art resolusi tinggi dan genre resmi.

ID3 Tag Injector: Menulis ulang metadata (Judul, Artis, Genre, Cover) secara permanen ke dalam file audio.

Smart Renamer: Mengubah nama file fisik menjadi format standar (contoh: Artis - Judul.mp3).

D. Fase Pengembangan (Roadmap)

Fase 1 (MVP - Python CLI): Fokus pada core logic. Membaca folder dengan skrip Python, integrasi Gemini API untuk pembersihan nama, integrasi API musik untuk cover, dan modifikasi ID3 tag menggunakan library mutagen.

Fase 2 (UI/UX - GUI): Membangun antarmuka grafis (menggunakan Python `customtkinter`) di mana pengguna bisa memilih folder dengan file picker, mengedit filter kata sampah, melihat progress bar saat pemrosesan massal, serta melihat status eksekusi (berhasil/gagal) dan fitur edit metadata & cover art secara manual.