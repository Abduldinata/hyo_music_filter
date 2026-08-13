import os
import glob
import re
import json
import time
import requests
import threading
import difflib
from tkinter import filedialog, messagebox, ttk
from io import BytesIO

try:
    from PIL import Image, ImageTk
    import customtkinter as ctk
except ImportError:
    pass

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TCON, APIC, TALB, TDRC, error as id3_error
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.flac import FLAC, Picture
except ImportError:
    pass

# ==========================================
# KONFIGURASI TEMA MODERN
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==========================================
# REGEX PATTERNS & JUNK WORDS
# ==========================================
PATTERNS = [
    re.compile(r"^(?P<track>\d{2,3})\s*[-.]\s*(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<album>.+?),\s*(?P<year>\d{4})\)\s*\[(?P<lang>JP|ID|ENG|KOR)\]$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<album>.+?)\s*[-.]\s*(?P<track>\d{1,3})\s*[-.]\s*(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*(?:\(feat\.\s*(?P<feat>.+?)\))?\s*\((?P<year>\d{4})\)\s*\[?(?P<lang>JP|ID|ENG)?\]?$", re.I),
    re.compile(r"^(?P<title>.+?)\s*[-.]\s*(?P<artist>.+?)\s*\[(?P<album>.+?)\]\s*\((?P<year>\d{4})\)$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<album>.+?)\)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\[(?P<lang>JP|ID|ENG)\]$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-.]\s*(?P<title>.+?)\s*\((?P<year>\d{4})\)$", re.I),
    re.compile(r"^(?P<artist>.+?)\s*[-–_]\s*(?P<title>.+?)$", re.I),
]

DEFAULT_JUNK_WORDS = [
    "official music video", "official video", "official audio", "official lyric video",
    "lyric video", "lyrics video", "lyric", "lyrics", "lirik", "karaoke", "instrumental",
    "audio", "video", "music", "320kbps", "mp3", "remix", "cover", "hd", "hq", "live", 
    "acoustic", "version", "edit", "mix", "vevo", "ft", "feat", "featuring"
]

JUNK_WORDS = []

def load_junk_words():
    global JUNK_WORDS
    if os.path.exists("junk_words.txt"):
        with open("junk_words.txt", "r", encoding="utf-8") as f:
            JUNK_WORDS = [w.strip() for w in f.read().split(",") if w.strip()]
    else:
        JUNK_WORDS = DEFAULT_JUNK_WORDS.copy()
        save_junk_words()

def save_junk_words():
    with open("junk_words.txt", "w", encoding="utf-8") as f:
        f.write(", ".join(JUNK_WORDS))

load_junk_words()

def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def parse_filename(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    cleaned_name = name
    
    if JUNK_WORDS:
        # Sort by length descending so longer phrases match first (e.g. "lyric video" before "lyric")
        sorted_junk = sorted(JUNK_WORDS, key=len, reverse=True)
        regex_junk = '|'.join([re.escape(w) for w in sorted_junk])
        
        # Buang teks di dalam kurung yang mengandung kata-kata junk
        cleaned_name = re.sub(rf'\((.*?)({regex_junk})(.*?)\)', '', cleaned_name, flags=re.IGNORECASE)
        cleaned_name = re.sub(rf'\[(.*?)({regex_junk})(.*?)\]', '', cleaned_name, flags=re.IGNORECASE)
        
        cleaned_name = cleaned_name.replace('_', ' ')
        
        for j in sorted_junk:
            cleaned_name = re.sub(r'\b' + re.escape(j) + r'\b', "", cleaned_name, flags=re.IGNORECASE)
            
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    cleaned_name = re.sub(r'\s+\.', '.', cleaned_name)
    
    for pattern in PATTERNS:
        m = pattern.match(cleaned_name)
        if m:
            data = m.groupdict()
            clean = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if v is not None}
            if 'year' in clean: clean['year'] = int(clean['year'])
            if 'track' in clean: clean['track'] = int(clean['track'])
            if 'feat' in clean: clean['featured_artists'] = [a.strip() for a in clean.pop('feat').split(',')]
            else: clean['featured_artists'] = []
            return clean
            
    # FALLBACK: Jika tidak ada pola regex yang cocok (contoh: tidak ada tanda strip "-")
    # Asumsikan seluruh teks yang tersisa adalah Title.
    if cleaned_name and len(cleaned_name) > 2:
        return {
            "artist": "",
            "title": cleaned_name
        }
            
    return None

