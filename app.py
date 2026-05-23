"""
Streamlit UI untuk Chatbot Rule-Based Teknik Informatika UNRI.
Jalankan dengan: streamlit run app.py
"""

import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# ==========================================
# KONFIGURASI
# ==========================================
BASE_PATH = Path(__file__).parent  # folder tempat app.py berada

st.set_page_config(
    page_title="Chatbot TI UNRI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ==========================================
# CORE CHATBOT
# ==========================================
class MasterRuleBasedChatbot:
    def __init__(self, default_year: str = "2025"):
        # 1. Load semua data JSON
        self.skripsi_data = self.load_json(BASE_PATH / "data_skripsi_advanced.json", [])
        self.kurikulum_data = self.load_json(BASE_PATH / "kurikulum.json", {})

        # Kalender Akademik gabungan 2 tahun ajaran
        kalender_2526 = self.load_json(BASE_PATH / "kalender_akademik.json", [])
        kalender_2627 = self.load_json(BASE_PATH / "kalender_akademik_2627_intents.json", [])
        for it in kalender_2526:
            it.setdefault("tahun_ajaran", "2025/2026")
        for it in kalender_2627:
            it.setdefault("tahun_ajaran", "2026/2027")
        self.kalender_data = kalender_2526 + kalender_2627

        self.dosen_data = self.load_json(BASE_PATH / "dosen.json", [])

        # Informasi Umum (format: {"intents": [...]})
        informasi_umum_raw = self.load_json(BASE_PATH / "informasi_umum_chatbot.json", {})
        self.informasi_umum_data = self._extract_intents(informasi_umum_raw)

        # Setelah Sidang (format: {"intents": [...]})
        setelah_sidang_map_raw = self.load_json(BASE_PATH / "after_sidang_map_biru_merah_chatbot.json", {})
        setelah_sidang_sitei_raw = self.load_json(BASE_PATH / "after_sidang_sitei_chatbot.json", {})
        self.setelah_sidang_data = (
            self._extract_intents(setelah_sidang_map_raw)
            + self._extract_intents(setelah_sidang_sitei_raw)
        )

        # SOP Jurusan & SOP Skripsi
        self.sop_jte_data = self.load_json(BASE_PATH / "sop_jte_fixed.json", [])
        self.sop_skripsi_data = self.load_json(BASE_PATH / "sop_skripsi.json", [])

        # 2. Aturan Rule-Based untuk Skripsi
        self.skripsi_rules = {
            "Format Umum": ["format umum", "format skripsi", "pedoman skripsi", "aturan format", "aturan penulisan", "format penulisan"],
            "Kertas": ["kertas", "ukuran kertas", "jenis kertas", "hvs", "a4", "70 gsm", "putih polos", "kertas skripsi"],
            "Pengetikan": ["pengetikan", "aturan pengetikan", "format pengetikan", "ketikan skripsi", "format naskah", "tata tulis"],
            "Cetakan naskah": ["cetakan naskah", "cetak naskah", "satu sisi", "single side", "bolak balik", "tidak bolak balik", "cetak skripsi", "print skripsi"],
            "Jenis huruf": ["jenis huruf", "font", "ukuran font", "ukuran huruf", "huruf skripsi", "times new roman", "tnr", "12 pt", "font skripsi", "jenis font", "symbol", "huruf yunani"],
            "Bilangan dan satuan": ["bilangan dan satuan", "bilangan", "satuan", "angka dan satuan", "bilangan desimal", "angka desimal", "koma desimal", "satuan resmi", "singkatan satuan"],
            "Jarak baris": ["jarak baris", "spasi", "line spacing", "jarak paragraf", "spasi paragraf", "spasi abstrak", "spasi daftar isi", "spasi daftar tabel", "spasi daftar gambar", "spasi tabel", "spasi gambar", "spasi daftar pustaka", "jarak judul", "spacing"],
            "Batas tepi": ["batas tepi", "margin", "batas margin", "jarak tepi", "tepi atas", "tepi bawah", "tepi kiri", "tepi kanan", "margin skripsi", "ukuran margin", "kiri kanan", "atas bawah"],
            "Pengisian ruangan": ["pengisian ruangan", "halaman penuh", "ruang kosong", "bagian kosong", "isi halaman", "batas kiri kanan", "naskah penuh", "halaman naskah"],
            "Permulaan kalimat": ["permulaan kalimat", "awal kalimat", "kalimat diawali angka", "kalimat diawali lambang", "kalimat diawali rumus", "angka awal kalimat", "singkatan awal kalimat", "narasi bilangan"],
            "Penulisan kutipan langsung dan kutipan tidak langsung": ["kutipan", "kutipan langsung", "kutipan tidak langsung", "penulisan kutipan", "sitasi", "citation", "nama pengarang", "tahun terbit", "halaman kutipan", "tanda petik", "apa style"],
            "Judul Bab, Sub Judul dan Anak Sub Judul": ["judul bab", "sub judul", "anak sub judul", "judul subbab", "subbab", "anak subbab", "heading", "judul kapital", "judul bold", "judul tebal", "format judul", "format sub judul"],
            "Angka Romawi": ["angka romawi", "romawi", "roman numeral", "nomor bab", "bab i", "romawi besar", "romawi kecil", "halaman awal", "penomoran halaman awal", "i ii iii"],
            "Angka Latin": ["angka latin", "nomor sub judul", "nomor subbab", "nomor anak sub judul", "nomor tabel", "nomor gambar", "nomor persamaan", "penomoran tabel", "penomoran gambar", "penomoran persamaan", "1.1", "1.1.1"],
            "Penomoran": ["penomoran", "nomor halaman", "nomor skripsi", "letak nomor halaman", "halaman tengah bawah", "numbering", "page number"],
            "Bentuk kalimat": ["bentuk kalimat", "kalimat pasif", "orang pertama", "orang kedua", "aku", "saya", "kami", "penulis", "kata ganti", "ucapan terima kasih"],
            "Bahasa": ["bahasa", "bahasa indonesia", "bahasa baku", "ejaan", "puebi", "istilah asing", "kata asing", "bahasa asing", "subyek predikat", "kalimat baku"],
            "Bagian Awal": ["bagian awal", "awal skripsi", "halaman awal", "susunan awal", "urutan bagian awal"],
            "Halaman Sampul": ["halaman sampul", "sampul", "cover", "cover skripsi", "warna sampul", "karton", "buffalo", "plastik sampul", "judul sampul", "logo universitas", "lambang universitas", "punggung skripsi"],
            "Halaman Judul": ["halaman judul", "judul skripsi", "lembar judul", "kertas putih", "tujuan karya ilmiah", "informasi tambahan", "format halaman judul", "lampiran iii"],
            "Halaman Pernyataan Orisinalitas": ["halaman pernyataan orisinalitas", "orisinalitas", "originalitas", "pernyataan asli", "keaslian skripsi", "karya sendiri", "plagiarisme", "lembar orisinalitas", "justify alignment"],
            "Halaman Pengesahan": ["halaman pengesahan", "lembar pengesahan", "pengesahan skripsi", "tanda tangan pembimbing", "dosen pembimbing", "koordinator program studi", "ketua jurusan", "spasi tunggal", "margin pengesahan"],
            "Prakata": ["prakata", "kata pengantar", "ucapan terima kasih", "terima kasih", "format prakata", "halaman prakata", "judul prakata", "pihak yang membantu"],
            "Halaman Pernyataan Persetujuan Publikasi Karya Ilmiah untuk": ["halaman pernyataan persetujuan publikasi", "persetujuan publikasi", "publikasi karya ilmiah", "kepentingan akademis", "hak cipta", "alihmedia", "menyimpan skripsi", "mempublikasikan skripsi", "lembar publikasi"],
            "Abstrak": ["abstrak", "abstract", "ringkasan", "ikhtisar", "inti skripsi", "kata kunci", "keyword", "maksimal 250 kata", "bahasa indonesia dan inggris", "metode penelitian", "hasil penelitian"],
            "Daftar Isi": ["daftar isi", "isi skripsi", "table of contents", "nomor halaman", "subbab daftar isi", "format daftar isi", "spasi daftar isi", "judul daftar isi", "lampiran x"],
            "Daftar Tabel, Daftar Gambar, dan Daftar Lain": ["daftar tabel", "daftar gambar", "daftar lampiran", "daftar simbol", "daftar notasi", "daftar lain", "list of tables", "list of figures", "nama tabel", "nama gambar", "title case", "spasi daftar gambar", "spasi daftar tabel"],
            "Bagian Isi": ["bagian isi", "isi skripsi", "bab skripsi", "pendahuluan", "tinjauan literatur", "bab utama", "kesimpulan dan saran", "susunan bab", "struktur skripsi", "jumlah bab"],
            "Daftar Pustaka": ["daftar pustaka", "pustaka", "referensi", "daftar referensi", "apa style", "american psychology association", "sitasi", "sumber kutipan", "penulisan referensi", "urutan alfabetis", "judul referensi", "italic referensi", "dafpus"],
            "Gambar": ["gambar", "ilustrasi", "grafik", "diagram", "denah", "peta", "bagan", "diagram alir", "potret", "judul gambar", "nomor gambar", "sumber gambar", "format gambar", "caption gambar", "peletakan gambar"],
            "Tabel": ["tabel", "format tabel", "judul tabel", "nomor tabel", "sumber tabel", "isi tabel", "kolom tabel", "kepala tabel", "tabel sambungan", "caption tabel", "spasi tabel", "tabel landscape", "tabel landskap", "peletakan tabel"],
            "Lambang": ["lambang", "lambang variabel", "simbol", "variabel", "abjad latin", "huruf yunani", "subskrip", "superskrip", "cetak bawah", "cetak atas", "lambang rumus"],
            "Satuan dan Singkatan": ["satuan dan singkatan", "satuan", "singkatan", "satuan si", "s.i", "singkatan satuan", "lambang satuan", "satuan baku", "mili", "centi", "kilo", "mega", "mikro", "italic satuan"],
            "Angka": ["angka", "bilangan", "penulisan angka", "tanda desimal", "tanda ribuan", "koma desimal", "titik ribuan", "persentase", "tanggal", "waktu", "angka awal kalimat", "bilangan pecahan", "angka kurang dari sepuluh"],
            "Cetak Miring/Italic": ["cetak miring", "italic", "huruf miring", "miring", "kata asing", "istilah asing", "bahasa asing", "ukuran huruf miring", "format italic"],
            "Penulisan Rumus dan Perhitungan Numerik": ["penulisan rumus", "rumus", "perhitungan numerik", "formula", "persamaan", "nomor rumus", "nomor persamaan", "rumus panjang", "operasi aritmetik", "tanda kurung", "operator kali", "centered", "posisi rumus"],
            "Sampul CD": ["sampul cd", "cover cd", "label cd", "cd skripsi", "judul cd", "logo universitas riau", "identitas cd", "nama prodi", "nama jurusan", "lampiran xvii"],
            "Penamaan File CD": ["penamaan file cd", "nama file cd", "file cd", "format file cd", "softcopy", "pdf", "file pdf", "kode jurusan", "kode prodi", "nama bab", "tahun skripsi", "portable digital format"],
            "Susunan File CD": ["susunan file cd", "folder cd", "urutan file cd", "struktur file cd", "bagian awal cd", "bagian isi cd", "bagian akhir cd", "full version", "referensi pdf", "lampiran pdf", "softcopy skripsi"]
        }

        # 3. Variabel & Konfigurasi Kurikulum
        self.kurikulum_year = default_year
        self.sem_map_2018 = {
            "Keahlian I": "Semester 5",
            "Keahlian II": "Semester 6",
            "Keahlian III": "Semester 6",
            "Keahlian IV": "Semester 7",
            "Keahlian V": "Semester 7",
        }

        self.course_names = []
        self.course_details = {}
        self.group_names = []
        self.spec_map = {}

        if not self.load_curriculum(self.kurikulum_year):
            if self.kurikulum_data:
                first_key = list(self.kurikulum_data.keys())[0]
                self.load_curriculum(first_key)

    # ------------------------------------------
    # LOADERS
    # ------------------------------------------
    def load_json(self, filepath, default_value):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default_value
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ File {filepath.name} rusak formatnya: {e}")
            return default_value

    def _extract_intents(self, raw):
        if isinstance(raw, dict):
            return raw.get("intents", [])
        if isinstance(raw, list):
            return raw
        return []

    # ------------------------------------------
    # KURIKULUM
    # ------------------------------------------
    def load_curriculum(self, year):
        if year not in self.kurikulum_data:
            return False

        self.kurikulum_year = year
        data_active = self.kurikulum_data[year]

        self.course_names = []
        self.course_details = {}
        self.group_names = []
        self.spec_map = {}

        for group in data_active:
            g_name = group.get("group_name", "Unknown")
            self.group_names.append(g_name)
            is_semester = "SEMESTER" in g_name.upper()

            for course in group.get("courses", []):
                c_name = course.get("name", "")
                c_no = course.get("no", "")

                real_semester = g_name if is_semester else self.sem_map_2018.get(str(c_no), "Semester Tidak Diketahui")

                if c_name:
                    self.course_names.append(c_name)
                    self.course_details[c_name] = {
                        "sks": course.get("sks", "0"),
                        "group": g_name,
                        "semester_info": real_semester,
                        "code": course.get("code", "-"),
                        "no_label": c_no,
                    }

                if self.kurikulum_year == "2018" and not is_semester and "Keahlian" in str(c_no):
                    if c_no not in self.spec_map:
                        self.spec_map[c_no] = []
                    self.spec_map[c_no].append({
                        "course_name": c_name,
                        "concentration": g_name,
                        "semester": self.sem_map_2018.get(c_no, ""),
                    })
        return True

    def resolve_concentration(self, user_query):
        text = self.normalize_text(user_query)
        aliases = {
            "Rekayasa Perangkat Lunak": ["rekayasa perangkat lunak", "rpl", "perangkat lunak", "software"],
            "Komputasi Cerdas dan Visualisasi": ["komputasi cerdas dan visualisasi", "komputasi cerdas", "visualisasi", "kcv"],
            "Komputasi Berbasis Jaringan": ["komputasi berbasis jaringan", "jaringan", "kbj"],
        }
        for group_name, group_aliases in aliases.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in group_aliases):
                return group_name
        for group_name in self.group_names:
            if not group_name.upper().startswith("SEMESTER") and self.normalize_text(group_name) in text:
                return group_name
        return None

    def get_keahlian_course_response(self, user_query):
        if self.kurikulum_year != "2018":
            return None

        text = self.normalize_text(user_query)
        roman_match = re.search(r"\bkeahlian\s+(i{1,3}|iv|v|1|2|3|4|5)\b", text)
        if not roman_match:
            return None

        roman_map = {
            "1": "I", "i": "I",
            "2": "II", "ii": "II",
            "3": "III", "iii": "III",
            "4": "IV", "iv": "IV",
            "5": "V", "v": "V",
        }
        keahlian = f"Keahlian {roman_map.get(roman_match.group(1), roman_match.group(1).upper())}"
        concentration = self.resolve_concentration(user_query)
        options = self.spec_map.get(keahlian, [])

        if concentration:
            options = [opt for opt in options if opt["concentration"] == concentration]

        if not options:
            return None

        if len(options) == 1:
            opt = options[0]
            details = self.course_details.get(opt["course_name"], {})
            return (
                f"**Mata Kuliah {keahlian} - {opt['concentration']} (Kurikulum 2018):**\n\n"
                f"- Nama: **{opt['course_name']}**\n"
                f"- Kode: {details.get('code', '-')}\n"
                f"- SKS: {details.get('sks', '4')}\n"
                f"- Semester: {opt.get('semester', self.sem_map_2018.get(keahlian, '-'))}"
            )

        response = f"**Pilihan Mata Kuliah {keahlian} (Kurikulum 2018):**\n\n"
        for opt in options:
            details = self.course_details.get(opt["course_name"], {})
            response += (
                f"- **{opt['concentration']}**: {opt['course_name']} "
                f"({details.get('code', '-')}, {details.get('sks', '4')} SKS, {opt.get('semester', '-')})\n"
            )
        return response

    def get_semester_info(self, semester_num):
        target = f"SEMESTER {semester_num}"
        for group in self.kurikulum_data.get(self.kurikulum_year, []):
            if group["group_name"].upper() == target:
                total_sks = group.get("total_sks", "0")
                response = f"**{target} (Kurikulum {self.kurikulum_year})**\n\nTotal Beban: {total_sks} SKS\n\n"
                for c in group["courses"]:
                    if self.kurikulum_year == "2018" and c["name"] in self.spec_map:
                        response += f"**{c['name']} ({c['sks']} SKS) - Pilih Konsentrasi:**\n"
                        for opt in self.spec_map[c["name"]]:
                            response += f"   - {opt['course_name']} ({opt['concentration']})\n"
                    else:
                        response += f"- [{c.get('code', '-')}] {c['name']} ({c['sks']} SKS)\n"
                return response
        return f"Maaf, data semester {semester_num} tidak ditemukan di Kurikulum {self.kurikulum_year}."

    # ------------------------------------------
    # RULE-BASED SEARCH HELPERS
    # ------------------------------------------
    def normalize_text(self, text):
        text = str(text).lower()
        text = re.sub(r"[-_/]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _meaningful_tokens(self, text):
        stopwords = {
            "ada", "aja", "aku", "anda", "apa", "apakah", "atau", "bagaimana",
            "bagi", "berapa", "dan", "dengan", "di", "gimana", "ini", "itu",
            "ke", "kapan", "mau", "nya", "saja", "siapa", "untuk", "yang",
        }
        tokens = re.findall(r"[a-z0-9]+", self.normalize_text(text))
        return [token for token in tokens if len(token) > 1 and token not in stopwords]

    def _keyword_match_score(self, user_query, keyword):
        """
        Rule-based exact/token score.
        Keyword multi-kata diprioritaskan daripada keyword generik satu kata.
        """
        query_text = self.normalize_text(user_query)
        keyword_text = self.normalize_text(keyword)
        if not keyword_text:
            return 0

        query_tokens = set(self._meaningful_tokens(query_text))
        keyword_tokens = set(self._meaningful_tokens(keyword_text))
        if not keyword_tokens:
            return 0

        matched_tokens = keyword_tokens & query_tokens
        if re.search(rf"\b{re.escape(keyword_text)}\b", query_text):
            if len(keyword_tokens) == 1 and len(query_tokens) > 2:
                return 60
            return 100 + min(len(keyword_tokens), 5) * 5
        if len(matched_tokens) == len(keyword_tokens):
            return 85 + min(len(keyword_tokens), 5) * 4
        if len(keyword_tokens) >= 2 and len(matched_tokens) >= 2:
            return 55 + len(matched_tokens) * 8
        if len(keyword_tokens) == 1 and matched_tokens and len(query_tokens) <= 2:
            return 60
        return 0

    def _best_keyword_match(self, user_query, keywords):
        best_keyword = None
        highest_score = 0
        for keyword in keywords:
            score = self._keyword_match_score(user_query, keyword)
            if score > highest_score:
                highest_score = score
                best_keyword = keyword
        return best_keyword, highest_score

    def detect_tahun_ajaran(self, user_query):
        text = self.normalize_text(user_query)
        if re.search(r"\b(2025\s*2026|25\s*26)\b", text):
            return "2025/2026"
        if re.search(r"\b(2026\s*2027|26\s*27)\b", text):
            return "2026/2027"
        return None

    def detect_semester_type(self, user_query):
        text = self.normalize_text(user_query)
        if "ganjil" in text:
            return "ganjil"
        if "genap" in text:
            return "genap"
        return None

    def item_text(self, item):
        fields = [
            item.get("intent", ""),
            item.get("topik_utama", ""),
            item.get("sub_topik", ""),
            item.get("full_context", ""),
            " ".join(map(str, item.get("keywords", []) or item.get("keyword", []))),
            self.format_konten(item.get("konten", "")),
        ]
        return self.normalize_text(" ".join(map(str, fields)))

    def rule_search_intent(self, user_query, data_list, threshold=80, exclude_prefixes=None, calendar=False):
        """
        exclude_prefixes: list of intent prefix strings to skip (e.g. ['info_surat_kpti_', 'info_surat_sti_'])
        """
        best_item = None
        highest_score = 0
        requested_ta = self.detect_tahun_ajaran(user_query) if calendar else None
        requested_term = self.detect_semester_type(user_query) if calendar else None
        for item in data_list:
            # Skip intent yang dikecualikan (ditangani secara khusus)
            if exclude_prefixes:
                intent_name = item.get("intent", "")
                if any(intent_name.startswith(prefix) for prefix in exclude_prefixes):
                    continue
            if not self._is_intent_allowed_for_query(user_query, item):
                continue
            keywords = item.get("keywords", []) or item.get("keyword", [])
            targets = list(keywords)
            for field in ["intent", "topik_utama", "sub_topik", "full_context"]:
                if item.get(field):
                    targets.append(str(item[field]).replace("_", " "))
            if not targets:
                continue
            _, score = self._best_keyword_match(user_query, targets)
            if calendar and score > 0:
                item_ta = item.get("tahun_ajaran", "")
                text = self.item_text(item)
                if requested_ta:
                    score += 45 if item_ta == requested_ta else -80
                if requested_term:
                    if requested_term in text:
                        score += 25
                    elif "ganjil" in text or "genap" in text:
                        score -= 45
                for admission_term in ["snbp", "snbt", "smm", "smbt"]:
                    if admission_term in self.normalize_text(user_query):
                        score += 35 if admission_term in text else -35
                query_text = self.normalize_text(user_query)
                action_rules = [
                    (["bayar", "pembayaran"], ["bayar", "pembayaran"]),
                    (["pengumuman"], ["pengumuman"]),
                    (["sanggah", "keberatan"], ["sanggah", "keberatan"]),
                    (["revisi", "ubah"], ["revisi", "ubah", "ganti"]),
                    (["pengisian", "isi"], ["pengisian", "isi"]),
                ]
                for query_words, item_words in action_rules:
                    if any(word in query_text for word in query_words):
                        score += 35 if any(word in text for word in item_words) else -35
            if score > highest_score:
                highest_score = score
                best_item = item
        return best_item if highest_score >= threshold else None

    def rule_search_skripsi_category(self, user_query, threshold=80):
        query_text = self.normalize_text(user_query)
        if "tabel" in query_text and any(cue in query_text for cue in [
            "judul tabel", "format tabel", "nomor tabel", "sumber tabel",
            "caption tabel", "isi tabel", "kolom tabel", "kepala tabel",
        ]):
            return "Tabel"
        if "gambar" in query_text and any(cue in query_text for cue in [
            "judul gambar", "format gambar", "nomor gambar", "sumber gambar",
            "caption gambar",
        ]):
            return "Gambar"

        best_category = None
        highest_score = 0
        for category, keywords in self.skripsi_rules.items():
            _, score = self._best_keyword_match(user_query, keywords)
            if score > highest_score:
                highest_score = score
                best_category = category
        return best_category if highest_score >= threshold else None

    def format_skripsi_category_response(self, matched_skripsi_cat):
        responses = []
        category_text = self.normalize_text(matched_skripsi_cat)
        for chunk in self.skripsi_data:
            fields = [
                self.normalize_text(chunk.get("topik_utama", "")),
                self.normalize_text(chunk.get("sub_topik", "")),
                self.normalize_text(chunk.get("full_context", "")),
            ]
            is_format_intro = (
                matched_skripsi_cat == "Format Umum"
                and not chunk.get("topik_utama")
                and category_text in self.normalize_text(chunk.get("konten", ""))
            )
            is_direct_category = any(
                field == category_text
                or field.endswith(f" {category_text}")
                or field.startswith(f"{category_text} ")
                for field in fields
            )
            if is_direct_category or is_format_intro:
                konten = self.format_konten(chunk.get('konten', ''))
                title = chunk.get("full_context", "").strip() or chunk.get("topik_utama", "").strip() or konten.splitlines()[0]
                responses.append(f"**{title}**\n\n{konten}")
        return "\n\n---\n\n".join(responses) if responses else None

    def is_penulisan_object_query(self, user_query):
        text = self.normalize_text(user_query)
        writing_cues = [
            "penulisan", "format", "aturan", "cara tulis", "cara menulis",
            "judul tabel", "nomor tabel", "sumber tabel", "caption tabel",
            "judul gambar", "nomor gambar", "caption gambar",
        ]
        return any(cue in text for cue in writing_cues)

    def detect_judul_context_target(self, user_query):
        text = self.normalize_text(user_query)
        if not re.search(r"\bjudul\b", text):
            return None

        if "tabel" in text:
            return ("skripsi_category", "Tabel")
        if "gambar" in text:
            return ("skripsi_category", "Gambar")
        if "halaman" in text:
            return ("skripsi_category", "Halaman Judul")
        if "bab" in text or "sub judul" in text or "subjudul" in text:
            return ("skripsi_category", "Judul Bab, Sub Judul dan Anak Sub Judul")

        skripsi_cues = [
            "skripsi", "topik", "pengajuan", "mengajukan", "ajukan", "usul",
            "pengusulan", "sitei", "pembimbing", "koordinator", "menyetujui",
            "memverifikasi",
        ]
        if any(cue in text for cue in skripsi_cues) or re.fullmatch(r"(?:apa|bagaimana|cara|info|informasi|tentang|mengenai|\s)*judul(?:\s+skripsi)?", text):
            return ("procedure", "judul")

        return ("procedure", "judul")

    def rule_search_sop(self, user_query, data_list, threshold=70, limit=2):
        scored = []
        for item in data_list:
            targets = [
                str(item.get("topik_utama", "")),
                str(item.get("sub_topik", "")),
                str(item.get("full_context", "")),
                " ".join(map(str, item.get("keywords", []) or item.get("keyword", []))),
                self.format_konten(item.get("konten", "")),
            ]
            targets = [t for t in targets if t]
            if not targets:
                continue
            _, score = self._best_keyword_match(user_query, targets)
            if score <= 0:
                query_tokens = set(self._meaningful_tokens(user_query))
                item_tokens = set(self._meaningful_tokens(" ".join(targets)))
                overlap = len(query_tokens & item_tokens)
                if overlap >= 3:
                    score = 45 + overlap * 8
            if score >= threshold:
                scored.append((score, item))
        if not scored:
            return []
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def format_sop_response(self, user_query, threshold=70, limit=2):
        sop_results = []
        sop_skripsi_hits = self.rule_search_sop(user_query, self.sop_skripsi_data, threshold=threshold, limit=limit)
        sop_jte_hits = self.rule_search_sop(user_query, self.sop_jte_data, threshold=threshold, limit=limit)
        for chunk in sop_skripsi_hits:
            konten = self.format_konten(chunk.get('konten', ''))
            sop_results.append(f"**SOP Skripsi - {chunk.get('full_context', 'Info')}**\n\n{konten}")
        for chunk in sop_jte_hits:
            konten = self.format_konten(chunk.get('konten', ''))
            sop_results.append(f"**SOP JTE - {chunk.get('full_context', 'Info')}**\n\n{konten}")
        if sop_results:
            return "\n\n---\n\n".join(sop_results)
        return None

    def format_sop_item(self, item, source_label):
        konten = self.format_konten(item.get('konten', ''))
        return f"**{source_label} - {item.get('full_context', 'Info')}**\n\n{konten}"

    def find_sop_by_phrase(self, data_list, phrases):
        for phrase in phrases:
            phrase = self.normalize_text(phrase)
            for item in data_list:
                haystack = self.item_text(item)
                if phrase in haystack:
                    return item
        return None

    def format_procedure_response(self, user_query, target):
        text = self.normalize_text(user_query)
        if target == "kp":
            phrases = (
                ["pengajuan seminar kerja praktek"]
                if "seminar" in text
                else ["pengajuan kerja praktek"]
            )
            item = self.find_sop_by_phrase(self.sop_jte_data, phrases)
            return self.format_sop_item(item, "SOP JTE") if item else None

        if target == "sempro":
            phrases = (
                ["prosedur pelaksanaan seminar proposal"]
                if "pelaksanaan" in text
                else ["prosedur seminar proposal skripsi"]
            )
            item = self.find_sop_by_phrase(self.sop_skripsi_data, phrases)
            return self.format_sop_item(item, "SOP Skripsi") if item else None

        if target == "sidang":
            phrases = (
                ["prosedur ujian skripsi"]
                if "pelaksanaan" in text
                else ["prosedur pendaftaran ujian skripsi", "prosedur ujian skripsi"]
            )
            item = self.find_sop_by_phrase(self.sop_skripsi_data, phrases)
            return self.format_sop_item(item, "SOP Skripsi") if item else None

        if target == "perpanjangan":
            items = []
            for item in self.sop_skripsi_data:
                context = self.normalize_text(item.get("full_context", ""))
                if context in {
                    "prosedur perpanjangan skripsi i",
                    "prosedur perpanjangan skripsi ii",
                }:
                    items.append(self.format_sop_item(item, "SOP Skripsi"))
            return "\n\n---\n\n".join(items) if items else None

        if target == "judul":
            item = self.find_sop_by_phrase(self.sop_skripsi_data, ["prosedur pengusulan judul skripsi"])
            return self.format_sop_item(item, "SOP Skripsi") if item else None

        return None

    def rule_search_curriculum(self, user_query):
        if not self.course_names:
            return None

        best_group, group_score = "", 0
        if group_score > 75 and "SEMESTER" not in best_group:
            for group in self.kurikulum_data.get(self.kurikulum_year, []):
                if group["group_name"] == best_group:
                    resp = f"📂 **Peminatan: {best_group} ({self.kurikulum_year})**\n\n"
                    for c in group["courses"]:
                        resp += f"- {c['name']} ({c['sks']} SKS)\n"
                    return resp

        matches = []
        valid_matches = [m for m in matches if m[1] > 65]
        if not valid_matches:
            return None

        response = f"**Hasil Pencarian Mata Kuliah ({self.kurikulum_year}):**\n"
        for name, _ in valid_matches:
            details = self.course_details[name]
            response += f"\n📖 **{name}**\n   • Kode : {details['code']}\n   • SKS  : {details['sks']}\n"
            if "Keahlian" in str(details["no_label"]) and self.kurikulum_year == "2018":
                response += f"   • Kategori : {details['no_label']} ({details['semester_info']})\n   • Grup     : {details['group']}\n"
            else:
                response += f"   • Semester : {details['group']}\n"
        return response

    def rule_search_curriculum(self, user_query):
        if not self.course_names:
            return None

        query_tokens = set(self._meaningful_tokens(user_query))
        matches = []
        for name in self.course_names:
            if self.kurikulum_year == "2018" and name in self.spec_map:
                continue
            name_tokens = set(self._meaningful_tokens(name))
            if not name_tokens:
                continue
            score = self._keyword_match_score(user_query, name)
            overlap = query_tokens & name_tokens
            has_course_cue = any(keyword in user_query for keyword in ["mata kuliah", "matkul"])
            if score == 0 and (
                len(overlap) >= min(2, len(name_tokens))
                or (has_course_cue and len(overlap) >= 1)
            ):
                score = 70 + len(overlap) * 5
            if score >= 70:
                matches.append((score, name))

        if not matches:
            for group_name in self.group_names:
                if self._keyword_match_score(user_query, group_name) >= 90 and "SEMESTER" not in group_name:
                    for group in self.kurikulum_data.get(self.kurikulum_year, []):
                        if group["group_name"] == group_name:
                            resp = f"**Peminatan: {group_name} ({self.kurikulum_year})**\n\n"
                            for c in group["courses"]:
                                resp += f"- {c['name']} ({c['sks']} SKS)\n"
                            return resp
            return None

        matches.sort(key=lambda x: x[0], reverse=True)
        response = f"**Hasil Pencarian Mata Kuliah ({self.kurikulum_year}):**\n"
        for _, name in matches[:3]:
            details = self.course_details[name]
            response += f"\n**{name}**\n- Kode: {details['code']}\n- SKS: {details['sks']}\n"
            if "Keahlian" in str(details["no_label"]) and self.kurikulum_year == "2018":
                response += f"- Kategori: {details['no_label']} ({details['semester_info']})\n- Grup: {details['group']}\n"
            else:
                response += f"- Semester: {details['group']}\n"
        return response

    def get_total_sks_per_semester(self):
        rows = []
        for group in self.kurikulum_data.get(self.kurikulum_year, []):
            group_name = group.get("group_name", "")
            if not group_name.upper().startswith("SEMESTER"):
                continue
            total_sks = group.get("total_sks")
            if total_sks is None:
                total_sks = sum(int(c.get("sks", 0) or 0) for c in group.get("courses", []))
            rows.append(f"- **{group_name.title()}**: {total_sks} SKS")
        if not rows:
            return None
        return f"**Total SKS tiap semester (Kurikulum {self.kurikulum_year}):**\n\n" + "\n".join(rows)

    def get_all_dosen_response(self):
        item = next((d for d in self.dosen_data if d.get("intent") == "daftar_nama_dosen_ti"), None)
        if item:
            return f"**Daftar Dosen TI:**\n\n{item['response']}"
        names = []
        for dosen in self.dosen_data:
            if dosen.get("intent", "").startswith("info_dosen_"):
                first_line = str(dosen.get("response", "")).splitlines()[0]
                if first_line:
                    names.append(f"- {first_line}")
        return "**Daftar Dosen TI:**\n\n" + "\n".join(names)

    def detect_procedure_target_after_action(self, user_query):
        text = self.normalize_text(user_query)
        action = r"(?:syarat|prosedur|tata cara|pendaftaran|pengajuan|mengajukan|ajukan|dokumen|berkas|form|surat)"
        targets = {
            "kp": r"(?:kp|kerja praktek|kerja praktik|seminar kp)",
            "sidang": r"(?:sidang skripsi|seminar hasil|semhas|ujian skripsi)",
            "sempro": r"(?:seminar proposal|sempro)",
            "perpanjangan": r"(?:perpanjangan skripsi|perpanjang(?:an)? waktu skripsi|perpanjang skripsi)",
            "judul": r"(?:(?:topik|judul)(?: skripsi)?)",
        }
        for target_name, target_pattern in targets.items():
            if re.search(rf"\b{action}\b(?:\s+\w+){{0,8}}\s+\b{target_pattern}\b", text):
                return target_name
            if re.search(rf"\b{target_pattern}\b(?:\s+\w+){{0,8}}\s+\b{action}\b", text):
                return target_name
        return None

    def detect_skripsi_stage_target(self, user_query):
        text = self.normalize_text(user_query)
        action_cues = [
            "kapan", "jadwal", "tanggal", "pelaksanaan", "syarat", "prosedur",
            "tata cara", "pendaftaran", "pengajuan", "cara daftar", "mengajukan",
            "dokumen", "berkas", "form", "surat",
        ]
        if not any(cue in text for cue in action_cues):
            return None
        if any(cue in text for cue in ["perpanjangan skripsi", "perpanjang waktu skripsi", "perpanjang skripsi"]):
            return "perpanjangan"
        if any(cue in text for cue in ["ujian skripsi", "sidang skripsi", "seminar hasil", "semhas"]):
            return "sidang"
        if any(cue in text for cue in ["seminar proposal", "sempro"]):
            return "sempro"
        if any(cue in text for cue in ["seminar kp", "seminar kerja praktek", "seminar kerja praktik"]):
            return "kp"
        return None

    def _has_admission_exam_context(self, user_query):
        text = self.normalize_text(user_query)
        admission_cues = [
            "seleksi", "pendaftaran", "pmb", "jalur masuk", "jalur pendaftaran",
            "mahasiswa baru", "calon mahasiswa", "snbp", "snbt", "smm", "smbt",
            "utbk", "kartu peserta", "kartu ujian", "cetak kartu", "lokasi ujian",
        ]
        return any(cue in text for cue in admission_cues)

    def _has_skripsi_exam_context(self, user_query):
        text = self.normalize_text(user_query)
        skripsi_cues = [
            "skripsi", "proposal", "sempro", "seminar proposal", "seminar hasil",
            "semhas", "sidang", "tugas akhir", "sitei", "sti", "pembimbing",
            "penguji",
        ]
        return any(cue in text for cue in skripsi_cues)

    def _is_intent_allowed_for_query(self, user_query, item):
        intent = item.get("intent", "")
        if intent == "info_ujian_seleksi":
            return self._has_admission_exam_context(user_query) and not self._has_skripsi_exam_context(user_query)
        return True

    def is_skip_skripsi_flow_query(self, user_query):
        text = self.normalize_text(user_query)
        has_skip_action = bool(re.search(r"\b(skip|lewati|melewati|tanpa|langsung)\b", text))
        has_sempro = any(cue in text for cue in ["seminar proposal", "sempro", "proposal"])
        has_next_stage = any(cue in text for cue in ["ujian skripsi", "sidang skripsi", "seminar hasil", "semhas"])
        return has_skip_action and has_sempro and has_next_stage

    # ------------------------------------------
    # HELPER: FORMAT KONTEN
    # ------------------------------------------
    def format_konten(self, konten):
        """Format konten: tiap poin di baris baru rapat tanpa gap paragraph."""
        if isinstance(konten, list):
            formatted = []
            for item in konten:
                item = item.strip()
                if not item:
                    continue
                
                # Deteksi item yang sudah punya numbering/bullet (A., 1), a), dll)
                if re.match(r'^[A-Z]\.|^\d+\)|^[a-z]\)|^-|^•', item):
                    formatted.append(item)
                # Item dengan indentasi (sub-poin)
                elif item.startswith('   '):
                    formatted.append(item)
                # Item biasa tanpa bullet
                else:
                    formatted.append(item)
            return '  \n'.join(formatted)
        return str(konten)

    # ------------------------------------------
    # PREPROCESSING SINGKATAN
    # ------------------------------------------
    def expand_abbreviations(self, text):
        """Ekspansi singkatan umum ke bentuk lengkap untuk matching lebih baik"""
        abbreviations = {
            r'\bsempro\b': 'sempro seminar proposal',
            r'\bsemhas\b': 'semhas seminar hasil sidang skripsi ujian skripsi',
            r'\bsidang skripsi\b': 'sidang skripsi ujian skripsi',
            # \bkp\b TIDAK diekspansi — menyebabkan false positive ke keyword KPTI
            # keyword "kp" ditangani langsung oleh rule SOP JTE
            r'\bta\b': 'ta tugas akhir skripsi',
            r'\bmatkul\b': 'matkul mata kuliah',
            r'\buts\b': 'uts ujian tengah semester',
            r'\buas\b': 'uas ujian akhir semester',
            r'\bkrs\b': 'krs kartu rencana studi',
            r'\bukt\b': 'ukt uang kuliah tunggal',
            r'\bspp\b': 'spp sumbangan pembinaan pendidikan',
            r'\bmbkm\b': 'mbkm merdeka belajar kampus merdeka',
            r'\bpmb\b': 'pmb penerimaan mahasiswa baru',
            r'\bsnbp\b': 'snbp seleksi nasional berdasarkan prestasi',
            r'\bsnbt\b': 'snbt seleksi nasional berdasarkan tes',
            r'\butbk\b': 'utbk ujian tulis berbasis komputer',
            r'\bkkn\b': 'kkn kuliah kerja nyata kukerta',
            # STI dan KPTI TIDAK diekspansi karena ditangani secara khusus
        }
        
        expanded = text.lower()
        for pattern, replacement in abbreviations.items():
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        
        return expanded

    # ------------------------------------------
    # ROUTER UTAMA
    # ------------------------------------------
    def get_response(self, user_input):
        cleaned_input = user_input.lower().strip()
        # Ekspansi singkatan untuk matching yang lebih baik
        expanded_input = self.expand_abbreviations(cleaned_input)

        # 1. Perintah Sistem
        if "ganti" in expanded_input:
            if "2018" in expanded_input:
                return "Berhasil beralih ke Kurikulum 2018." if self.load_curriculum("2018") else "Data Kurikulum 2018 tidak ada."
            elif "2025" in expanded_input:
                return "Berhasil beralih ke Kurikulum 2025." if self.load_curriculum("2025") else "Data Kurikulum 2025 tidak ada."

        if "kurikulum 2018" in expanded_input and self.kurikulum_year != "2018":
            self.load_curriculum("2018")
        elif "kurikulum 2025" in expanded_input and self.kurikulum_year != "2025":
            self.load_curriculum("2025")

        sem_match = re.search(r"(?:sem|semester)\s*(\d+)", expanded_input)
        if "total" in expanded_input and "sks" in expanded_input:
            if sem_match:
                return self.get_semester_info(sem_match.group(1))
            if any(keyword in expanded_input for keyword in ["tiap semester", "setiap semester", "per semester", "semua semester"]):
                return self.get_total_sks_per_semester() or f"Total SKS Kurikulum {self.kurikulum_year}: 144 SKS."
            return f"Total SKS yang harus ditempuh berdasarkan Kurikulum {self.kurikulum_year} adalah 144 SKS."
        if sem_match:
            return self.get_semester_info(sem_match.group(1))

        keahlian_response = self.get_keahlian_course_response(expanded_input)
        if keahlian_response:
            return keahlian_response

        if self.is_skip_skripsi_flow_query(expanded_input):
            sop_response = self.format_procedure_response(expanded_input, "sidang")
            if sop_response:
                return sop_response

        # Query tentang bimbingan skripsi/proposal/KP → arahkan ke SOP, bukan kurikulum.
        # Ini mencegah "seminar proposal" atau "skripsi" terdeteksi sebagai nama mata kuliah.
        is_bimbingan_query = bool(re.search(r"\bbimbingan\b", expanded_input)) and any(
            kw in expanded_input for kw in [
                "berapa", "minimal", "minimum", "syarat", "kali", "logbook",
                "log book", "berapa kali", "jumlah", "ketentuan",
            ]
        )
        if is_bimbingan_query:
            sop_response = self.format_sop_response(expanded_input, threshold=50, limit=2)
            if sop_response:
                return sop_response

        # Query ujian semester harus masuk kalender, bukan intent umum "ujian seleksi".
        is_semester_exam_query = (
            re.search(r"\b(uts|uas)\b", cleaned_input)
            or "ujian tengah semester" in expanded_input
            or "ujian akhir semester" in expanded_input
        )
        calendar_action_query = any(keyword in cleaned_input for keyword in [
            "kapan", "jadwal", "batas", "masa", "tanggal", "pelaksanaan",
            "pengisian", "isi krs", "revisi", "ubah krs", "ganti matakuliah",
            "perkuliahan", "kuliah", "praktikum", "bayar", "pembayaran",
            "pengumuman ukt", "sanggah ukt", "keberatan ukt",
        ])
        calendar_topic_query = any(keyword in cleaned_input for keyword in [
            "revisi krs", "pengisian krs", "isi krs", "krs", "uts", "uas",
            "perkuliahan", "kuliah", "praktikum", "ukt", "spp", "toefl", "ept",
        ])
        calendar_specific_ukt_query = "ukt" in cleaned_input and any(
            keyword in cleaned_input for keyword in ["snbp", "snbt", "smm", "smbt", "sanggah"]
        )
        is_course_query = any(keyword in expanded_input for keyword in ["mata kuliah", "matkul"])
        if (
            is_semester_exam_query
            or calendar_specific_ukt_query
            or (calendar_action_query and calendar_topic_query and not is_course_query)
        ):
            best_kalender = self.rule_search_intent(expanded_input, self.kalender_data, threshold=60, calendar=True)
            if best_kalender:
                ta = best_kalender.get("tahun_ajaran", "")
                header = f"**Informasi Akademik (TA {ta}):**" if ta else "**Informasi Akademik:**"
                return f"{header}\n\n{best_kalender['response']}"

        if is_course_query:
            kurikulum_response = self.rule_search_curriculum(expanded_input)
            if kurikulum_response:
                return kurikulum_response

        # Publikasi ilmiah terkait skripsi adalah informasi umum, bukan SOP skripsi.
        is_publication_query = any(keyword in expanded_input for keyword in [
            "publikasi", "publikasi ilmiah", "apresiasi publikasi", "ekuivalensi",
            "scopus", "q1", "q2", "q3", "q4", "sinta", "s1", "s2",
            "loa jurnal", "nilai publikasi", "nilai skripsi jurnal",
        ])
        if is_publication_query:
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_ketentuan_publikasi":
                    return f"**Informasi:**\n\n{item['response']}"

        judul_context_target = self.detect_judul_context_target(expanded_input)
        if judul_context_target:
            target_type, target_value = judul_context_target
            if target_type == "procedure":
                sop_response = self.format_procedure_response(expanded_input, target_value)
                if sop_response:
                    return sop_response
            elif target_type == "skripsi_category":
                skripsi_response = self.format_skripsi_category_response(target_value)
                if skripsi_response:
                    return skripsi_response

        # Query prosedural wajib punya aksi + objek setelahnya, mis. "syarat KP" atau "prosedur sempro".
        procedure_target = self.detect_procedure_target_after_action(expanded_input)
        if procedure_target:
            sop_response = self.format_procedure_response(expanded_input, procedure_target)
            if sop_response:
                return sop_response

        skripsi_stage_target = self.detect_skripsi_stage_target(expanded_input)
        if skripsi_stage_target:
            sop_response = self.format_procedure_response(expanded_input, skripsi_stage_target)
            if sop_response:
                return sop_response

        if self.is_penulisan_object_query(expanded_input):
            matched_skripsi_cat = self.rule_search_skripsi_category(expanded_input, threshold=75)
            if matched_skripsi_cat:
                skripsi_response = self.format_skripsi_category_response(matched_skripsi_cat)
                if skripsi_response:
                    return skripsi_response

        # "Siapa saja ..." tidak selalu berarti daftar dosen; cek konteks skripsi/SITEI dulu.
        is_skripsi_context_query = any(keyword in expanded_input for keyword in [
            "sitei", "topik", "menyetujui", "memverifikasi",
        ])
        has_procedure_action = re.search(r"\b(syarat|prosedur|tata cara|pendaftaran|pengajuan)\b", expanded_input)
        if is_skripsi_context_query and (not has_procedure_action or procedure_target):
            sop_response = (
                self.format_procedure_response(expanded_input, procedure_target)
                if procedure_target
                else self.format_sop_response(expanded_input, threshold=70, limit=2)
            )
            if sop_response:
                return sop_response

        # 2. Informasi Umum
        # Deteksi khusus KP MBKM — hanya jika user eksplisit menyebut "mbkm" atau "merdeka belajar"
        # Gunakan cleaned_input (sebelum ekspansi) agar tidak false positive
        is_mbkm_query = any(kw in cleaned_input for kw in ["mbkm", "merdeka belajar", "merdeka belajar kampus merdeka"])

        # Deteksi khusus untuk "visi misi" atau "visi dan misi"
        if any(keyword in expanded_input for keyword in ["visi misi", "visi dan misi", "visi & misi"]):
            visi_item = None
            misi_item = None
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_visi_prodi":
                    visi_item = item
                elif item.get("intent") == "info_misi_prodi":
                    misi_item = item
            
            if visi_item and misi_item:
                return f"**Visi & Misi Program Studi:**\n\n{visi_item['response']}\n\n---\n\n{misi_item['response']}"
            elif visi_item:
                return f"**Informasi:**\n\n{visi_item['response']}"
            elif misi_item:
                return f"**Informasi:**\n\n{misi_item['response']}"
        
        # Deteksi khusus untuk KPTI (HANYA jika user eksplisit mengetik "kpti")
        # Gunakan cleaned_input (bukan expanded) untuk menghindari false positive dari ekspansi "kp"
        kpti_specific_match = re.search(r'\bkpti[-\s]?(\d+)\b', cleaned_input)
        kpti_general_match = re.search(r'\bkpti\b', cleaned_input)
        
        if kpti_specific_match:
            # User menanyakan KPTI spesifik dengan nomor (contoh: "kpti-1", "kpti 10")
            kpti_num = kpti_specific_match.group(1)
            for item in self.informasi_umum_data:
                if item.get("intent") == f"info_surat_kpti_{kpti_num}":
                    return f"**Informasi:**\n\n{item['response']}"
        elif kpti_general_match and not re.search(r'\b(syarat|prosedur|cara|alur|tata cara|ketentuan)\b', cleaned_input):
            # User hanya mengetik "kpti" saja tanpa konteks prosedur - tampilkan overview
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_overview_kpti":
                    return f"**Daftar Form KPTI:**\n\n{item['response']}"
        # Deteksi khusus untuk STI (HANYA jika user eksplisit mengetik "sti")
        # Pastikan bukan bagian dari kata lain (seperti "prestasi", "investasi")
        sti_specific_match = re.search(r'\bsti[-\s]?(\d+)\b', cleaned_input)
        sti_general_match = re.search(r'\bsti\b', cleaned_input) and not re.search(r'\bkpti\b', cleaned_input)
        
        if sti_specific_match:
            # User menanyakan STI spesifik dengan nomor
            sti_num = sti_specific_match.group(1)
            for item in self.informasi_umum_data:
                if item.get("intent") == f"info_surat_sti_{sti_num}":
                    return f"**Informasi:**\n\n{item['response']}"
        elif sti_general_match and not re.search(r'\b(syarat|prosedur|cara|alur|tata cara|ketentuan)\b', cleaned_input):
            # User hanya mengetik "sti" saja tanpa konteks prosedur - tampilkan overview
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_overview_sti":
                    return f"**Daftar Form STI:**\n\n{item['response']}"
        
        # KP MBKM — hanya tampilkan jika user eksplisit menyebut "mbkm" atau "merdeka belajar"
        if is_mbkm_query:
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_prosedur_kp_mbkm":
                    return f"**Informasi:**\n\n{item['response']}"

        if re.search(r"\b(ukt|uang kuliah tunggal|biaya kuliah)\b", expanded_input):
            for item in self.informasi_umum_data:
                if item.get("intent") == "info_biaya_kuliah_teknik_informatika":
                    return f"**Informasi:**\n\n{item['response']}"

        best_info = self.rule_search_intent(
            expanded_input,
            self.informasi_umum_data,
            threshold=80,
            exclude_prefixes=["info_surat_kpti_", "info_surat_sti_", "info_overview_kpti", "info_overview_sti", "info_prosedur_kp_mbkm"]
        )
        if best_info:
            return f"**Informasi:**\n\n{best_info['response']}"

        # 3. Dosen
        is_dosen_list_query = (
            re.fullmatch(r"\s*(dosen|daftar dosen|nama dosen|list dosen|semua dosen)\s*", cleaned_input)
            or any(keyword in cleaned_input for keyword in [
                "siapa saja dosen", "siapa aja dosen", "semua nama dosen",
                "dosen ti siapa", "dosen teknik informatika siapa",
            ])
        )
        if is_dosen_list_query:
            return self.get_all_dosen_response()

        best_dosen = self.rule_search_intent(expanded_input, self.dosen_data, threshold=80)
        if best_dosen:
            # Pastikan tiap field dosen tampil di baris terpisah (single \n → double \n untuk markdown)
            raw = best_dosen['response']
            # Hindari double-spacing jika sudah ada \n\n
            dosen_response = re.sub(r'\n(?!\n)', '\n\n', raw)
            return f"**Informasi Dosen:**\n\n{dosen_response}"

        # 4. Kalender Akademik
        # Prioritaskan intent jadwal_wisuda_semua untuk query umum tentang wisuda
        if any(keyword in expanded_input for keyword in ["kapan wisuda", "jadwal wisuda", "wisuda kapan", "semua jadwal wisuda", "jadwal wisuda 2026", "jadwal wisuda 2027", "wisuda tahun ini"]) and not re.search(r"wisuda\s*(ke-?)?\s*\d+", expanded_input):
            for item in self.kalender_data:
                if item.get("intent") == "jadwal_wisuda_semua":
                    return f"**Jadwal Wisuda:**\n\n{item['response']}"
        
        best_kalender = self.rule_search_intent(expanded_input, self.kalender_data, threshold=80, calendar=True)
        if best_kalender:
            ta = best_kalender.get("tahun_ajaran", "")
            header = f"**Informasi Akademik (TA {ta}):**" if ta else "**Informasi Akademik:**"
            return f"{header}\n\n{best_kalender['response']}"

        # 5. Setelah Sidang
        best_setelah = self.rule_search_intent(expanded_input, self.setelah_sidang_data, threshold=80)
        if best_setelah:
            return f"**Setelah Sidang:**\n\n{best_setelah['response']}"

        # 6. Pedoman Penulisan Skripsi (dicek lebih dulu karena lebih spesifik untuk aturan penulisan)
        # Deteksi query umum tentang pedoman/aturan penulisan skripsi
        if any(keyword in expanded_input for keyword in ["aturan penulisan", "pedoman penulisan", "format penulisan", "cara menulis skripsi", "panduan penulisan"]):
            overview_chunks = []
            for chunk in self.skripsi_data:
                if chunk.get("sub_topik") == "Umum" and chunk.get("topik_utama") in ["Kertas", "Pengetikan", "Penomoran", "Bahasa"]:
                    konten = self.format_konten(chunk.get('konten', ''))
                    overview_chunks.append(f"**{chunk.get('full_context', 'Info')}**\n\n{konten}")
            if overview_chunks:
                return "**Pedoman Penulisan Skripsi:**\n\n" + "\n\n---\n\n".join(overview_chunks[:4]) + "\n\n*Tanyakan lebih spesifik untuk detail (contoh: 'aturan margin', 'format tabel', 'daftar pustaka')*"
        
        matched_skripsi_cat = self.rule_search_skripsi_category(expanded_input, threshold=75)
        if matched_skripsi_cat:
            skripsi_response = self.format_skripsi_category_response(matched_skripsi_cat)
            if skripsi_response:
                return skripsi_response

        # 7. SOP Skripsi & SOP JTE (dicek setelah Pedoman Skripsi)
        non_procedural_sop_context = any(keyword in expanded_input for keyword in [
            "pakaian seminar", "pakaian sidang", "tim penguji", "pembimbing skripsi",
            "waktu pengerjaan skripsi", "penilaian proposal", "penilaian ujian skripsi",
            "setelah seminar kp", "setelah seminar kerja praktek", "setelah seminar kerja praktik",
            "minimal toefl", "minimum toefl", "skor toefl", "nilai toefl", "syarat toefl",
            "toefl sidang", "toefl semhas", "toefl ujian skripsi",
            "minimal logbook", "minimum logbook", "jumlah logbook", "berapa kali logbook",
            "logbook bimbingan", "logbook sempro", "logbook semhas", "logbook sidang",
        ])
        if procedure_target or non_procedural_sop_context:
            sop_response = (
                self.format_procedure_response(expanded_input, procedure_target)
                if procedure_target
                else self.format_sop_response(expanded_input, threshold=70, limit=2)
            )
            if sop_response:
                return sop_response

        # 8. Kurikulum Matkul
        kurikulum_response = self.rule_search_curriculum(expanded_input)
        if kurikulum_response:
            return kurikulum_response

        # 9. Fallback
        return (
            "Maaf, saya tidak menemukan jawaban yang relevan. Coba contoh pertanyaan di sidebar, "
            "atau gunakan kategori berikut:\n\n"
            "- **Kurikulum** — `semester 5`, `matkul algoritma`\n"
            "- **Kalender** — `kapan wisuda 128`, `jadwal uts`\n"
            "- **Dosen** — `dosen pak irsan`, `kaprodi ti`\n"
            "- **Pedoman Skripsi** — `aturan margin skripsi`\n"
            "- **Setelah Sidang** — `map biru`, `alur bebas lab`\n"
            "- **SOP** — `prosedur seminar proposal`, `pendaftaran KP`\n"
            "- **Informasi Umum** — `alur pendaftaran`, `beasiswa`, `biaya ukt`, `form sti-1`, `kontak admin`\n"
            f"- `ganti 2018` (Ubah versi kurikulum, saat ini: {self.kurikulum_year})"
        )


# ==========================================
# CACHE BOT (biar gak reload file tiap rerun)
# ==========================================
@st.cache_resource
def load_bot(default_year: str = "2025"):
    return MasterRuleBasedChatbot(default_year=default_year)


# ==========================================
# UI
# ==========================================
bot = load_bot(default_year="2025")

# ---- Sidebar ----
with st.sidebar:
    st.markdown("## 🤖 Chatbot TI UNRI")
    st.caption("Rule-Based")

    st.markdown("### ⚙️ Pengaturan")
    kur_options = list(bot.kurikulum_data.keys()) if bot.kurikulum_data else [bot.kurikulum_year]
    if kur_options:
        current_idx = kur_options.index(bot.kurikulum_year) if bot.kurikulum_year in kur_options else 0
        selected_year = st.selectbox("Versi Kurikulum Aktif", kur_options, index=current_idx)
        if selected_year != bot.kurikulum_year:
            bot.load_curriculum(selected_year)
            st.rerun()

    st.markdown("### 💡 Contoh Pertanyaan")
    examples = [
        "Siapa kaprodi TI?",
        "Visi dan Misi",
        "Kapan wisuda 128?",
        "Semester 3",
        "Isi map biru apa saja?",
        "Prosedur sempro",
        "Syarat semhas",
        "Syarat pengajuan KP",
        "Aturan margin skripsi",
        "Jumlah dosen TI",
        "Alur pendaftaran UNRI",
        "Biaya UKT Teknik Informatika",
        "Beasiswa Pemprov Riau",
        "Download form STI-1",
        "Kontak admin prodi",
        "Prosedur KP MBKM",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key=f"ex_{q}"):
            st.session_state["pending_input"] = q
            st.rerun()

    st.markdown("### 📂 Sumber Data")
    st.caption(
        "- Kurikulum (2018 & 2025)\n"
        "- Kalender Akademik TA 25/26 & 26/27\n"
        "- Data Dosen\n"
        "- Pedoman Penulisan Skripsi\n"
        "- SOP JTE & SOP Skripsi\n"
        "- Setelah Sidang (Map Biru/Merah & SITEI)\n"
        "- Informasi Umum (Pendaftaran, UKT, Beasiswa,\n"
        "  Form STI/KPTI, Publikasi, KP MBKM, dll.)"
    )

    if st.button("🗑️ Bersihkan Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# ---- Main Area ----
st.title("🤖 Chatbot Teknik Informatika UNRI")
st.caption(
    f"Kurikulum aktif: **{bot.kurikulum_year}** · "
    f"Gunakan chatbot ini untuk bertanya seputar kurikulum, dosen, kalender akademik, skripsi, KP, informasi umum, dan administrasi."
)

# Init chat state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Halo! 👋 Saya asisten virtual Teknik Informatika UNRI.\n\n"
                "Silakan tanyakan apa saja seputar:\n"
                "- Kurikulum & mata kuliah\n"
                "- Jadwal akademik (UTS/UAS/wisuda)\n"
                "- Info dosen\n"
                "- Prosedur skripsi & KP\n"
                "- Alur setelah sidang\n"
                "- Informasi umum (pendaftaran, UKT, beasiswa, form STI/KPTI, publikasi)\n\n"
                "💡 **Tips:** Kamu bisa pakai singkatan seperti:\n"
                "• **sempro** = seminar proposal\n"
                "• **semhas** = seminar hasil / sidang skripsi\n"
                "• **KP** = kerja praktik\n"
                "• **TA** = tugas akhir / skripsi\n"
                "• **UTS/UAS** = ujian tengah/akhir semester\n"
                "• **KRS** = kartu rencana studi\n\n"
                "Kamu juga bisa klik contoh pertanyaan di sidebar."
            ),
        }
    ]

# Tampilkan riwayat chat
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ambil input user (dari chat_input atau tombol contoh)
user_input = st.chat_input("Ketik pertanyaanmu di sini...")
if not user_input and "pending_input" in st.session_state:
    user_input = st.session_state.pop("pending_input")

if user_input:
    # Simpan pesan user
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            start_time = time.perf_counter()
            response = bot.get_response(user_input)
            elapsed = time.perf_counter() - start_time
        st.markdown(response)
        st.caption(f"⏱️ Diproses dalam {elapsed * 1000:.1f} ms")

    st.session_state["messages"].append({"role": "assistant", "content": response})
