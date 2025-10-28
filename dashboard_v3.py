import streamlit as st
import pandas as pd
import mysql.connector
import os
from datetime import datetime
# --- IMPORT FILE AI V3 KITA ---
from ai_logic_v3 import analyze_submission_ai_v3

# --- Konfigurasi Database ---
def connect_db():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="", # GANTI DENGAN PASSWORD MYSQL ANDA
            database="hackathon_bkn"
        )
        # Set auto-commit agar perubahan langsung tersimpan
        db.autocommit = True
        return db
    except mysql.connector.Error as e:
        st.error(f"Error koneksi DB: {e}")
        return None

# --- Fungsi Bantuan Database (CRUD) ---

@st.cache_data(ttl=60)
def get_user(email):
    db = connect_db()
    if db:
        with db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM asn WHERE email = %s", (email,))
            user = cursor.fetchone()
        db.close()
        return user
    return None

@st.cache_data(ttl=60)
def get_bawahan(atasan_id):
    db = connect_db()
    if db:
        with db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM asn WHERE atasan_id = %s", (atasan_id,))
            bawahan = cursor.fetchall()
        db.close()
        return bawahan
    return []

@st.cache_data(ttl=60)
def get_all_kompetensi():
    """(Level-Up 3) Mengambil daftar kompetensi dari DB."""
    db = connect_db()
    if db:
        with db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM kompetensi ORDER BY nama_kompetensi")
            kompetensi = cursor.fetchall()
        db.close()
        return kompetensi
    return []

@st.cache_data(ttl=60)
def get_task_templates_for_asn(atasan_id):
    """Mengambil template tugas yang ditugaskan oleh atasan."""
    db = connect_db()
    if db:
        with db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM task_templates WHERE atasan_id = %s", (atasan_id,))
            templates = cursor.fetchall()
            
            # (Level-Up 3) Ambil juga kompetensi untuk setiap template
            for t in templates:
                cursor.execute("""
                    SELECT k.nama_kompetensi 
                    FROM template_kompetensi_mapping tm
                    JOIN kompetensi k ON tm.kompetensi_id = k.id
                    WHERE tm.template_id = %s
                """, (t['id'],))
                t['kompetensi_list'] = [k['nama_kompetensi'] for k in cursor.fetchall()]
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
            s.id as submission_id, s.file_path, s.tanggal_submit,
            a.nama_asn,
            t.judul_tugas, t.tipe_dokumen,
            e.skor_ai, e.catatan_ai, e.skor_final_atasan
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
def get_kinerja_asn_overall(asn_id):
    """Mengambil riwayat kinerja UMUM ASN untuk grafik (Line chart)."""
    db = connect_db()
    if not db:
        return pd.DataFrame()
    
    query = """
        SELECT DATE_FORMAT(s.tanggal_submit, '%Y-%m') as bulan, 
               AVG(e.skor_final_atasan) as rata_rata_skor
        FROM evaluasi_kinerja e
        JOIN task_submissions s ON e.submission_id = s.id
        WHERE s.asn_id = %s AND e.skor_final_atasan IS NOT NULL
          AND s.tanggal_submit >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY bulan
        ORDER BY bulan ASC
    """
    df = pd.read_sql(query, db, params=(asn_id,))
    db.close()
    if not df.empty:
        df = df.set_index('bulan')
    return df

@st.cache_data(ttl=30)
def get_kompetensi_performance(asn_id):
    """(Level-Up 3) Mengambil skor rata-rata per KOMPETENSI (Bar chart)."""
    db = connect_db()
    if not db:
        return pd.DataFrame()
    
    query = """
        SELECT 
            k.nama_kompetensi, 
            AVG(e.skor_final_atasan) as rata_rata_skor
        FROM evaluasi_kinerja e
        JOIN task_submissions s ON e.submission_id = s.id
        JOIN template_kompetensi_mapping tm ON s.template_id = tm.template_id
        JOIN kompetensi k ON tm.kompetensi_id = k.id
        WHERE s.asn_id = %s AND e.skor_final_atasan IS NOT NULL
        GROUP BY k.nama_kompetensi
    """
    df = pd.read_sql(query, db, params=(asn_id,))
    db.close()
    if not df.empty:
        df = df.set_index('nama_kompetensi')
    return df

