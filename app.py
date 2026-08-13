import os
import glob
import re
import json
import time
import requests
import threading
from tkinter import filedialog, messagebox, ttk
from io import BytesIO

try:
    from PIL import Image, ImageTk
    import customtkinter as ctk
except ImportError:
    pass

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TCON, APIC, TALB, TDRC, error
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
            
    return None

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
        
        self.btn_auto = ctk.CTkButton(self.toolbar, text="🚀 Auto-Fix (Smart)", font=("Inter", 13, "bold"), 
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
        
        # Baris 1: Search box + label counter
        self.frame_search = ctk.CTkFrame(self.frame_filter, fg_color="transparent")
        self.frame_search.pack(fill="x", pady=(0, 6))
        
        ctk.CTkLabel(self.frame_search, text="🔍", font=("Inter", 14)).pack(side="left", padx=(0, 4))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.entry_search = ctk.CTkEntry(self.frame_search, textvariable=self.search_var,
                                         placeholder_text="Cari file, artis, atau judul...",
                                         height=30, font=("Inter", 11))
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.lbl_filter_count = ctk.CTkLabel(self.frame_search, text="0 file", 
                                             font=("Inter", 11, "bold"), text_color="#888")
        self.lbl_filter_count.pack(side="right")
        
        # Baris 2: Tombol-tombol filter
        self.frame_filter_buttons = ctk.CTkFrame(self.frame_filter, fg_color="transparent")
        self.frame_filter_buttons.pack(fill="x")
        
        self.active_filter = "all"  # State filter aktif
        self.filter_buttons = {}    # Referensi tombol untuk update style
        
        filter_defs = [
            ("all",        "📋 Semua"),
            ("az",         "🔤 A → Z"),
            ("za",         "🔤 Z → A"),
            ("success",    "✅ Sukses"),
            ("no_cover",   "⚠️ Tanpa Cover"),
            ("fail_regex", "❌ Gagal Regex"),
            ("pending",    "⏳ Belum Proses"),
        ]
        
        for key, label in filter_defs:
            btn = ctk.CTkButton(
                self.frame_filter_buttons, text=label, font=("Inter", 11),
                height=28, corner_radius=14,
                fg_color="#333333" if key != "all" else "#1f538d",
                hover_color="#444444",
                command=lambda k=key: self._set_filter(k)
            )
            btn.pack(side="left", padx=(0, 5))
            self.filter_buttons[key] = btn
        
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
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", style="Treeview")
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
        self.music_files = glob.glob(os.path.join(self.target_dir, "*.mp3"))
        
        # Simpan semua row ke data internal
        self._all_rows = []
        for fp in self.music_files:
            fname = os.path.basename(fp)
            parsed = parse_filename(fp)
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
    
    def _set_filter(self, filter_key):
        """Ganti filter aktif dan re-render tabel."""
        self.active_filter = filter_key
        self._apply_filter()
    
    def _apply_filter(self, *args):
        """Filter dan render ulang tabel berdasarkan filter aktif + search query."""
        # Update style tombol: aktif = biru, lainnya = abu
        for key, btn in self.filter_buttons.items():
            if key == self.active_filter:
                btn.configure(fg_color="#1f538d")
            else:
                btn.configure(fg_color="#333333")
        
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
            if f == "success" and "✅" not in status:
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
                
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        filepath = selected[0]
        self.selected_file = filepath
        
        # Reset Panel
        for ent in self.inputs.values():
            ent.delete(0, 'end')
        self.lbl_cover.configure(image="", text="Loading...")
        self.current_cover_path = None
        self.photo_preview = None
        self.root.update()
        
        # Load ID3
        try:
            audio = MP3(filepath, ID3=ID3)
            if audio.tags:
                if 'TIT2' in audio: self.inputs["Judul"].insert(0, audio.tags['TIT2'].text[0])
                if 'TPE1' in audio: self.inputs["Artis"].insert(0, audio.tags['TPE1'].text[0])
                if 'TALB' in audio: self.inputs["Album"].insert(0, audio.tags['TALB'].text[0])
                if 'TCON' in audio: self.inputs["Genre"].insert(0, audio.tags['TCON'].text[0])
                
                apic = audio.tags.getall('APIC')
                if apic:
                    img_data = apic[0].data
                    pil_img = Image.open(BytesIO(img_data)).convert("RGB")
                    self.photo_preview = ctk.CTkImage(light_image=pil_img, size=(160, 160))
                    self.lbl_cover.configure(image=self.photo_preview, text="")
                else:
                    self.lbl_cover.configure(text="Tidak ada Cover")
            else:
                self.lbl_cover.configure(text="Tidak ada Cover")
        except:
            self.lbl_cover.configure(text="Error load Cover")
            
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
            audio = MP3(self.selected_file, ID3=ID3)
            try: audio.delete()
            except error: pass
            
            audio.tags = ID3()
            if title: audio.tags.add(TIT2(encoding=3, text=title))
            if artist: audio.tags.add(TPE1(encoding=3, text=artist))
            if album: audio.tags.add(TALB(encoding=3, text=album))
            if genre: audio.tags.add(TCON(encoding=3, text=genre))
            
            if self.current_cover_path:
                with open(self.current_cover_path, "rb") as img:
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()))
            
            audio.save(v2_version=3)
            
            ext = os.path.splitext(self.selected_file)[1]
            new_filename = clean_filename(f"{artist} - {title}{ext}")
            directory = os.path.dirname(self.selected_file)
            new_filepath = os.path.join(directory, new_filename)
            
            if self.selected_file != new_filepath:
                if os.path.exists(new_filepath):
                    new_filename = clean_filename(f"{artist} - {title} (1){ext}")
                    new_filepath = os.path.join(directory, new_filename)
                os.rename(self.selected_file, new_filepath)
                
            self._update_row(self.selected_file, new_filepath, new_filename, artist, title, "✅ SUKSES (Manual)")
            self.selected_file = new_filepath
            self.music_files = glob.glob(os.path.join(self.target_dir, "*.mp3"))
            
            self.lbl_status.configure(text=f"Berhasil menyimpan & rename: {new_filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan: {e}")

    def run_auto_fix(self):
        if not self.target_dir: return
        if not self.music_files:
            messagebox.showwarning("Peringatan", "Tidak ada file musik untuk diproses.")
            return
        self.btn_auto.configure(state="disabled", text="⏳ Memproses...")
        self.btn_folder.configure(state="disabled")
        
        # Tampilkan progress bar
        self.frame_progress.pack(fill="x", padx=15, pady=(0, 5), before=self.tree_frame)
        self.progress_bar.set(0)
        self.lbl_progress_detail.configure(text="Mempersiapkan...")
        self.lbl_progress_stats.configure(text="")
        
        threading.Thread(target=self._auto_fix_worker, daemon=True).start()

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

    def _fetch_from_spotify(self, artist, title, cover_dir):
        """Coba cari metadata dari Spotify sebagai fallback. Return cache_entry atau None."""
        try:
            from spotify_client import is_configured, search_track
            if not is_configured():
                return None
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
                "source": "Spotify"
            }
        except Exception:
            pass
        return None
        
    def _auto_fix_worker(self):
        cover_dir = os.path.join(self.target_dir, "covers")
        os.makedirs(cover_dir, exist_ok=True)
        
        total = len(self.music_files)
        count_success = 0
        count_fail = 0
        count_skip = 0
        
        for idx, fp in enumerate(self.music_files, 1):
            fname = os.path.basename(fp)
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
            
            # Cascade: Cache → iTunes → Spotify
            if not cache_entry:
                cache_entry = self._fetch_from_itunes(artist, title, cover_dir)
                if cache_entry:
                    source_label = "iTunes"
                    self.cache_db[key] = cache_entry
                    
            if not cache_entry:
                cache_entry = self._fetch_from_spotify(artist, title, cover_dir)
                if cache_entry:
                    source_label = "Spotify"
                    self.cache_db[key] = cache_entry
                    
            status_text = f"✅ Sukses ({source_label})"
            try:
                audio = MP3(fp, ID3=ID3)
                try: audio.delete()
                except error: pass
                
                audio.tags = ID3()
                audio.tags.add(TIT2(encoding=3, text=title))
                audio.tags.add(TPE1(encoding=3, text=artist))
                
                if cache_entry:
                    if cache_entry.get("album"): audio.tags.add(TALB(encoding=3, text=cache_entry["album"]))
                    if cache_entry.get("year"): audio.tags.add(TDRC(encoding=3, text=str(cache_entry["year"])))
                    if cache_entry.get("genre"): audio.tags.add(TCON(encoding=3, text=cache_entry["genre"]))
                    if cache_entry.get("local_cover") and os.path.exists(cache_entry["local_cover"]):
                        with open(cache_entry["local_cover"], "rb") as img:
                            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()))
                    else:
                        status_text = f"⚠️ Tanpa Cover ({source_label})"
                else:
                    status_text = "⚠️ Metadata Tidak Ditemukan"
                
                audio.save(v2_version=3)
                
                ext = os.path.splitext(fp)[1]
                new_fname = clean_filename(f"{artist} - {title}{ext}")
                new_fp = os.path.join(self.target_dir, new_fname)
                if fp != new_fp:
                    if os.path.exists(new_fp):
                        new_fname = clean_filename(f"{artist} - {title} (1){ext}")
                        new_fp = os.path.join(self.target_dir, new_fname)
                    os.rename(fp, new_fp)
                
                count_success += 1
                self.root.after(0, self._update_row, fp, new_fp, new_fname, artist, title, status_text)
            except Exception as e:
                count_fail += 1
                self.root.after(0, self._update_row, fp, fp, fname, artist, title, f"❌ Error: {str(e)[:30]}")
            
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
