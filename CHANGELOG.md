# Changelog

Semua perubahan yang signifikan pada proyek "Hyo Music Filter" akan dicatat dalam file ini.

## [v1.7.0] - 2026-08-13
### Ditambahkan
- **Gemini AI Core Engine (Opsional)**: Aplikasi sekarang mendukung integrasi dengan Google Gemini AI (menggunakan model `gemini-1.5-flash` gratis) untuk mem-parsing dan memperbaiki nama file yang sangat kotor. 
  - Jika Gemini API Key disediakan di `.env`, AI akan memproses nama file sebelum mencarinya di iTunes/MusicBrainz. Ini memecahkan masalah "Gagal Regex" untuk file yang tidak memiliki pola standar.
  - Jika tidak ada API Key, aplikasi tetap bekerja 100% normal menggunakan parser Regex lokal.
- File `.env` dan `.env.example` ditambahkan kembali untuk menampung konfigurasi opsional ini secara aman.

## [v1.6.1] - 2026-08-13
### Diperbaiki
- **Solusi untuk File Korup (MPEG Sync Error)**: Saat pengguna memproses file yang korup (contohnya file MP4 video yang di-rename menjadi `.mp3` secara paksa tanpa konversi), library akan menolak menyuntikkan ID3 tag. Sekarang, alih-alih gagal total, aplikasi akan menampilkan opsi cerdas: aplikasi akan **tetap me-rename nama file fisiknya** menjadi rapi (sesuai artis/judul) meskipun metadatanya tidak dapat disuntikkan. File ini akan diberi status `⚠️ Rename Saja (File Korup)`.

## [v1.6.0] - 2026-08-13
### Ditambahkan
- **Batch Select Auto-Fix**: Sekarang pengguna dapat memproses (Auto-Fix) hanya file-file tertentu saja, alih-alih seluruh isi folder.
  - Tahan tombol `Ctrl` atau `Shift` untuk memilih (blok) beberapa file pada tabel.
  - Tombol Auto-Fix akan otomatis berubah menjadi `🚀 Auto-Fix (X Terpilih)` dan hanya akan mengunduh metadata + me-rename lagu-lagu yang kamu pilih saja.
  - Jika tidak ada yang dipilih, tombol akan berbunyi `🚀 Auto-Fix (Semua)` dan memproses seluruh folder.

## [v1.5.4] - 2026-08-13
### Ditambahkan
- **Smart Skip (Optimasi Performa)**: Aplikasi kini akan mengecek kelengkapan file musik (apakah sudah memiliki Artist, Title, dan Cover Art) *sebelum* memprosesnya. 
  - File yang sudah lengkap otomatis ditandai `✅ Sudah Lengkap` di tabel.
  - Proses Auto-Fix dan Fetch Metadata CLI akan langsung melewati file ini, menghemat kuota request API dan waktu eksekusi.
- Filter baru di dropdown: `✅ Sudah Lengkap` untuk memudahkan menemukan file-file yang sudah sempurna.

## [v1.5.3] - 2026-08-13
### Diubah
- **Migrasi dari Spotify ke MusicBrainz**: Karena Spotify Web API kini mewajibkan akun Premium, aplikasi sepenuhnya bermigrasi menggunakan API MusicBrainz dan Cover Art Archive sebagai sistem Fallback. Kelebihannya: 100% gratis, database open-source, dan **tidak perlu lagi repot mengatur file `.env` maupun API Key**. File konfigurasi rahasia telah dihapus.
- **Hybrid Pencarian Cover**: Jika iTunes berhasil menemukan metadata lagu namun tidak memiliki gambar cover, aplikasi otomatis mencari cover tersebut di MusicBrainz.

## [v1.5.2] - 2026-08-13
### Diubah
- **UI Filter yang Lebih Rapi**: Mengganti deretan tombol filter yang memakan tempat menjadi sebuah Dropdown (OptionMenu) yang ringkas di sebelah kanan kotak pencarian.

### Diperbaiki (Bug Fixes)
- Penanganan error khusus untuk bug *"can't sync to MPEG frame"* (karena file korup atau file video MP4 yang di-rename menjadi `.mp3` tanpa proses konversi). File tersebut kini ditandai dengan jelas sebagai `❌ File Korup/Bukan MP3 Asli` agar mudah diidentifikasi.

## [v1.5.1] - 2026-08-13
### Ditambahkan
- **Fitur Auto-Correct Typo**: Jika nama file memiliki salah eja (typo), aplikasi sekarang akan otomatis menggunakan ejaan resmi yang dikembalikan oleh iTunes/MusicBrainz untuk ID3 Tag dan nama file akhir. 

## [v1.5.0] - 2026-08-13
### Ditambahkan
- **Dukungan M4A & FLAC**: Aplikasi sekarang dapat membaca, memproses, dan menyuntikkan metadata (serta cover art) untuk file berekstensi `.m4a` dan `.flac`, tidak lagi terbatas pada `.mp3`.
- Injeksi metadata yang lebih aman dan modular di `app.py` menggunakan metode utilitas khusus.

### Diperbaiki
- Konsolidasi logika pencarian file di CLI (`main.py` dan `fetch_metadata.py`) agar otomatis mendeteksi MP3, M4A, dan FLAC di subfolder.

## [v1.4.0] - 2026-08-13
### Ditambahkan
- **Recursive Directory Scan**: Sekarang aplikasi membaca file musik tidak hanya di folder utama, tapi juga di semua subfolder di dalamnya secara otomatis.
- Tampilan kolom "Nama File" di tabel kini menunjukkan *relative path* (contoh: `2024\Anime\song.mp3`) agar user tahu lagu tersebut berada di subfolder mana.

### Diperbaiki (Bug Fixes)
- Memperbaiki bug kritis di Auto-Fix di mana file yang berada di subfolder dipindahkan secara paksa (flatten) ke folder root saat di-rename. Sekarang file akan tetap berada di dalam subfoldernya masing-masing.

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
