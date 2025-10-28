# PERFORMA-AI V3: Evaluasi Kinerja ASN Berbasis AI & Kompetensi

> *"Dari Subjektif ke Objektif. Dari Reaktif ke Proaktif. Dari Nilai ke Pengembangan."*

Sistem evaluasi kinerja ASN yang *objektif, transparan, dan adaptif* menggunakan AI untuk analisis dokumen PDF, dashboard kinerja real-time, dan rekomendasi pengembangan diri berbasis kompetensi.

---

## Fitur Utama
- Atasan buat *template tugas* dengan: kompetensi, tipe dokumen, bobot, kata kunci
- ASN upload PDF → *AI V3 analisis otomatis* (relevansi, struktur, analisis, keluasan)
- Atasan *validasi final* + feedback
- Dashboard: *tren kinerja + skor per kompetensi*
- *Rekomendasi pelatihan otomatis* jika skor kompetensi < 65

---

## Tech Stack
- *Frontend*: Streamlit (dashboard interaktif)
- *Backend*: MySQL
- *AI Engine*: Custom Rule-Based AI (PyPDF2 + weighted scoring)
- *Data*: Pandas

---

## Cara Menjalankan

```bash
# 1. Clone repo
git clone https://github.com/rexxel321/hackaton-bkn.git
cd hackaton-bkn

# 2. Setup environment
py -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy init.sql dan masukin di mysql (untuk database)

# 5. Jalankan aplikasi
streamlit run dashboard_v3.py