def check_submission_exists(asn_id, template_id):
    db = connect_db()
    if db:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 FROM task_submissions WHERE asn_id = %s AND template_id = %s", (asn_id, template_id))
            exists = cursor.fetchone()
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
st.set_page_config(page_title="PERFORMA-AI V3", layout="wide")
st.title("🚀 PERFORMA-AI: Sistem Evaluasi Kinerja Adaptif")

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
        
        already_submitted = check_submission_exists(user_id, template_id)
        
        if already_submitted:
            st.success(f"✔️ **{judul}** (Sudah Dikerjakan)")
            continue
        
        with st.expander(f"📝 **{judul}** (Belum Dikerjakan)", expanded=True):
            st.markdown("**Kriteria Penilaian dari Atasan:**")
            
            # (Level-Up 3) Tampilkan kompetensi
            st.markdown(f" - **Kompetensi Terkait:** `{' | '.join(template['kompetensi_list'])}`")
            # (Level-Up 2) Tampilkan Tipe Dokumen
            st.markdown(f" - **Tipe Dokumen:** `{template['tipe_dokumen']}`")
            st.markdown(f" - **Kata Kunci Wajib:** `{template['required_keywords']}`")
            st.markdown(f" - **Bagian Wajib:** `{template['required_sections']}`")
            
            # (Level-Up 1) Tampilkan Bobot
            st.markdown(f" - **Bobot:** Relevansi ({template['weight_relevansi']}%), Struktur ({template['weight_struktur']}%), Analisis ({template['weight_analisis']}%), Keluasan ({template['weight_keluasan']}%)")

            with st.form(key=f"form_task_{template_id}", clear_on_submit=True):
                uploaded_file = st.file_uploader("Upload Dokumen (PDF Saja):", type=["pdf"])
                submit_button = st.form_submit_button("Submit Tugas")

                if submit_button and uploaded_file is not None:
                    filename = f"{user_id}_{template_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    with st.spinner(f"AI V3 sedang menganalisis '{judul}'..."):
                        # Panggil AI V3 yang baru
                        skor_ai, catatan_ai = analyze_submission_ai_v3(file_path, template)
                        
                        db = connect_db()
                        if db:
                            with db.cursor() as cursor:
                                cursor.execute("INSERT INTO task_submissions (template_id, asn_id, file_path) VALUES (%s, %s, %s)",
                                               (template_id, user_id, file_path))
                                submission_id = cursor.lastrowid
                                
                                cursor.execute("INSERT INTO evaluasi_kinerja (submission_id, skor_ai, catatan_ai) VALUES (%s, %s, %s)",
                                               (submission_id, float(skor_ai), catatan_ai))
                            db.close()
                            
                            st.success(f"Berhasil submit '{judul}'! Menunggu validasi atasan.")
                            st.subheader("Hasil Pra-Penilaian AI (V3):")
                            st.metric(label="Skor AI (Weighted)", value=f"{skor_ai:.1f} / 100")
                            st.info(catatan_ai)
                            
                            st.cache_data.clear()
                            st.rerun()

    # --- Tampilkan Dashboard Kinerja (Level-Up 3) ---
    st.header("Dashboard Kinerja Anda")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Tren Kinerja Overall (6 Bulan)")
        df_kinerja = get_kinerja_asn_overall(user_id)
        if df_kinerja.empty:
            st.info("Belum ada data evaluasi final.")
        else:
            st.line_chart(df_kinerja)
    
    with col2:
        st.subheader("Skor Rata-rata per Kompetensi")
        df_kompetensi = get_kompetensi_performance(user_id)
        if df_kompetensi.empty:
            st.info("Belum ada skor per kompetensi.")
        else:
            st.bar_chart(df_kompetensi)

    # --- Logika Rekomendasi (Level-Up 3) ---
    st.subheader("Rekomendasi Pengembangan Diri")
    if not df_kompetensi.empty:
        # Cari kompetensi terlemah
        lemah = df_kompetensi[df_kompetensi['rata_rata_skor'] < 65].sort_values('rata_rata_skor')
        if not lemah.empty:
            for nama_kompetensi, row in lemah.iterrows():
                st.error(f"🚨 **Rekomendasi:** Kinerja Anda untuk kompetensi **'{nama_kompetensi}'** masih di bawah standar (Skor: {row['rata_rata_skor']:.1f}). Kami merekomendasikan Anda untuk mengikuti pelatihan [e-Learning: {nama_kompetensi} untuk ASN].")
        else:
            st.success("🎉 Selamat! Kinerja Anda di semua kompetensi sudah di atas standar. Pertahankan!")
    else:
        st.info("Rekomendasi akan muncul setelah Anda menyelesaikan tugas dan divalidasi atasan.")

