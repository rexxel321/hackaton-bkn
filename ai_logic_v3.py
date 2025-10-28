import PyPDF2
import re
import os
from collections import Counter

def analyze_submission_ai_v3(file_path, template):
    """
    Fungsi 'AI' kustom V3 (Implementasi 3 Level-Up).
    Menganalisis file PDF berdasarkan template yang DIBOBOTKAN oleh atasan.
    
    'template' adalah dict lengkap dari database, berisi:
    - required_keywords, required_sections
    - tipe_dokumen ('Analitis/Data', 'Deskriptif/Notulensi', dll.)
    - weight_relevansi, weight_struktur, weight_analisis, weight_keluasan
    """
    try:
        # 1. Buka dan baca file PDF
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text().lower() + " "

        final_skor = 0
        catatan = ["**Laporan Analisis AI (V3):**"]
        words = text.split()
        word_count = len(words)
        word_freq = Counter(words)

        # --- Menghitung 4 SKOR MENTAH (0-100) ---

        # 1. SKOR MENTAH: Relevansi Kata Kunci
        raw_score_relevansi = 0
        keywords_str = template.get('required_keywords', '')
        task_keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        if task_keywords:
            found_count = sum(1 for k in task_keywords if word_freq[k] > 0)
            if found_count == len(task_keywords):
                raw_score_relevansi = 100 # Semua keyword ditemukan
            elif found_count > 0:
                raw_score_relevansi = 50 # Sebagian ditemukan
        
        catatan.append(f"1. Relevansi: {raw_score_relevansi}/100 (Ditemukan {found_count}/{len(task_keywords)} kata kunci)")

        # 2. SKOR MENTAH: Kelengkapan Struktur
        raw_score_struktur = 0
        sections_str = template.get('required_sections', '')
        task_sections = [s.strip().lower() for s in sections_str.split(',') if s.strip()]
        if task_sections:
            found_sections = [s for s in task_sections if re.search(s, text)]
            raw_score_struktur = (len(found_sections) / len(task_sections)) * 100
        
        catatan.append(f"2. Struktur: {raw_score_struktur:.0f}/100 (Ditemukan {len(found_sections)}/{len(task_sections)} bagian)")

        # 3. SKOR MENTAH: Kualitas Analisis (Level-Up 2)
        raw_score_analisis = 0
        insight_keywords = ['rekomendasi', 'solusi', 'usulan', 'penyebab', 'evaluasi', 'tindak lanjut']
        insight_count = sum(1 for word in insight_keywords if word in text)
        
        # Cek insight (50%)
        if insight_count >= 3:
            raw_score_analisis += 50
        elif insight_count >= 1:
            raw_score_analisis += 25
        
        # Cek Kuantitatif (50%) - HANYA jika tipe 'Analitis'
        if template['tipe_dokumen'] == 'Analitis/Data':
            # Mencari angka (cth: 123), persentase (cth: 50%), atau mata uang (cth: Rp)
            if re.search(r'(\d+)|(\d+%)|(rp\s*\d+)', text):
                raw_score_analisis += 50 # Ditemukan data kuantitatif
                catatan.append("✔️ Kualitas: Data kuantitatif terdeteksi.")
            else:
                catatan.append("❌ Kualitas: Laporan analitis ini tidak mengandung data kuantitatif (angka/persen).")
        else:
            # Jika bukan analitis, 50% sisanya diambil dari insight lagi
            raw_score_analisis *= 2 # Skor insight di-double
            
        catatan.append(f"3. Kualitas Analisis: {raw_score_analisis}/100")

        # 4. SKOR MENTAH: Keluasan Dokumen
        raw_score_keluasan = 0
        if word_count > 1000:
            raw_score_keluasan = 100
        elif word_count > 500:
            raw_score_keluasan = 75
        elif word_count > 200:
            raw_score_keluasan = 50
        
        catatan.append(f"4. Keluasan: {raw_score_keluasan}/100 ({word_count} kata)")

        # --- Kalkulasi Skor Akhir (Level-Up 1: Weighted Average) ---
        final_skor = (
            (raw_score_relevansi * template['weight_relevansi'] / 100) +
            (raw_score_struktur * template['weight_struktur'] / 100) +
            (raw_score_analisis * template['weight_analisis'] / 100) +
            (raw_score_keluasan * template['weight_keluasan'] / 100)
        )
        
        final_catatan = "\n".join(catatan)
        return final_skor, final_catatan

    except Exception as e:
        print(f"Error saat memproses PDF: {e}")
        return 0, f"Error: Gagal memproses file PDF. {e}"