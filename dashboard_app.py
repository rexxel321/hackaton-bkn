import streamlit as st
import pandas as pd
import mysql.connector
import os
from datetime import datetime
# --- IMPORT FILE AI YANG BARU ---
from process_submission_ai import analyze_submission_ai

# --- Konfigurasi Database ---
def connect_db():
    """Menghubungkan ke database MySQL."""
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="", # GANTI DENGAN PASSWORD MYSQL ANDA
            database="hackathon_bkn"
        )
        return db
    except mysql.connector.Error as e:
        st.error(f"Error koneksi DB: {e}")
        return None

# --- Fungsi Bantuan Database (CRUD) ---
# (Semua fungsi di-cache agar lebih cepat)

@st.cache_data(ttl=60)
def get_user(email):
    """Mengambil data user berdasarkan email."""
    db = connect_db()
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM asn WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        return user
    return None

@st.cache_data(ttl=60)
def get_bawahan(atasan_id):
    """Mengambil daftar bawahan dari seorang atasan."""
    db = connect_db()
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM asn WHERE atasan_id = %s", (atasan_id,))
        bawahan = cursor.fetchall()
        cursor.close()
        db.close()
        return bawahan
    return []

@st.cache_data(ttl=60)
def get_task_templates_for_asn(atasan_id):
    """Mengambil template tugas yang ditugaskan oleh atasan."""
    db = connect_db()
    if db:
        cursor = db.cursor(dictionary=True)
        # Query untuk mengambil template DAN mengecek apakah sudah disubmit oleh user
        cursor.execute("SELECT * FROM task_templates WHERE atasan_id = %s", (atasan_id,))
        templates = cursor.fetchall()
        cursor.close()
        db.close()
        return templates
    return []

@st.cache_data(ttl=30)
def get_submissions_for_atasan(bawahan_ids):
    """Mengambil semua submission dari bawahan untuk divalidasi."""
    db = connect_db()
    if not db or not bawahan_ids:
        return pd.DataFrame()
    
    placeholders = ','.join(['%s'] * len(bawahan_ids))
    query = f"""
        SELECT 
            s.id as submission_id, 
            s.file_path, 
            s.tanggal_submit,
            a.nama_asn,
            t.judul_tugas, 
            t.required_keywords, 
            t.required_sections,
            e.skor_ai, 
            e.catatan_ai, 
            e.skor_final_atasan
        FROM task_submissions s
        JOIN asn a ON s.asn_id = a.id
        JOIN task_templates t ON s.template_id = t.id
        LEFT JOIN evaluasi_kinerja e ON s.id = e.submission_id
        WHERE s.asn_id IN ({placeholders})
        ORDER BY s.tanggal_submit DESC
    """
    df = pd.read_sql(query, db, params=bawahan_ids)
    db.close()
    return df

@st.cache_data(ttl=30)
def get_kinerja_asn(asn_id):
    """Mengambil riwayat kinerja ASN untuk grafik (dari tabel baru)."""
    db = connect_db()
    if not db:
        return pd.DataFrame()
    
    query = """
        SELECT DATE_FORMAT(s.tanggal_submit, '%Y-%m') as bulan, 
               AVG(e.skor_final_atasan) as rata_rata_skor
        FROM evaluasi_kinerja e
        JOIN task_submissions s ON e.submission_id = s.id
        WHERE s.asn_id = %s 
          AND e.skor_final_atasan IS NOT NULL
          AND s.tanggal_submit >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY bulan
        ORDER BY bulan ASC
    """
    df = pd.read_sql(query, db, params=(asn_id,))
    db.close()
    if not df.empty:
        df = df.set_index('bulan')
    return df

def check_submission_exists(asn_id, template_id):
    """Mengecek apakah ASN sudah submit untuk template ini."""
    db = connect_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM task_submissions WHERE asn_id = %s AND template_id = %s", (asn_id, template_id))
        exists = cursor.fetchone()
        cursor.close()
        db.close()
        return exists is not None
    return False

# --- Direktori Upload ---
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# =================================================================
# --- Tampilan Aplikasi (UI) ---
# =================================================================
st.set_page_config(page_title="PERFORMA-AI V2", layout="wide")
st.title("🚀 PERFORMA-AI: Sistem Evaluasi Kinerja Berbasis Template")

# --- Demo "Login" ---
st.sidebar.title("Login Demo")
email = st.sidebar.text_input("Masukkan email Anda (demo):", "budi@asn.go.id")
user = get_user(email)