# =================================================================
# --- Tampilan 2: ATASAN ---
# =================================================================
if is_atasan:
    
    # --- Bagian 1: Buat Template Tugas (Full Upgrade) ---
    st.header("Modul Atasan: Manajemen Template Tugas")
    with st.expander("Buat Template Tugas Baru (V3)", expanded=False):
        
        kompetensi_options_all = get_all_kompetensi()
        kompetensi_dict = {k['nama_kompetensi']: k['id'] for k in kompetensi_options_all}
        
        with st.form("form_template", clear_on_submit=False):
            st.write("Buat standar penilaian adaptif untuk tim Anda.")
            judul = st.text_input("1. Judul Tugas (cth: Laporan Analisis Kinerja)")
            
            # (Level-Up 3) Pilih Kompetensi
            kompetensi_terpilih_nama = st.multiselect(
                "2. Kompetensi Terkait (Level-Up 3)",
                options=kompetensi_dict.keys()
            )
            
            # (Level-Up 2) Pilih Tipe Dokumen
            tipe_dokumen = st.selectbox(
                "3. Tipe Dokumen (Level-Up 2)",
                options=['Analitis/Data', 'Deskriptif/Notulensi', 'Esai/Opini']
            )

            st.markdown("---")
            st.markdown("4. Kriteria Penilaian (Opsional):")
            keywords = st.text_input("Kata Kunci Wajib (pisahkan koma)", "laporan, analisis, rekomendasi")
            sections = st.text_input("Bagian Wajib (pisahkan koma)", "pendahuluan, pembahasan, kesimpulan")
            
            st.markdown("---")
            # (Level-Up 1) Set Bobot
            st.markdown("5. Atur Bobot Penilaian (Total harus 100)")
            w_rel = st.slider("Bobot Relevansi (%)", 0, 100, 25)
            w_str = st.slider("Bobot Struktur (%)", 0, 100, 25)
            w_ana = st.slider("Bobot Kualitas Analisis (%)", 0, 100, 25)
            w_kel = st.slider("Bobot Keluasan (%)", 0, 100, 25)
            
            total_bobot = w_rel + w_str + w_ana + w_kel
            if total_bobot != 100:
                st.error(f"Total Bobot harus 100! Saat ini: {total_bobot}")

            submit_template = st.form_submit_button("Buat Template")

            if submit_template and judul and (total_bobot == 100):
                db = connect_db()
                if db:
                    with db.cursor() as cursor:
                        # Insert ke task_templates
                        sql = """INSERT INTO task_templates 
                                 (atasan_id, judul_tugas, required_keywords, required_sections, tipe_dokumen, 
                                  weight_relevansi, weight_struktur, weight_analisis, weight_keluasan) 
                                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                        val = (user_id, judul, keywords, sections, tipe_dokumen, w_rel, w_str, w_ana, w_kel)
                        cursor.execute(sql, val)
                        template_id = cursor.lastrowid
                        
                        # (Level-Up 3) Insert ke tabel mapping kompetensi
                        kompetensi_terpilih_ids = [kompetensi_dict[nama] for nama in kompetensi_terpilih_nama]
                        map_sql = "INSERT INTO template_kompetensi_mapping (template_id, kompetensi_id) VALUES (%s, %s)"
                        map_val = [(template_id, k_id) for k_id in kompetensi_terpilih_ids]
                        cursor.executemany(map_sql, map_val)
                    
                    db.close()
                    st.success(f"Template '{judul}' berhasil dibuat!")
                    st.cache_data.clear()
                    st.rerun()
            elif submit_template:
                st.error("Gagal. Pastikan Judul diisi dan Total Bobot adalah 100.")

    # --- Bagian 2: Validasi Tugas Bawahan ---
    st.header("Validasi Kinerja Tim Anda")
    # (Logika di bagian ini sama persis dengan Opsi 2, tidak perlu diubah)
    bawahan_list = get_bawahan(user_id)
    if not bawahan_list: st.stop()
    bawahan_ids = [b['id'] for b in bawahan_list]
    df_submissions = get_submissions_for_atasan(bawahan_ids)
    if df_submissions.empty: st.stop()

    pending_subs = df_submissions[df_submissions['skor_final_atasan'].isna()]
    selesai_subs = df_submissions[df_submissions['skor_final_atasan'].notna()]

    st.subheader(f"Tugas Menunggu Validasi ({len(pending_subs)})")
    
    if pending_subs.empty:
        st.success("Semua tugas sudah Anda validasi.")
    
    for _, row in pending_subs.iterrows():
        expander_title = f"**{row['nama_asn']}** - {row['judul_tugas']} (Tipe: {row['tipe_dokumen']})"
        
        with st.expander(expander_title):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Hasil Pra-Penilaian AI (V3):**")
                st.metric(label="Skor AI (Weighted)", value=f"{row['skor_ai']:.1f} / 100")
                st.info(f"**Catatan AI:**\n\n{row['catatan_ai']}")
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
                            with db.cursor() as cursor:
                                cursor.execute("""
                                    UPDATE evaluasi_kinerja 
                                    SET skor_final_atasan = %s, catatan_atasan = %s, tanggal_evaluasi = NOW()
                                    WHERE submission_id = %s
                                """, (skor_final, catatan, row['submission_id']))
                            db.close()
                            st.success(f"Validasi untuk '{row['judul_tugas']}' berhasil disimpan!")
                            st.cache_data.clear()
                            st.rerun()
    
    st.subheader("Riwayat Tugas Selesai Divalidasi")
    st.dataframe(selesai_subs[['nama_asn', 'judul_tugas', 'skor_ai', 'skor_final_atasan']])