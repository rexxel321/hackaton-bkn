import PyPDF2
import re
import os

def analyze_document_ai(file_path, task_keywords_str):
    """
    Fungsi 'AI' kustom kita untuk menganalisis file PDF.
    Versi baru: Menganalisis berdasarkan kata kunci tugas yang dinamis.
    """
    try:
        # 1. Buka dan baca file PDF
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            for page in reader.pages:
                # Menambahkan spasi antar halaman untuk memastikan kata kunci tidak tergabung
                text += page.extract_text().lower() + " "

        skor = 0
        catatan = []

        # --- Kriteria Penilaian AI ---

        # Kriteria 1: Kelengkapan Struktur (Bobot 40)
        # Memeriksa struktur laporan standar
        if re.search(r'latar belakang|pendahuluan', text):
            skor += 15
            catatan.append("✔️ Pendahuluan terdeteksi.")
        else:
            catatan.append("❌ Tidak ada Pendahuluan/Latar Belakang.")

        if re.search(r'analisis|pembahasan|hasil', text):
            skor += 15
            catatan.append("✔️ Analisis/Pembahasan terdeteksi.")
        else:
            catatan.append("❌ Tidak ada Analisis/Pembahasan.")

        if re.search(r'rekomendasi|kesimpulan|penutup', text):
            skor += 10
            catatan.append("✔️ Kesimpulan/Rekomendasi terdeteksi.")
        else:
            catatan.append("❌ Tidak ada Kesimpulan/Penutup.")

        # Kriteria 2: Keluasan / Kedalaman (Bobot 30)
        # Menghitung jumlah kata total dalam dokumen
        word_count = len(text.split())
        if word_count > 1000:
            skor += 30
            catatan.append(f"✔️ Dokumen komprehensif ({word_count} kata).")
        elif word_count > 500:
            skor += 15
            catatan.append(f"⚠️ Dokumen cukup ({word_count} kata).")
        else:
            catatan.append(f"❌ Dokumen terlalu ringkas ({word_count} kata).")
        
        # Kriteria 3: Relevansi Tugas (Bobot 30)
        # AI akan mencari kata kunci yang diinput oleh ASN
        
        # Bersihkan dan pisahkan kata kunci
        task_keywords = [k.strip().lower() for k in task_keywords_str.split(',') if k.strip()]
        
        if not task_keywords:
            catatan.append("⚠️ Tidak ada kata kunci tugas yang dimasukkan untuk dinilai.")
        else:
            found_words = [word for word in task_keywords if word in text]
            
            if len(found_words) == len(task_keywords): # Menemukan semua kata kunci
                skor += 30
                catatan.append(f"✔️ Sangat Relevan. Semua kata kunci ditemukan: {', '.join(found_words)}.")
            elif len(found_words) >= 1: # Menemukan beberapa
                skor += 15
                catatan.append(f"⚠️ Cukup Relevan. Kata kunci ditemukan: {', '.join(found_words)}.")
            else: # Tidak menemukan satupun
                catatan.append(f"❌ Tidak Relevan. Tidak ada kata kunci tugas yang ditemukan di dokumen.")
        
        # --- Finalisasi Skor ---
        
        # Normalisasi skor (memastikan tidak lebih dari 100)
        final_skor = min(skor, 100)
        final_catatan = "\n".join(catatan)

        return final_skor, final_catatan

    except Exception as e:
        print(f"Error saat memproses PDF: {e}")
        return 0, f"Error: Gagal memproses file PDF. {e}"