if not user:
    st.sidebar.error("User tidak ditemukan. Coba: 'budi@asn.go.id' atau 'citra@asn.go.id'")
    st.stop()

st.sidebar.success(f"Selamat datang, **{user['nama_asn']}**!")
st.sidebar.write(f"Jabatan: *{user['jabatan']}*")

is_atasan = user['atasan_id'] is None
user_id = user['id']

# =================================================================
# --- Tampilan 1: ASN (Bawahan) ---
# =================================================================
if not is_atasan:
    st.header("Modul ASN: Daftar Tugas Anda")
    st.info("Berikut adalah daftar tugas yang ditugaskan oleh atasan Anda. Upload dokumen Anda sesuai kriteria.")

    templates = get_task_templates_for_asn(user['atasan_id'])
    
    if not templates:
        st.warning("Atasan Anda belum membuat template tugas.")
        st.stop()

    for template in templates:
        template_id = template['id']
        judul = template['judul_tugas']
        
        # Cek apakah sudah disubmit
        already_submitted = check_submission_exists(user_id, template_id)
        
        if already_submitted:
            st.success(f"✔️ **{judul}** (Sudah Dikerjakan)")
            continue # Lanjut ke template berikutnya
        
        # Jika belum dikerjakan, tampilkan form upload
        with st.expander(f"📝 **{judul}** (Belum Dikerjakan)", expanded=True):
            st.markdown("**Kriteria Penilaian dari Atasan:**")
            st.markdown(f" - **Kata Kunci Wajib:** `{template['required_keywords']}`")
            st.markdown(f" - **Bagian Wajib:** `{template['required_sections']}`")
            
            with st.form(key=f"form_task_{template_id}", clear_on_submit=True):
                uploaded_file = st.file_uploader("Upload Dokumen (PDF Saja):", type=["pdf"])
                submit_button = st.form_submit_button("Submit Tugas")

                if submit_button and uploaded_file is not None:
                    # 1. Simpan file ke server
                    filename = f"{user_id}_{template_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    with st.spinner(f"AI sedang menganalisis '{judul}'..."):
                        # 2. Panggil "AI" untuk menganalisis berdasarkan template
                        skor_ai, catatan_ai = analyze_submission_ai(file_path, template)
                        
                        # 3. Simpan ke database
                        db = connect_db()
                        if db:
                            cursor = db.cursor()
                            # Insert ke task_submissions
                            cursor.execute("INSERT INTO task_submissions (template_id, asn_id, file_path) VALUES (%s, %s, %s)",
                                           (template_id, user_id, file_path))
                            submission_id = cursor.lastrowid
                            
                            # Insert ke evaluasi_kinerja (hasil AI)
                            cursor.execute("INSERT INTO evaluasi_kinerja (submission_id, skor_ai, catatan_ai) VALUES (%s, %s, %s)",
                                           (submission_id, float(skor_ai), catatan_ai))
                            db.commit()
                            cursor.close()
                            db.close()
                            
                            st.success(f"Berhasil submit '{judul}'! Menunggu validasi atasan.")
                            st.subheader("Hasil Pra-Penilaian AI:")
                            st.metric(label="Skor AI", value=f"{skor_ai:.1f} / 100")
                            st.info(catatan_ai)
                            
                            # Hapus cache dan rerun
                            st.cache_data.clear()
                            st.rerun()

    # --- Tampilkan Grafik Kinerja & Rekomendasi ---
    st.header("Grafik Kinerja Anda (6 Bulan Terakhir)")
    df_kinerja = get_kinerja_asn(user_id)
    # (Logika grafik dan rekomendasi sama seperti sebelumnya)
    if df_kinerja.empty:
        st.info("Belum ada data evaluasi final dari atasan untuk ditampilkan.")
    else:
        st.line_chart(df_kinerja)
        if len(df_kinerja) >= 2:
            skor_terbaru = df_kinerja['rata_rata_skor'].iloc[-1]
            skor_sebelumnya = df_kinerja['rata_rata_skor'].iloc[-2]
            tren = skor_terbaru - skor_sebelumnya
            
            if tren < -5:
                st.error(f"🚨 **Rekomendasi:** Kinerja Anda menurun {tren:.1f} poin. Direkomendasikan ikut pelatihan [Manajemen Proyek].")
            elif tren > 5:
                st.success(f"🎉 **Rekomendasi:** Kinerja Anda meningkat {tren:.1f} poin! Kandidat kuat untuk [Talent Pool].")
            else:
                st.info("Kinerja Anda stabil.")