def is_similar(str1, str2, threshold=0.75):
    """Cek apakah dua string mirip (fuzzy match)."""
    if not str1 or not str2:
        return False
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio() >= threshold

class HyoMusicModernGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hyo Music Filter - Premium Edition")
        self.root.geometry("1200x750")
        
        # Load Application Icon
        try:
            icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon")
            icon_png = os.path.join(icon_dir, "icon.png")
            icon_ico = os.path.join(icon_dir, "icon.ico")
            
            if os.path.exists(icon_ico):
                # .ico adalah format native Windows, paling andal untuk titlebar + taskbar
                self.root.iconbitmap(icon_ico)
            elif os.path.exists(icon_png):
                # Fallback: gunakan PNG via wm_iconphoto
                img = Image.open(icon_png)
                self.app_icon = ImageTk.PhotoImage(img)
                self.root.wm_iconphoto(True, self.app_icon)
        except Exception as e:
            print(f"Failed to load icon: {e}")
            
        self.target_dir = ""
        self.music_files = []
        self.selected_file = None
        self.cache_db = {}
        self.current_cover_path = None
        self.photo_preview = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Grid layout
        self.root.grid_columnconfigure(0, weight=7)
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(0, weight=1)
        
        # ================= KIRI: PANEL TABEL & KONTROL =================
        self.frame_left = ctk.CTkFrame(self.root, corner_radius=10)
        self.frame_left.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
        
        # Toolbar Atas
        self.toolbar = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=15, pady=15)
        
        self.btn_folder = ctk.CTkButton(self.toolbar, text="📂 Pilih Folder", font=("Inter", 13, "bold"), command=self.load_folder)
        self.btn_folder.pack(side="left", padx=(0, 10))
        
        self.btn_auto = ctk.CTkButton(self.toolbar, text="🚀 Auto-Fix (Semua)", font=("Inter", 13, "bold"), 
                                      fg_color="#006400", hover_color="#008000", command=self.run_auto_fix)
        self.btn_auto.pack(side="left")
        
        self.lbl_status = ctk.CTkLabel(self.toolbar, text="Siap.", font=("Inter", 12, "italic"), text_color="gray")
        self.lbl_status.pack(side="right")
        
        # Progress Bar Area
        self.frame_progress = ctk.CTkFrame(self.frame_left, fg_color="transparent", height=50)
        self.frame_progress.pack(fill="x", padx=15, pady=(0, 5))
        self.frame_progress.pack_forget()  # Sembunyikan dulu, tampil saat Auto-Fix jalan
        
        self.lbl_progress_detail = ctk.CTkLabel(self.frame_progress, text="", font=("Inter", 11), text_color="#aaaaaa")
        self.lbl_progress_detail.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.frame_progress, height=14, corner_radius=7)
        self.progress_bar.pack(fill="x", pady=(3, 0))
        self.progress_bar.set(0)
        
        self.lbl_progress_stats = ctk.CTkLabel(self.frame_progress, text="", font=("Inter", 10), text_color="#888888")
        self.lbl_progress_stats.pack(anchor="e")
        
        # ================= FILTER BAR =================
        self.frame_filter = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.frame_filter.pack(fill="x", padx=15, pady=(0, 8))
        
        # Baris 1: Search box + Dropdown Filter + Counter
        self.frame_search = ctk.CTkFrame(self.frame_filter, fg_color="transparent")
        self.frame_search.pack(fill="x")
        
        ctk.CTkLabel(self.frame_search, text="🔍", font=("Inter", 14)).pack(side="left", padx=(0, 4))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.entry_search = ctk.CTkEntry(self.frame_search, textvariable=self.search_var,
                                         placeholder_text="Cari file, artis, atau judul...",
                                         height=30, font=("Inter", 11))
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Dropdown Filter
        self.filter_options = {
            "📋 Semua": "all",
            "🔤 A → Z": "az",
            "🔤 Z → A": "za",
            "✅ Sukses": "success",
            "✅ Sudah Lengkap": "complete",
            "⚠️ Tanpa Cover": "no_cover",
            "❌ Gagal Regex": "fail_regex",
            "⏳ Belum Proses": "pending"
        }
        
        self.active_filter = "all"
        self.combo_filter = ctk.CTkOptionMenu(
            self.frame_search,
            values=list(self.filter_options.keys()),
            font=("Inter", 11),
            width=140,
            command=self._on_dropdown_change
        )
        self.combo_filter.pack(side="left", padx=(0, 15))
        
        self.lbl_filter_count = ctk.CTkLabel(self.frame_search, text="0 file", 
                                             font=("Inter", 11, "bold"), text_color="#888")
        self.lbl_filter_count.pack(side="right")
        
        # Data internal untuk menyimpan semua row (agar filter tidak kehilangan data)
        self._all_rows = []  # List of (iid, values_tuple)
        
        # Treeview (Dark Mode)
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", 
                        background="#2b2b2b", foreground="white", rowheight=30, fieldbackground="#2b2b2b",
                        bordercolor="#343638", borderwidth=0, font=("Inter", 10))
        self.style.map('Treeview', background=[('selected', '#1f538d')])
        self.style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=("Inter", 11, "bold"), relief="flat")
        self.style.map("Treeview.Heading", background=[('active', '#3484F0')])
        
        self.tree_frame = ctk.CTkFrame(self.frame_left)
        self.tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        columns = ("file", "artist", "title", "status")
        # selectmode="extended" memungkinkan Ctrl+Click dan Shift+Click
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", style="Treeview", selectmode="extended")
        self.tree.heading("file", text="Nama File Asli")
        self.tree.heading("artist", text="Artis (RegEx)")
        self.tree.heading("title", text="Judul (RegEx)")
        self.tree.heading("status", text="Status Eksekusi")
        
        self.tree.column("file", width=250)
        self.tree.column("artist", width=120)
        self.tree.column("title", width=180)
        self.tree.column("status", width=140)
        
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Panel Edit Kata Sampah (Junk Words)
        self.frame_junk = ctk.CTkFrame(self.frame_left, fg_color="#1e1e1e", corner_radius=8)
        self.frame_junk.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(self.frame_junk, text="🧽 Kamus Filter Teks Sampah (Pisahkan dengan koma):", 
                     font=("Inter", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        self.txt_junk = ctk.CTkTextbox(self.frame_junk, height=60, font=("Inter", 12))
        self.txt_junk.pack(fill="x", padx=10, pady=(5, 5))
        self.txt_junk.insert("1.0", ", ".join(JUNK_WORDS))
        
        self.btn_save_junk = ctk.CTkButton(self.frame_junk, text="💾 Simpan Filter & Refresh Tabel", 
                                           fg_color="#8b0000", hover_color="#a52a2a",
                                           command=self.save_and_refresh_junk)
        self.btn_save_junk.pack(anchor="e", padx=10, pady=(0, 10))
        
        # ================= KANAN: PANEL MANUAL EDIT =================
        self.frame_right = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#1e1e1e")
        self.frame_right.grid(row=0, column=1, padx=(5, 15), pady=15, sticky="nsew")
        
        ctk.CTkLabel(self.frame_right, text="🛠️ Editor Manual", font=("Inter", 18, "bold")).pack(pady=20)
        
        # Gambar Cover Art
        self.lbl_cover = ctk.CTkLabel(self.frame_right, text="Tidak ada Cover", 
                                      width=160, height=160, fg_color="#2b2b2b", corner_radius=8)
        self.lbl_cover.pack(pady=10)
        
        self.btn_cover = ctk.CTkButton(self.frame_right, text="📸 Pilih Cover dari PC...", width=160,
                                       fg_color="#444", hover_color="#555", command=self.browse_cover)
        self.btn_cover.pack(pady=(0, 20))
        
        # Input Metadata
        self.inputs = {}
        for field in ["Artis", "Judul", "Album", "Genre"]:
            lbl = ctk.CTkLabel(self.frame_right, text=field + ":", font=("Inter", 12))
            lbl.pack(anchor="w", padx=25)
            ent = ctk.CTkEntry(self.frame_right, width=250, height=35, placeholder_text=f"Masukkan {field}...")
            ent.pack(padx=25, pady=(0, 10))
            self.inputs[field] = ent
            
        self.btn_save = ctk.CTkButton(self.frame_right, text="💾 Simpan & Rename File", 
                                      height=45, font=("Inter", 14, "bold"),
                                      fg_color="#005bb5", hover_color="#0074e8", command=self.save_manual)
        self.btn_save.pack(fill="x", padx=25, pady=30)
        
    def save_and_refresh_junk(self):
        global JUNK_WORDS
        text = self.txt_junk.get("1.0", "end").strip()
        JUNK_WORDS = [w.strip() for w in text.split(",") if w.strip()]
        save_junk_words()
        if self.target_dir:
            self._refresh_table()
            messagebox.showinfo("Sukses", "Kamus Filter berhasil disimpan dan daftar lagu telah disegarkan!")
        else:
            messagebox.showinfo("Sukses", "Kamus Filter berhasil disimpan!")

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder: return
        self.target_dir = folder
        self._refresh_table()
        
    def _refresh_table(self):
        if not self.target_dir: return
        
        # Cari mp3, m4a, dan flac
        self.music_files = []
        for ext in ("*.mp3", "*.m4a", "*.flac"):
            self.music_files.extend(glob.glob(os.path.join(self.target_dir, "**", ext), recursive=True))
        
        # Simpan semua row ke data internal
        self._all_rows = []
        for fp in self.music_files:
            # Gunakan relative path agar user tahu kalau file ada di subfolder
            fname = os.path.relpath(fp, self.target_dir)
            
            # Cek kelengkapan metadata file tersebut
            meta = self._read_metadata(fp)
            is_complete = bool(meta.get("title") and meta.get("artist") and meta.get("cover_data"))
            
            parsed = parse_filename(fp)
            
            # Jika sudah lengkap, pakai metadata bawaan file
            if is_complete:
                artist = meta["artist"]
                title = meta["title"]
                status = "✅ Sudah Lengkap"
            else:
                # Jika belum lengkap, pakai tebakan Regex
                artist = parsed.get('artist', '') if parsed else ''
                title = parsed.get('title', '') if parsed else ''
                status = "⏳ Siap di-Auto Fix" if parsed else "❌ Gagal Regex (Edit Manual)"
                
            self._all_rows.append((fp, (fname, artist, title, status)))
            
        self.lbl_status.configure(text=f"Sukses memuat {len(self.music_files)} file.")
        
        cache_path = os.path.join(self.target_dir, "music_metadata.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                self.cache_db = json.load(f)
        
        # Reset filter ke "Semua" dan render tabel
        self.active_filter = "all"
        self.search_var.set("")
        self._apply_filter()
    
    def _on_dropdown_change(self, choice):
        """Handler saat dropdown filter dipilih."""
        self.active_filter = self.filter_options.get(choice, "all")
        self._apply_filter()
        
    def _apply_filter(self, *args):
        """Filter dan render ulang tabel berdasarkan filter aktif + search query."""
        
        search_query = self.search_var.get().strip().lower()
        
        # Bersihkan tabel
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter rows
        filtered = []
        for iid, vals in self._all_rows:
            fname, artist, title, status = vals
            
            # Search filter
            if search_query:
                searchable = f"{fname} {artist} {title}".lower()
                if search_query not in searchable:
                    continue
            
            # Status filter
            f = self.active_filter
            if f == "success" and "✅ Sukses" not in status:
                continue
            elif f == "complete" and "✅ Sudah Lengkap" not in status:
                continue
            elif f == "no_cover" and "⚠️" not in status:
                continue
            elif f == "fail_regex" and "❌" not in status:
                continue
            elif f == "pending" and "⏳" not in status:
                continue
            # "all", "az", "za" tidak filter status
            
            filtered.append((iid, vals))
        
        # Sort jika A-Z atau Z-A
        if self.active_filter == "az":
            filtered.sort(key=lambda x: (x[1][1].lower(), x[1][2].lower()))  # artist, title
        elif self.active_filter == "za":
            filtered.sort(key=lambda x: (x[1][1].lower(), x[1][2].lower()), reverse=True)
        
        # Render
        for iid, vals in filtered:
            self.tree.insert("", "end", iid=iid, values=vals)
        
        # Update counter
        self.lbl_filter_count.configure(text=f"{len(filtered)} / {len(self._all_rows)} file")
                
    def _read_metadata(self, filepath):
        """Membaca metadata dari file musik (MP3, M4A, FLAC)."""
        ext = os.path.splitext(filepath)[1].lower()
        meta = {"title": "", "artist": "", "album": "", "genre": "", "cover_data": None}
        
        try:
            if ext == ".mp3":
                audio = MP3(filepath, ID3=ID3)
                if audio.tags:
                    if 'TIT2' in audio: meta["title"] = audio.tags['TIT2'].text[0]
                    if 'TPE1' in audio: meta["artist"] = audio.tags['TPE1'].text[0]
                    if 'TALB' in audio: meta["album"] = audio.tags['TALB'].text[0]
                    if 'TCON' in audio: meta["genre"] = audio.tags['TCON'].text[0]
                    apic = audio.tags.getall('APIC')
                    if apic: meta["cover_data"] = apic[0].data
            elif ext == ".m4a":
                audio = MP4(filepath)
                if audio.tags:
                    if '\xa9nam' in audio: meta["title"] = audio.tags['\xa9nam'][0]
                    if '\xa9ART' in audio: meta["artist"] = audio.tags['\xa9ART'][0]
                    if '\xa9alb' in audio: meta["album"] = audio.tags['\xa9alb'][0]
                    if '\xa9gen' in audio: meta["genre"] = audio.tags['\xa9gen'][0]
                    if 'covr' in audio: meta["cover_data"] = audio.tags['covr'][0]
            elif ext == ".flac":
                audio = FLAC(filepath)
                if audio.tags:
                    if 'title' in audio: meta["title"] = audio.tags['title'][0]
                    if 'artist' in audio: meta["artist"] = audio.tags['artist'][0]
                    if 'album' in audio: meta["album"] = audio.tags['album'][0]
                    if 'genre' in audio: meta["genre"] = audio.tags['genre'][0]
                if audio.pictures:
                    meta["cover_data"] = audio.pictures[0].data
        except Exception:
            pass
        return meta

    def _inject_metadata(self, filepath, title, artist, album, year, genre, cover_path):
        """Menulis metadata ke file musik sesuai ekstensinya (MP3/M4A/FLAC)."""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == ".mp3":
            audio = MP3(filepath, ID3=ID3)
            try: audio.delete()
            except id3_error: pass
            
            audio.tags = ID3()
            if title: audio.tags.add(TIT2(encoding=3, text=title))
            if artist: audio.tags.add(TPE1(encoding=3, text=artist))
            if album: audio.tags.add(TALB(encoding=3, text=album))
            if year: audio.tags.add(TDRC(encoding=3, text=str(year)))
            if genre: audio.tags.add(TCON(encoding=3, text=genre))
            
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, "rb") as img:
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()))
            audio.save(v2_version=3)
            
        elif ext == ".m4a":
            audio = MP4(filepath)
            audio.delete()
            if title: audio.tags['\xa9nam'] = [title]
            if artist: audio.tags['\xa9ART'] = [artist]
            if album: audio.tags['\xa9alb'] = [album]
            if year: audio.tags['\xa9day'] = [str(year)]
            if genre: audio.tags['\xa9gen'] = [genre]
            
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, "rb") as img:
                    audio.tags['covr'] = [MP4Cover(img.read(), imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
            
        elif ext == ".flac":
            audio = FLAC(filepath)
            audio.delete()
            if title: audio["title"] = title
            if artist: audio["artist"] = artist
            if album: audio["album"] = album
            if year: audio["date"] = str(year)
            if genre: audio["genre"] = genre
            
            if cover_path and os.path.exists(cover_path):
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3 # Front cover
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                with open(cover_path, "rb") as img:
                    pic.data = img.read()
                audio.add_picture(pic)
            audio.save()
        else:
            raise ValueError(f"Ekstensi {ext} tidak didukung")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.btn_auto.configure(text="🚀 Auto-Fix (Semua)")
            return
            
        # Update teks tombol Auto-Fix jika ada file terpilih
        if len(selected) > 0:
            self.btn_auto.configure(text=f"🚀 Auto-Fix ({len(selected)} Terpilih)")
            
        # Untuk panel Manual Editor (Kanan), hanya tampilkan file PERTAMA yang dipilih
        filepath = selected[0]
        self.selected_file = filepath
        
        # Reset Panel
        for ent in self.inputs.values():
            ent.delete(0, 'end')
        self.lbl_cover.configure(image="", text="Loading...")
        self.current_cover_path = None
        self.photo_preview = None
        self.root.update()
        
        # Load tags via util method
        meta = self._read_metadata(filepath)
        if meta["title"]: self.inputs["Judul"].insert(0, meta["title"])
        if meta["artist"]: self.inputs["Artis"].insert(0, meta["artist"])
        if meta["album"]: self.inputs["Album"].insert(0, meta["album"])
        if meta["genre"]: self.inputs["Genre"].insert(0, meta["genre"])
        
        if meta["cover_data"]:
            try:
                pil_img = Image.open(BytesIO(meta["cover_data"])).convert("RGB")
                self.photo_preview = ctk.CTkImage(light_image=pil_img, size=(160, 160))
                self.lbl_cover.configure(image=self.photo_preview, text="")
            except Exception:
                self.lbl_cover.configure(text="Error render Cover")
        else:
            self.lbl_cover.configure(text="Tidak ada Cover")
            
        # Fallback to Treeview values if empty
        if not self.inputs["Judul"].get(): self.inputs["Judul"].insert(0, self.tree.item(filepath, "values")[2])
        if not self.inputs["Artis"].get(): self.inputs["Artis"].insert(0, self.tree.item(filepath, "values")[1])
        
    def browse_cover(self):
        if not self.selected_file: return
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.current_cover_path = file_path
            pil_img = Image.open(file_path).convert("RGB")
            self.photo_preview = ctk.CTkImage(light_image=pil_img, size=(160, 160))
            self.lbl_cover.configure(image=self.photo_preview, text="")
            
    def save_manual(self):
        if not self.selected_file: return
        
        artist = self.inputs["Artis"].get().strip()
        title = self.inputs["Judul"].get().strip()
        album = self.inputs["Album"].get().strip()
        genre = self.inputs["Genre"].get().strip()
        
        try:
            # Inject tags using util method
            self._inject_metadata(self.selected_file, title, artist, album, None, genre, self.current_cover_path)
            
            ext = os.path.splitext(self.selected_file)[1]
            new_filename = clean_filename(f"{artist} - {title}{ext}")
            directory = os.path.dirname(self.selected_file)
            new_filepath = os.path.join(directory, new_filename)
            
            if self.selected_file != new_filepath:
                if os.path.exists(new_filepath):
                    new_filename = clean_filename(f"{artist} - {title} (1){ext}")
                    new_filepath = os.path.join(directory, new_filename)
                os.rename(self.selected_file, new_filepath)
                
            rel_path = os.path.relpath(new_filepath, self.target_dir)
            self._update_row(self.selected_file, new_filepath, rel_path, artist, title, "✅ SUKSES (Manual)")
            self.selected_file = new_filepath
            self.music_files = glob.glob(os.path.join(self.target_dir, "**", "*.mp3"), recursive=True)
            
            self.lbl_status.configure(text=f"Berhasil menyimpan & rename: {new_filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan: {e}")

    def run_auto_fix(self):
        if not self.target_dir: return
        if not self.music_files:
            messagebox.showwarning("Peringatan", "Tidak ada file musik untuk diproses.")
            return
            
        # Cek apakah ada file yang diselect di Treeview
        selected_iids = self.tree.selection()
        
        # Buat daftar file yang akan diproses
        files_to_process = []
        if selected_iids:
            files_to_process = list(selected_iids)
        else:
            files_to_process = self.music_files
            
        self.btn_auto.configure(state="disabled", text="⏳ Memproses...")
        self.btn_folder.configure(state="disabled")
        
        # Tampilkan progress bar
        self.frame_progress.pack(fill="x", padx=15, pady=(0, 5), before=self.tree_frame)
        self.progress_bar.set(0)
        self.lbl_progress_detail.configure(text="Mempersiapkan...")
        self.lbl_progress_stats.configure(text="")
        
        threading.Thread(target=self._auto_fix_worker, args=(files_to_process,), daemon=True).start()

    def _update_progress(self, current, total, detail_text, stats_text):
        """Update progress bar dan label dari main thread."""
        self.progress_bar.set(current / total if total > 0 else 0)
        self.lbl_progress_detail.configure(text=detail_text)
        self.lbl_progress_stats.configure(text=stats_text)
        self.lbl_status.configure(text=f"Memproses {current}/{total}...")

    def _fetch_from_itunes(self, artist, title, cover_dir):
        """Coba cari metadata dari iTunes. Return cache_entry atau None."""
        try:
            term = f"{artist} {title}".strip().replace(' ', '+')
            url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=1"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.json()['resultCount'] > 0:
                item = resp.json()['results'][0]
                cover_url = item.get("artworkUrl100", "").replace("100x100bb.jpg", "600x600bb.jpg")
                cover_path = None
                if cover_url:
                    safe_name = "".join([c for c in f"{item.get('artistName')} - {item.get('trackName')}" if c.isalnum() or c==' ']).rstrip()
                    cover_path = os.path.join(cover_dir, f"{safe_name}.jpg")
                    if not os.path.exists(cover_path):
                        img_data = requests.get(cover_url, timeout=10).content
                        with open(cover_path, "wb") as f: f.write(img_data)
                return {
                    "artist": item.get("artistName"), "title": item.get("trackName"),
                    "album": item.get("collectionName"), "year": item.get("releaseDate", "")[:4],
                    "genre": item.get("primaryGenreName"), "local_cover": cover_path,
                    "source": "iTunes"
                }
        except Exception:
            pass
        return None

    def _fetch_from_musicbrainz(self, artist, title, cover_dir):
        """Coba cari metadata dari MusicBrainz sebagai fallback. Return cache_entry atau None."""
        try:
            from musicbrainz_client import search_track
            result = search_track(artist, title)
            if not result:
                return None
                
            cover_path = None
            if result.get("cover_url"):
                safe_name = "".join([c for c in f"{result['artist']} - {result['title']}" if c.isalnum() or c==' ']).rstrip()
                cover_path = os.path.join(cover_dir, f"{safe_name}.jpg")
                if not os.path.exists(cover_path):
                    img_data = requests.get(result["cover_url"], timeout=10).content
                    with open(cover_path, "wb") as f: f.write(img_data)
                    
            return {
                "artist": result.get("artist"), "title": result.get("title"),
                "album": result.get("album"), "year": result.get("year"),
                "genre": result.get("genre"), "local_cover": cover_path,
                "source": "MusicBrainz"
            }
        except Exception:
            pass
        return None
        
    def _auto_fix_worker(self, target_files):
        cover_dir = os.path.join(self.target_dir, "covers")
        os.makedirs(cover_dir, exist_ok=True)
        
        total = len(target_files)
        count_success = 0
        count_fail = 0
        count_skip = 0
        
        for idx, fp in enumerate(target_files, 1):
            fname = os.path.basename(fp)
            
            # Cek status file di data internal
            current_status = ""
            for iid, vals in self._all_rows:
                if iid == fp:
                    current_status = vals[3]
                    break
                    
            if "✅ Sudah Lengkap" in current_status:
                count_skip += 1
                stats = f"✅ {count_success}  ⏭️ {count_skip}  ❌ {count_fail}"
                self.root.after(0, self._update_progress, idx, total, f"⏭️ Skip (File sudah lengkap): {fname}", stats)
                continue
                
            parsed = parse_filename(fp)
            
            if not parsed:
                count_skip += 1
                stats = f"✅ {count_success}  ⏭️ {count_skip}  ❌ {count_fail}"
                self.root.after(0, self._update_progress, idx, total, f"⏭️ Skip (Regex gagal): {fname}", stats)
                self.root.after(0, self._update_row, fp, fp, fname, "", "", "❌ Gagal Regex")
                continue
                
            artist, title = parsed.get('artist', ''), parsed.get('title', '')
            if not artist or not title:
                count_skip += 1
                stats = f"✅ {count_success}  ⏭️ {count_skip}  ❌ {count_fail}"
                self.root.after(0, self._update_progress, idx, total, f"⏭️ Skip (data kosong): {fname}", stats)
                continue
            
            stats = f"✅ {count_success}  ⏭️ {count_skip}  ❌ {count_fail}"
            self.root.after(0, self._update_progress, idx, total, f"[{idx}/{total}] 🔍 {artist} - {title}", stats)
                
            key = f"{artist.lower()}||{title.lower()}"
            cache_entry = self.cache_db.get(key)
            source_label = "Cache"
            
            # Cascade: Cache → iTunes → MusicBrainz (Lengkapi Cover)
            if not cache_entry:
                cache_entry = self._fetch_from_itunes(artist, title, cover_dir)
                if cache_entry:
                    # VALIDASI KEMIRIPAN
                    if not is_similar(artist, cache_entry["artist"]) or not is_similar(title, cache_entry["title"]):
                        cache_entry = None # Tolak jika hasilnya terlalu berbeda (bukan lagu yang sama)
                    else:
                        source_label = "iTunes"
                        
                        # Jika iTunes sukses TAPI tidak ada cover, coba cari cover-nya di MusicBrainz!
                        if not cache_entry.get("local_cover"):
                            mb_data = self._fetch_from_musicbrainz(artist, title, cover_dir)
                            if mb_data and mb_data.get("local_cover"):
                                cache_entry["local_cover"] = mb_data["local_cover"]
                                source_label = "iTunes + MusicBrainz"
                                
                        self.cache_db[key] = cache_entry
                    
            if not cache_entry:
                cache_entry = self._fetch_from_musicbrainz(artist, title, cover_dir)
                if cache_entry:
                    # VALIDASI KEMIRIPAN
                    if not is_similar(artist, cache_entry["artist"]) or not is_similar(title, cache_entry["title"]):
                        cache_entry = None
                    else:
                        source_label = "MusicBrainz"
                        self.cache_db[key] = cache_entry
                    
            status_text = f"✅ Sukses ({source_label})"
            try:
                db_album = cache_entry.get("album") if cache_entry else None
                db_year = cache_entry.get("year") if cache_entry else None
                db_genre = cache_entry.get("genre") if cache_entry else None
                db_cover = cache_entry.get("local_cover") if cache_entry else None
                
                # AUTO-CORRECT TYPO
                final_artist = cache_entry.get("artist") if cache_entry and cache_entry.get("artist") else artist
                final_title = cache_entry.get("title") if cache_entry and cache_entry.get("title") else title
                
                if cache_entry and not (db_cover and os.path.exists(db_cover)):
                    status_text = f"⚠️ Tanpa Cover ({source_label})"
                elif not cache_entry:
                    status_text = "⚠️ Metadata Tidak Ditemukan"
                    
                self._inject_metadata(fp, final_title, final_artist, db_album, db_year, db_genre, db_cover)
                
                ext = os.path.splitext(fp)[1]
                new_fname = clean_filename(f"{final_artist} - {final_title}{ext}")
                directory = os.path.dirname(fp)
                new_fp = os.path.join(directory, new_fname)
                if fp != new_fp:
                    if os.path.exists(new_fp):
                        new_fname = clean_filename(f"{final_artist} - {final_title} (1){ext}")
                        new_fp = os.path.join(directory, new_fname)
                    os.rename(fp, new_fp)
                
                count_success += 1
                rel_path = os.path.relpath(new_fp, self.target_dir)
                self.root.after(0, self._update_row, fp, new_fp, rel_path, final_artist, final_title, status_text)
            except mutagen.MutagenError as e:
                # Menangkap error spesifik "can't sync to MPEG frame" dan file korup lainnya
                count_fail += 1
                rel_path = os.path.relpath(fp, self.target_dir)
                self.root.after(0, self._update_row, fp, fp, rel_path, artist, title, "❌ File Korup/Bukan MP3 Asli")
            except Exception as e:
                count_fail += 1
                rel_path = os.path.relpath(fp, self.target_dir)
                self.root.after(0, self._update_row, fp, fp, rel_path, artist, title, f"❌ Error: {str(e)[:30]}")
            
            # Update stats setelah proses file selesai
            stats = f"✅ {count_success}  ⏭️ {count_skip}  ❌ {count_fail}"
            self.root.after(0, self._update_progress, idx, total, f"[{idx}/{total}] ✔ {artist} - {title}", stats)
                
        # Simpan Cache
        with open(os.path.join(self.target_dir, "music_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(self.cache_db, f, indent=4)
            
        self.root.after(0, self._finish_auto_fix, count_success, count_skip, count_fail, total)

    def _finish_auto_fix(self, success=0, skip=0, fail=0, total=0):
        self.progress_bar.set(1.0)
        self.lbl_progress_detail.configure(text="Selesai!")
        self.lbl_status.configure(text="Auto-Fix Selesai!")
        self.btn_auto.configure(state="normal", text="🚀 Auto-Fix (Smart)")
        self.btn_folder.configure(state="normal")
        
        summary = (
            f"Proses Auto-Fix selesai!\n\n"
            f"📊 Ringkasan ({total} file):\n"
            f"  ✅ Sukses: {success}\n"
            f"  ⏭️ Dilewati: {skip}\n"
            f"  ❌ Gagal: {fail}"
        )
        messagebox.showinfo("Selesai", summary)

    def _update_row(self, old_id, new_id, new_fname, artist, title, status):
        # Update data internal _all_rows
        new_vals = (new_fname, artist, title, status)
        for i, (iid, vals) in enumerate(self._all_rows):
            if iid == old_id:
                self._all_rows[i] = (new_id, new_vals)
                break
        else:
            # Row baru (misalnya dari manual save)
            self._all_rows.append((new_id, new_vals))
        
        # Update treeview langsung (jika row visible di filter saat ini)
        if self.tree.exists(old_id):
            self.tree.delete(old_id)
        self.tree.insert("", "end", iid=new_id, values=new_vals)
        
        # Update counter
        visible = len(self.tree.get_children())
        self.lbl_filter_count.configure(text=f"{visible} / {len(self._all_rows)} file")

if __name__ == "__main__":
    # Set AppUserModelID SEBELUM window dibuat agar icon taskbar Windows benar
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('hyo.musicfilter.app.1')
    except Exception:
        pass

    app = ctk.CTk()
    gui = HyoMusicModernGUI(app)
    app.mainloop()
