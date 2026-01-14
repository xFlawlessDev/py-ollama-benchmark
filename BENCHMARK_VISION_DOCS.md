# Benchmark Protocol: Vision-Language (Multimodal)

**Scope:** Image Processing (OCR, Analysis) & Visual QA.
**Target Hardware:** Ryzen AI Max 395 (96GB VRAM Split).
**Model Target:** `qwen3-vl:30b`

## 1. Metrik Kunci Vision (The "Vision Tax")

Berbeda dengan teks, vision memiliki satu metrik krusial tambahan:

### A. Image Processing Time (Prompt Eval Duration)

* **Apa itu:** Waktu yang dibutuhkan model untuk "menatap" gambar dan mengubahnya menjadi ribuan token visual sebelum mulai menjawab.
* **Kenapa Penting:** Ini adalah *Latency Awal* (Time To First Token/TTFT) yang dirasakan user. User mengupload gambar, lalu menunggu...
* **Target Ryzen AI Max:**
* Gambar Sedang (720p): **< 1.0 detik**.
* Gambar Besar (4K / Dokumen Padat): **1.5 - 3.0 detik**.



### B. Generation Speed (Post-Vision TPS)

* **Apa itu:** Setelah gambar diproses, seberapa cepat model menulis jawabannya.
* **Analisis:** Kecepatan ini biasanya **sedikit lebih lambat** daripada model teks murni (misal: Qwen-Text 32B vs Qwen-VL 32B) karena arsitektur VL lebih kompleks.

### C. Stabilitas Sistem (Success vs Fail)

Script benchmark baru kini melacak **Success Rate**:

*   **Success:** Request berhasil mendapat respon 200 OK lengkap dalam batas waktu (timeout).
*   **Failure:** Request gagal karena:
    *   **Timeout:** Server terlalu sibuk sehingga tidak menjawab dalam 300 detik.
    *   **OOM (Out of Memory):** VRAM penuh saat mencoba memproses batch image baru, menyebabkan Ollama crash atau melempar error 500.
    *   **Connection Error:** Antrian request penuh.

**Aturan Praktis:**
Dalam produksi enterprise, **Failure Rate harus 0%**. Satu kegagalan berarti satu user yang kecewa. Jika fail count > 0, berarti concurrency setting `OLLAMA_NUM_PARALLEL` Anda terlalu tinggi.

---

## 2. Tantangan Teknis: Bandwidth Shock

Saat 8 user mengupload gambar secara bersamaan pada arsitektur *Unified Memory*:

1. **Lonjakan Data:** 8 gambar  ukuran file  dikirim ke VRAM.
2. **Proses Encoder:** Vision Encoder `qwen3-vl` bekerja keras mengubah piksel menjadi matriks perhatian (attention matrices). Ini memakan bandwidth memori yang luar biasa besar dalam waktu singkat.

**Dampak pada Ryzen AI Max:**
Bandwidth ~130 GB/s akan langsung jenuh (saturated).

* **Gejala:** Anda akan melihat `Image Process Time` melonjak drastis. Jika 1 user butuh 0.5s, maka 8 user mungkin butuh 4-6 detik hanya untuk memproses gambar, sebelum mulai mengetik.

---

## 3. Analisis Hasil Skenario

Saat menganalisis CSV output:

### Skenario: OCR_HEAVY_LOAD (Beban Puncak)

Ini adalah tes terberat bagi sistem Anda. Model harus memahami detail gambar dan menulis jawaban panjang.

**Cara Membaca Data:**
Perhatikan kolom `img_proc_time` (Waktu Proses Gambar) saat user bertambah.

| Users | Avg TPS (Speed Ngetik) | Image Proc Time (Speed Melihat) | Success/Fail | Status |
| --- | --- | --- | --- | --- |
| 1 | 45 t/s | 0.6 s | 1/0 | **Excellent** |
| 4 | 20 t/s | 1.2 s | 4/0 | **Good** (Linear scaling) |
| **8** | **10 t/s** | **3.5 s** | **8/0** | **Bandwidth Limit Hit!** (Safe Max) |
| 12 | 5 t/s | 6.0 s | 12/0 | **Overloaded** (Too slow but working) |
| 16 | 2 t/s | 15.0 s | **12/4** | **CRITICAL FAILURE** (Timeouts/Crashes) |

**Interpretasi Data & Kegagalan:**

1.  **The "Safe Max" (8 Users):** Waktu tunggu "melihat gambar" (3.5s) adalah batas psikologis user. Di atas ini, user akan mengira aplikasi hang. Setting `OLLAMA_NUM_PARALLEL=8` adalah batas absolut.
2.  **The "Critical Failure" (16 Users):** Perhatikan kolom **Success/Fail (12/4)**.
    *   Angka `4` failures menunjukkan server menolak melayani.
    *   Penyebab: Antrian penuh (kv cache full), atau *watchdog timer* mematikan request yang nyangkut terlalu lama.
    *   **Tindakan:** Jika Anda melihat failure muncul, **TURUNKAN** `OLLAMA_NUM_PARALLEL` segera. Jangan paksa hardware.

---

## 4. Rekomendasi Operasional Vision

Berdasarkan karakteristik beban kerja vision:

1. **Parallelism Lebih Rendah:**
Jangan samakan dengan teks. Jika teks bisa 10-12 paralel, Vision sebaiknya dibatasi di **6-8 paralel** agar `Image Process Time` tidak meledak.
2. **Wajib Flash Attention:**
Pastikan `OLLAMA_FLASH_ATTENTION=1` aktif. Tanpa ini, memproses gambar resolusi tinggi akan menyebabkan penggunaan VRAM melonjak tajam (memory spike) dan bisa OOM walau VRAM 96GB.
3. **Edukasi User (Resolusi Gambar):**
Beritahu tim Anda: "Tidak perlu upload foto 4K dari HP untuk OCR struk belanja". Gambar 720p atau 1080p sudah lebih dari cukup untuk `qwen3-vl` dan jauh lebih ramah bandwidth server.