# =================================================================
# --- Tampilan 2: ATASAN ---
# =================================================================
if is_atasan:
    
    # --- Bagian 1: Buat Template Tugas ---
    st.header("Modul Atasan: Manajemen Template Tugas")
    with st.expander("Buat Template Tugas Baru", expanded=False):
        with st.form("form_template", clear_on_submit=True):
            st.write("Buat standar penilaian untuk tim Anda.")
            judul = st.text_input("Judul Tugas (cth: Laporan Absensi Bulanan)")
            keywords = st.text_input("Kata Kunci Wajib (pisahkan koma)", "laporan, rekapitulasi, absen, persentase")
            sections = st.text_input("Bagian Wajib (pisahkan koma)", "pendahuluan, analisis, kesimpulan")
            submit_template = st.form_submit_button("Buat Template")

            if submit_template and judul:
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO task_templates (atasan_id, judul_tugas, required_keywords, required_sections) VALUES (%s, %s, %s, %s)",
                                   (user_id, judul, keywords, sections))
                    db.commit()
                    cursor.close()
                    db.close()
                    st.success(f"Template '{judul}' berhasil dibuat!")
                    st.cache_data.clear() # Hapus cache agar ASN bisa lihat
                    st.rerun()

    # --- Bagian 2: Validasi Tugas Bawahan ---
    st.header("Validasi Kinerja Tim Anda")
    bawahan_list = get_bawahan(user_id)
    if not bawahan_list:
        st.info("Anda tidak memiliki bawahan untuk dievaluasi.")
        st.stop()

    bawahan_ids = [b['id'] for b in bawahan_list]
    df_submissions = get_submissions_for_atasan(bawahan_ids)

    if df_submissions.empty:
        st.info("Belum ada tugas yang dikumpulkan oleh tim Anda.")
        st.stop()

    pending_subs = df_submissions[df_submissions['skor_final_atasan'].isna()]
    selesai_subs = df_submissions[df_submissions['skor_final_atasan'].notna()]

    st.subheader(f"Tugas Menunggu Validasi ({len(pending_subs)})")
    
    if pending_subs.empty:
        st.success("Semua tugas sudah Anda validasi.")
    
    for _, row in pending_subs.iterrows():
        expander_title = f"**{row['nama_asn']}** - {row['judul_tugas']} (Submit: {row['tanggal_submit'].strftime('%d %b')})"
        
        with st.expander(expander_title):
            st.markdown(f"**ASN:** {row['nama_asn']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Hasil Pra-Penilaian AI:**")
                st.metric(label="Skor AI", value=f"{row['skor_ai']:.1f} / 100")
                st.info(f"**Catatan AI:**\n\n{row['catatan_ai']}")
                
                # Menampilkan kriteria yang dipakai AI
                st.markdown("**Kriteria yang Dinilai (dari Template):**")
                st.markdown(f" - *Keywords:* `{row['required_keywords']}`")
                st.markdown(f" - *Sections:* `{row['required_sections']}`")
                
                try:
                    with open(row['file_path'], "rb") as file:
                        st.download_button("Download Dokumen", file, os.path.basename(row['file_path']), "application/pdf")
                except FileNotFoundError:
                    st.error("File dokumen tidak ditemukan.")
            
            with col2:
                st.write("**Formulir Validasi Final:**")
                with st.form(key=f"form_val_{row['submission_id']}"):
                    skor_final = st.slider("Skor Final Anda:", 0.0, 100.0, float(row['skor_ai']), 0.5)
                    catatan = st.text_area("Catatan/Feedback Anda:", "")
                    submit_validasi = st.form_submit_button("Submit Validasi")

                    if submit_validasi:
                        db = connect_db()
                        if db:
                            cursor = db.cursor()
                            cursor.execute("""
                                UPDATE evaluasi_kinerja 
                                SET skor_final_atasan = %s, catatan_atasan = %s, tanggal_evaluasi = NOW()
                                WHERE submission_id = %s
                            """, (skor_final, catatan, row['submission_id']))
                            db.commit()
                            cursor.close()
                            db.close()
                            
                            st.success(f"Validasi untuk '{row['judul_tugas']}' berhasil disimpan!")
                            st.cache_data.clear() # Hapus cache
                            st.rerun() # Muat ulang
    
    st.subheader("Riwayat Tugas Selesai Divalidasi")
    st.dataframe(selesai_subs[['nama_asn', 'judul_tugas', 'tanggal_submit', 'skor_ai', 'skor_final_atasan']])