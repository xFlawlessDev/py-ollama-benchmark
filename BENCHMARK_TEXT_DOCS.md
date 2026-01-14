# Benchmark Protocol: Text & Logic Engine

**Scope:** Pure Text Generation, Coding Logic, & RAG Retrieval.
**Target Hardware:** Ryzen AI Max 395 (96GB VRAM Split).

## 1. Key Metrics (Metrik Kunci)

Dalam benchmarking teks, ada dua jenis kecepatan yang harus dibedakan secara tegas:

### A. Generation Speed (Eval Rate)

* **Apa itu:** Kecepatan model "menulis" jawaban kata per kata.
* **Unit:** Tokens/Second (t/s).
* **Penting untuk:** User experience saat chatting.
* **Target (Qwen 32B @ Ryzen AI Max):**
* Single User: **40 - 60 t/s**.
* 10 Users: **10 - 15 t/s**.



### B. Prompt Processing Speed (Prompt Eval Rate)

* **Apa itu:** Kecepatan model "membaca" dan memahami konteks input (dokumen PDF panjang, history chat lama) sebelum mulai menjawab.
* **Penting untuk:** RAG, Summarization, dan Analisis Dokumen Legal.
* **Target:** Ryzen AI Max dengan `OLLAMA_FLASH_ATTENTION=1` harusnya bisa mencapai **> 500 t/s** (sangat cepat).

### C. Reliability Metrics (Success vs Fail)

Script benchmark teks kini mencatat **Success vs Fail** secara eksplisit.

*   **Penyebab Fail Umum di Teks:**
    1.  **Context Window Exceeded:** Prompt user + History > Kapasitas Context Model (misal 32k). Ini sering terjadi pada skenario Summarization atau Coding panjang.
    2.  **Server Timeout:** Antrian `OLLAMA_NUM_PARALLEL` penuh, request user ke-N menunggu lebih dari 60 detik (default timeout script).
    3.  **KV Cache Eviction:** Saat memori penuh, performa bisa drop drastis atau request di-kill.

---

## 2. Kalkulasi Throughput Text-Only

Model Teks murni (seperti `qwen2.5:32b` atau `llama3.1`) lebih ringan secara komputasi daripada model Vision, karena tidak ada *Vision Encoder* yang berjalan.

**Estimasi Peningkatan Kapasitas:**
Jika pada Vision Benchmark Anda mendapat Total Throughput 100 t/s, pada Text Benchmark Anda bisa berharap kenaikan sekitar **15-20%**.

Ini berarti Anda mungkin bisa menaikkan `OLLAMA_NUM_PARALLEL` lebih tinggi (misal ke **10** atau **12**) khusus untuk model teks.

---

## 3. Analisis Hasil Skenario

Saat Anda melihat file CSV hasil benchmark, perhatikan pola berikut:

### Skenario: CODING_HEAVY

Coding membutuhkan logika deduktif yang dalam. Biasanya TPS-nya lebih rendah daripada Chat biasa.

* *Indikator Sehat:* Jika speed Coding hanya drop **10-15%** dibanding Chat biasa.
* *Indikator Masalah:* Jika speed Coding drop **> 50%**, berarti model mengalami kesulitan komputasi (Compute Bound), bukan Memory Bound.

### Analisis Failure Rate (Troubleshooting)

Jika Anda melihat kolom `Fail` mulai terisi (angka > 0):

| Gejala | Retry Strategy | Solusi Root Cause |
| :--- | :--- | :--- |
| **Fail di High Concurrency (16+ used)** | Kemungkinan Timeout. Server terlalu lambat memproses antrian. | Turunkan `OLLAMA_NUM_PARALLEL`. Jangan set > 12 untuk model 30B+. |
| **Fail di Input Panjang (Summarize)** | Kemungkinan Context Overflow. | Cek `OLLAMA_NUM_CTX`. Naikkan ke 16384 atau 32768 jika VRAM cukup. |
| **Random Fails** | Kemungkinan VRAM Fragmentation atau OOM sesaat. | Restart service Ollama. Cek apakah ada model lain yang load di background. |

### Skenario: RAG_FLOW

Perhatikan kolom `embed_latency` (jika Anda menambahkannya ke log) atau selisih waktu.

* Tujuan RAG benchmark adalah melihat apakah proses *Embedding* (Qwen-Embed) mencuri bandwidth dari proses *Generation* (Qwen-Text).
* Karena Anda menggunakan **Dual-Residency (MAX_LOADED_MODELS=2)**, harusnya tidak ada penalti waktu (zero overhead).

---

## 4. Rekomendasi Tuning Text-Only

Jika server ini khusus dipakai untuk Text/Coding (tanpa gambar), Anda bisa mengubah konfigurasi `.env` sedikit lebih agresif:

1. **Naikkan Parallelism:**
Dari `OLLAMA_NUM_PARALLEL=6` (Vision) -> Naikkan ke **8** atau **10**.
*Alasan:* Beban komputasi teks lebih ringan, jadi GPU bisa handle lebih banyak thread bersamaan.
2. **Konteks Lebih Panjang:**
Tanpa beban memori gambar, Anda bisa memberikan jatah konteks (Context Window) lebih besar ke user, misal **16k** atau **32k** per user, sangat berguna untuk analisa dokumen tebal.
3. **Model Lebih Besar (Opsional):**
Untuk teks murni, Anda bahkan bisa mencoba **Llama 3.1 70B** (Q4_K_M).
* VRAM: ~42GB.
* Sisa untuk User: ~54GB (Masih cukup untuk ~20 user).
* *Keuntungan:* Kecerdasan jauh lebih tinggi (setara GPT-4).
* *Kerugian:* Speed per user akan turun separuhnya (~20-30 t/s single user).