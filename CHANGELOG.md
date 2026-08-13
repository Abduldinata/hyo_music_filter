# Changelog

Semua perubahan yang signifikan pada proyek "Hyo Music Filter" akan dicatat dalam file ini.

## [v1.3.0] - 2026-08-13
### Ditambahkan
- **Filter & Search Bar** pada tabel file musik:
  - Search box real-time untuk mencari berdasarkan nama file, artis, atau judul.
  - 7 tombol filter: 📋 Semua, 🔤 A→Z, 🔤 Z→A, ✅ Sukses, ⚠️ Tanpa Cover, ❌ Gagal Regex, ⏳ Belum Proses.
  - Counter file yang ditampilkan vs total (contoh: `12 / 50 file`).
  - Tombol filter aktif berwarna biru, lainnya abu-abu.
- Data internal `_all_rows` untuk menyimpan semua row agar filter tidak kehilangan data.

### Diubah
- Fungsi `_update_row` sekarang juga meng-update data internal `_all_rows` agar filter konsisten setelah Auto-Fix.
- Fungsi `save_manual` menggunakan `_update_row` terpusat untuk konsistensi data.

## [v1.2.0] - 2026-08-13
### Ditambahkan
- **Progress Bar** pada proses Auto-Fix: bar visual, counter real-time `[3/25]`, dan statistik ✅⏭️❌.
- **Spotify API Fallback**: Jika iTunes tidak menemukan lagu, otomatis cari di Spotify (konfigurasi via `.env`).
- **Modul `spotify_client.py`**: Client Credentials Flow, auto-refresh token, pencarian track + genre artis.
- File `.env` dan `.env.example` untuk menyimpan API key secara aman.
- File `.gitignore` standar Python project.
- **Ringkasan akhir** setelah Auto-Fix selesai (popup statistik sukses/skip/gagal).
- Tombol "Pilih Folder" dan "Auto-Fix" di-disable selama proses berjalan agar tidak bentrok.
- Error message per-file yang lebih deskriptif (bukan hanya "Error File").

### Diperbaiki (Bug Fixes)
- Fix icon tidak berubah di Windows: `SetCurrentProcessExplicitAppUserModelID` dipindahkan sebelum window dibuat, dan icon dikonversi ke `.ico` native.

## [v1.1.1] - 2026-08-13
### Ditambahkan
- Ikon aplikasi resmi diintegrasikan ke dalam antarmuka aplikasi (`app.py`).

### Diperbaiki (Bug Fixes)
- Memperbaiki bug minor terkait status text update pada Treeview setelah proses manual.
- Menyempurnakan fallback mekanisme error handling pada auto-fix GUI.

## [v1.1.0] - 2026-08-12
### Ditambahkan
- **Modern GUI (`app.py`)**: Antarmuka grafis yang premium (Dark Mode) menggunakan `customtkinter`.
- Fitur **Manual Editor** untuk injeksi ID3 Tag (Artis, Judul, Album, Genre, dan upload Cover Art dari PC).
- Tabel navigasi (Treeview) untuk memilah status file musik (Sudah beres / Gagal / Siap diproses).
- Panel Editor Kata Sampah (Junk Words dictionary editor) secara langsung di aplikasi dengan auto-refresh.
- Proses auto-fix (Fetch iTunes & Injeksi) dijalankan di background thread agar UI tidak freeze.

### Diubah
- Regex parser ditingkatkan untuk menangani filter teks junk lebih optimal di dalam tanda kurung.

## [v1.0.0] - 2026-08-12
### Ditambahkan
- **CLI Core Tools**: Versi rilis awal.
- Pemisahan logis antara `fetch_metadata.py` (Proses Online - iTunes API Fetcher) dan `main.py` (Proses Offline - ID3 Injector & Renamer).
- Sistem deteksi Regex 8 lapis (Patterns) untuk menebak artis dan judul dari nama file.
- Pembersihan nama file otomatis dengan kata kunci "junk words" bawaan.
