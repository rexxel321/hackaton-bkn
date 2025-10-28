import PyPDF2
import re
import os
from collections import Counter

def analyze_submission_ai(file_path, template):
    """
    Fungsi 'AI' kustom V2 (Opsi 2).
    Menganalisis file PDF berdasarkan template yang dibuat atasan.
    
    'template' adalah dict dari database, cth:
    { 'required_keywords': 'laporan,absen', 'required_sections': 'pendahuluan,analisis' }
    """
    try:
        # 1. Buka dan baca file PDF
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text().lower() + " "

        skor = 0
        catatan = []
        words = text.split()
        word_count = len(words)
        word_freq = Counter(words)

        # --- Kriteria 1: Relevansi Kata Kunci (Bobot 40) ---
        # (Berdasarkan 'required_keywords' dari template)
        skor_relevansi = 0
        keywords_str = template.get('required_keywords', '')
        task_keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        
        if task_keywords:
            found_count = 0
            total_mentions = 0
            for k in task_keywords:
                if word_freq[k] > 0:
                    found_count += 1
                    total_mentions += word_freq[k]
            
            if found_count == len(task_keywords):
                skor_relevansi = 40 # Semua keyword ditemukan
                catatan.append(f"✔️ Relevansi: Sangat baik! Semua {len(task_keywords)} kata kunci ditemukan.")
            elif found_count > 0:
                skor_relevansi = 20 # Sebagian ditemukan
                catatan.append(f"⚠️ Relevansi: Cukup. Hanya {found_count} dari {len(task_keywords)} kata kunci ditemukan.")
            else:
                catatan.append("❌ Relevansi: Buruk. Tidak ada kata kunci relevan yang ditemukan.")
        else:
            catatan.append("⚠️ Relevansi: Tidak ada kata kunci wajib di template.")
        skor += skor_relevansi

        # --- Kriteria 2: Kelengkapan Struktur (Bobot 30) ---
        # (Berdasarkan 'required_sections' dari template)
        skor_struktur = 0
        sections_str = template.get('required_sections', '')
        task_sections = [s.strip().lower() for s in sections_str.split(',') if s.strip()]
        
        if task_sections:
            found_sections = [s for s in task_sections if re.search(s, text)]
            if len(found_sections) == len(task_sections):
                skor_struktur = 30
                catatan.append(f"✔️ Struktur: Lengkap! Semua {len(task_sections)} bagian ditemukan.")
            elif len(found_sections) > 0:
                skor_struktur = 15
                catatan.append(f"⚠️ Struktur: Kurang. Hanya menemukan: {', '.join(found_sections)}.")
            else:
                catatan.append("❌ Struktur: Buruk. Tidak ada bagian wajib yang ditemukan.")
        else:
            catatan.append("⚠️ Struktur: Tidak ada bagian wajib di template.")
        skor += skor_struktur

        # --- Kriteria 3: Kualitas Analisis (Bobot 20) ---
        # (Indikator generik untuk 'insight')
        skor_analisis = 0
        insight_keywords = ['rekomendasi', 'solusi', 'usulan', 'penyebab', 'evaluasi', 'tindak lanjut']
        insight_count = sum(1 for word in insight_keywords if word in text)
        
        if insight_count >= 3:
            skor_analisis = 20
            catatan.append("✔️ Kualitas: Baik. Dokumen berorientasi solusi.")
        elif insight_count >= 1:
            skor_analisis = 10
            catatan.append("⚠️ Kualitas: Cukup. Dokumen bersifat deskriptif.")
        else:
            catatan.append("❌ Kualitas: Buruk. Laporan hanya deskriptif, tidak ada insight.")
        skor += skor_analisis

        # --- Kriteria 4: Keluasan Dokumen (Bobot 10) ---
        skor_keluasan = 0
        if word_count > 500:
            skor_keluasan = 10
            catatan.append(f"✔️ Keluasan: Komprehensif ({word_count} kata).")
        elif word_count > 200:
            skor_keluasan = 5
            catatan.append(f"⚠️ Keluasan: Cukup ({word_count} kata).")
        else:
            catatan.append(f"❌ Keluasan: Terlalu ringkas ({word_count} kata).")
        skor += skor_keluasan

        # --- Finalisasi Skor ---
        final_skor = min(skor, 100)
        final_catatan = "\n".join(catatan)

        return final_skor, final_catatan

    except Exception as e:
        print(f"Error saat memproses PDF: {e}")
        return 0, f"Error: Gagal memproses file PDF. {e}"