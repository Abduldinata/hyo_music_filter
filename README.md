# Hyo Music Filter

Hyo Music Filter adalah utility tool berbasis Regex tingkat lanjut yang mengotomatisasi proses perapian file musik unduhan. Aplikasi ini membersihkan nama file dari "kata-kata sampah" (seperti "official video", "lyric", dll), mengambil metadata dan cover album resmi dari iTunes API & MusicBrainz, serta menyuntikkan ID3 Tags tersebut ke dalam file musik secara permanen.

## Fitur Utama

- **Smart Renamer:** Mengubah format nama file musik yang berantakan menjadi rapi (contoh: `Artis - Judul.mp3`).
- **Metadata Fetcher:** Mendownload Genre dan Foto Cover Album resolusi tinggi secara otomatis dari Apple iTunes, dengan fallback ke **MusicBrainz & Cover Art Archive** (100% Gratis, tanpa API Key).
- **ID3 Tag Injector:** Menulis Artist, Title, Album, Genre, dan Cover Image ke dalam properti file musik secara permanen (Mendukung MP3, M4A, dan FLAC).
- **GUI Modern & CLI:** Dapat digunakan melalui aplikasi GUI (Dark Mode) yang dibekali editor manual, maupun secara CLI (Command Line).
- **Progress Bar & Statistik:** Menampilkan progress real-time saat pemrosesan massal, lengkap dengan ringkasan akhir (sukses/gagal/skip).
- **Filter & Search:** Dropdown filter berdasarkan status (Sukses, Gagal Regex, Tanpa Cover, Belum Proses) dan search box untuk pencarian cepat.
- **Sort A-Z / Z-A:** Mengurutkan tabel berdasarkan artis dan judul secara ascending atau descending.

## Persyaratan (Requirements)

Pastikan sistem Anda telah terinstal **Python 3.8** atau yang lebih baru.

Install pustaka Python (dependencies) yang dibutuhkan:

```bash
pip install mutagen requests pillow customtkinter
```

*(Tidak perlu konfigurasi API Key tambahan, semua berjalan otomatis dan gratis).*

## Cara Penggunaan

### 1. Menggunakan Versi GUI (Rekomendasi)

Jalankan perintah berikut:

```bash
python app.py
```

**Alur kerja:**
1. Klik tombol **"📂 Pilih Folder"** dan pilih folder tempat musik `.mp3` Anda berada.
2. Gunakan **Search Box** dan **tombol Filter** (Semua, A→Z, Z→A, ✅ Sukses, ⚠️ Tanpa Cover, ❌ Gagal Regex, ⏳ Belum Proses) untuk memilah file.
3. Klik **"🚀 Auto-Fix (Smart)"** untuk memproses semua file secara otomatis. Progress bar akan menampilkan status real-time.
4. Setelah selesai, popup ringkasan akan muncul menampilkan jumlah file sukses, dilewati, dan gagal.

**Manual Editor:**
- Klik salah satu file di tabel sebelah kiri.
- Edit Judul, Artis, Album, Genre, dan Cover Art di panel kanan.
- Klik **"💾 Simpan & Rename File"** untuk menyimpan.

**Filter Kata Sampah:**
- Di bagian kiri bawah, sesuaikan daftar kata-kata sampah (contoh: `remix`, `live`, dll.).
- Klik tombol simpan untuk menyegarkan tampilan tabel.

### 2. Menggunakan Versi CLI

Jika Anda lebih menyukai antarmuka terminal, prosesnya dibagi menjadi dua tahap:

**Tahap 1: Download Metadata (Online)**
```bash
python fetch_metadata.py
```
Masukkan path folder musik Anda. Script ini akan membuat file `music_metadata.json` dan folder `covers/` sebagai cache lokal.

**Tahap 2: Injeksi ID3 & Rename File (Offline)**
```bash
python main.py
```
Masukkan kembali path folder yang sama. Script ini akan membaca cache dari Tahap 1, menyuntikkan metadata & cover art, dan me-rename file Anda.

## Struktur Proyek

```
hyo_music_filter/
├── app.py              # Aplikasi GUI utama (CustomTkinter)
├── main.py             # CLI: ID3 Injector & Smart Renamer (Offline)
├── fetch_metadata.py   # CLI: iTunes Metadata Fetcher (Online)
├── spotify_client.py   # Modul Spotify Web API client
├── junk_words.txt      # Kamus kata-kata sampah yang bisa diedit
├── icon/
│   ├── icon.png        # Icon aplikasi (source)
│   └── icon.ico        # Icon aplikasi (Windows native)
├── .env                # API keys (RAHASIA - tidak masuk Git)
├── .env.example        # Template konfigurasi API keys
├── .gitignore          # Daftar file yang diabaikan Git
├── prd.md              # Product Requirements Document
├── CHANGELOG.md        # Riwayat perubahan versi
└── README.md           # Dokumentasi ini
```

## Penyelesaian Masalah (Troubleshooting)

| Masalah | Solusi |
|---------|--------|
| Proses gagal (Error) | Pastikan file `.mp3` tidak sedang diputar oleh aplikasi lain (Groove Music, VLC, dll). |
| Lagu tidak ditemukan di iTunes/MusicBrainz | Pastikan nama file awal memiliki Artis dan Judul yang cukup jelas. Gunakan Manual Editor jika perlu. |
| Icon tidak muncul di taskbar | Pastikan file `icon/icon.ico` ada. Jalankan `app.py` langsung (bukan dari IDE). |

## Lisensi

Proyek ini dibuat untuk keperluan pribadi dan edukasi.
