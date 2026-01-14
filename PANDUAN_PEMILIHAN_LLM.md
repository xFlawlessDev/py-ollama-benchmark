# Panduan Komprehensif Pemilihan Model LLM dan Embedding untuk Infrastruktur Lokal

**Versi Dokumen:** 1.0  
**Target Audiens:** DevOps Engineer, AI Infrastructure Architect  
**Fokus:** Self-Hosted Inference (High-Performance Workstation/Server)

---

## 1. Pendahuluan

### 1.1 Tujuan
Dokumen ini berfungsi sebagai panduan teknis bagi tim DevOps dalam merancang arsitektur inferensi lokal yang efisien. Fokus utamanya adalah pemilihan model Large Language Model (LLM) dan Embedding yang optimal berdasarkan kendala perangkat keras (hardware constraints) dan karakteristik beban kerja (workload).

### 1.2 Cakupan
Panduan ini mencakup:
*   Analisis trade-off antara ukuran model, kuantisasi, dan akurasi.
*   Metodologi pemilihan model embedding untuk aplikasi RAG (Retrieval-Augmented Generation).
*   Strategi manajemen sumber daya untuk skenario *Single-User* vs *Multi-User*.
*   Contoh studi kasus implementasi pada perangkat keras *Unified Memory Architecture* modern (Ryzen AI Max 395).

### 1.3 Metodologi
Rekomendasi dalam dokumen ini didasarkan pada kalkulasi teknis (bottom-up approach) yang meliputi limitasi VRAM, bandwidth memori, dan estimasi throughput token, bukan sekadar skor benchmark sintetik.

---

## 2. Faktor Penentu Pemilihan Model LLM

Dalam lingkungan *self-hosted*, pemilihan model adalah permainan kompromi antara tiga variabel utama: **Kualitas (Reasoning)**, **Kecepatan (Latency/Throughput)**, dan **Biaya (VRAM/Compute)**.

### 2.1 Ukuran Parameter (Parameter Count)
Ukuran parameter berkorelasi langsung dengan kemampuan *reasoning* dan kebutuhan memori.

| Kelas Model | Ukuran (Contoh) | Karakteristik & Use Case | Kebutuhan VRAM (FP16) |
| :--- | :--- | :--- | :--- |
| **Small** | 7B - 14B | Cepat, efisien. Cocok untuk tugas spesifik (summarization, classification) atau chat ringan. | 14GB - 28GB |
| **Medium** | 32B - 70B | Keseimbangan terbaik. Kemampuan instruksi kompleks setara GPT-3.5/GPT-4 awal. Cocok untuk Coding & RAG umum. | 64GB - 140GB |
| **Large** | 100B+ | *State-of-the-art reasoning*. Sangat lambat di hardware komoditas. Hanya untuk riset atau batch processing kompleks. | >200GB |

### 2.2 Kuantisasi (Quantization)
Kuantisasi adalah faktor paling kritikal untuk menjalankan model Medium/Large di hardware terbatas. Ini mengurangi presisi bobot model dari 16-bit (FP16) ke bit yang lebih rendah.

*   **FP16/BF16**: Standar training. Akurasi 100%. Boros memori.
*   **GGUF/EXL2 (4-bit / Q4_K_M)**: "Sweet Spot" industri saat ini. Mengurangi penggunaan memori hingga ~50-60% dengan degradasi akurasi yang **dapat diabaikan** (< 1-2% perplexity loss).
*   **Extreme Low-Bit (Q2/Q3)**: Tidak disarankan untuk *reasoning* berat. Model menjadi "halu" (incoherent).

> **Rule of Thumb:** Lebih baik menjalankan model **Besar (70B) di Q4** daripada model **Kecil (30B) di FP16**. "Model size beats precision."

### 2.3 Context Window & KV Cache
Panjang konteks (misal: 8k vs 128k token) bukan hanya fitur, tapi beban infrastruktur.
*   **Linear/Quadratic Growth**: Konsumsi memori untuk menyimpan konteks (KV Cache) tumbuh seiring panjangnya input.
*   **KV Cache Quantization**: Pada konteks sangat panjang (long-context RAG), pertimbangkan menggunakan **FP8 KV Cache** (opsiteredia di vLLM/llama.cpp) untuk menghemat VRAM hingga 2x tanpa degradasi berarti.

---

## 3. Strategi Pemilihan Model Embedding

Model embedding mengubah teks menjadi vektor numerik untuk pencarian semantik (RAG). Pemilihannya sering diabaikan, padahal krusial untuk akurasi retrieval.

### 3.1 Kriteria Seleksi (MTEB Leaderboard)
Gunakan acuan **MTEB (Massive Text Embedding Benchmark)**. Jangan terpaku pada model OpenAI (text-embedding-3). Model open-source seringkali lebih performant dan efisien.

### 3.2 Pertimbangan Teknis
1.  **Sequence Length**:
    *   **512 tokens**: Cukup untuk pencarian kalimat/paragraf pendek.
    *   **8192 tokens**: Diperlukan untuk *full document retrieval* atau legal/medical docs (Contoh: `nomic-embed-text-v1.5`, `jina-embeddings-v3`).
2.  **Dimensi Vektor**:
    *   Semakin besar dimensi (misal: 1024 vs 384), semakin akurat nuansa semantiknya, TAPI memperbesar ukuran indeks Vector DB dan memperlambat pencarian (latency).
    *   **Rekomendasi**: Dimensi 768 (sekelas `bge-base-en-v1.5`) adalah keseimbangan terbaik untuk mayoritas aplikasi enterprise.

### 3.3 Model Embedding Terbaru dari Ollama (Q1 2026)

#### A. EmbeddingGemma (Google)
Model embedding kompak 300M parameter dari Google, dibangun dari Gemma 3 dengan inisialisasi T5Gemma.

| Spesifikasi | Detail |
| :--- | :--- |
| **Parameter** | 300M |
| **Ukuran File** | 622 MB |
| **Context Window** | 2K tokens |
| **Bahasa** | 100+ bahasa |
| **Training Data** | ~320 billion tokens |

*   **Kelebihan**:
    *   Ukuran sangat kecil, cocok untuk deployment on-device (mobile, laptop, desktop).
    *   State-of-the-art untuk ukuran kelasnya.
    *   Sangat baik untuk search, retrieval, classification, clustering, dan semantic similarity.
*   **Use Case**: Aplikasi edge computing, mobile apps, atau skenario dengan resource terbatas.

#### B. Qwen3-Embedding (Alibaba)
Seri model embedding komprehensif dari Qwen3, tersedia dalam berbagai ukuran untuk fleksibilitas deployment.

| Varian | Ukuran File | Context Window | Embedding Dimension |
| :--- | :--- | :--- | :--- |
| **qwen3-embedding:0.6b** | 639 MB | 32K tokens | Up to 4096 |
| **qwen3-embedding:4b** | 2.5 GB | 40K tokens | Up to 4096 |
| **qwen3-embedding:8b** | 4.7 GB | 40K tokens | Up to 4096 |

*   **Kelebihan**:
    *   **#1 di MTEB Multilingual Leaderboard** (Skor 70.58, per Juni 2025) untuk varian 8B.
    *   Context window sangat panjang (32K-40K), ideal untuk full document retrieval.
    *   Dimensi embedding fleksibel (32 hingga 4096), bisa disesuaikan dengan kebutuhan.
    *   Mendukung 100+ bahasa termasuk bahasa pemrograman.
    *   Kemampuan multilingual, cross-lingual, dan code retrieval yang kuat.
*   **Use Case**: Text retrieval, code retrieval, text classification, text clustering, bitext mining.

### 3.4 Rekomendasi Model Embedding (Q1 2026)

| Kategori | Model Rekomendasi | Catatan |
| :--- | :--- | :--- |
| **Best MTEB Score** | `qwen3-embedding:8b` | #1 Multilingual Leaderboard (70.58) |
| **Best Long Context** | `qwen3-embedding:4b` / `qwen3-embedding:8b` | 40K context window |
| **Best Compact (<1GB)** | `embeddinggemma` atau `qwen3-embedding:0.6b` | Ideal untuk on-device/edge |
| **Best Speed/Performance** | `nomic-embed-text-v1.5` | Matryoshka supported |
| **Best Indonesian Support** | `intfloat/multilingual-e5-large` atau `qwen3-embedding` | Multilingual 100+ bahasa |
| **Best Overall Balance** | `bge-m3` | Multilingual, 8192 context |

---

## 4. Analisis Skenario Penggunaan

Strategi deployment harus disesuaikan dengan pola penggunaan utama: apakah untuk respons instan ke satu pengguna, atau throughput tinggi untuk banyak pengguna.

### 4.1 Skenario A: Single User (Low Latency Focus)
*   **Contoh Kasus**: Personal AI Assistant, Coding Co-pilot, Debugging Tool.
*   **Metrik Kunci**: **Time To First Token (TTFT)**. Pengguna tidak boleh menunggu > 1-2 detik untuk mulai melihat respons.
*   **Strategi Hardware**:
    *   Kecepatan memori (Memory Bandwidth) adalah raja.
    *   Offload GPU 100% wajib hukumnya. Jangan menggunakan split CPU/GPU jika latency adalah prioritas.
*   **Strategi Model**:
    *   Gunakan model terbesar yang muat sepenuhnya di VRAM dengan buffer sisa ~10-20% untuk KV Cache.

### 4.2 Skenario B: Multi User (Throughput Focus)
*   **Contoh Kasus**: Internal API Server, Customer Service Chatbot, Batch Document Processing.
*   **Metrik Kunci**: **Tokens Per Second (TPS) Total System**. TTFT individual boleh lebih lambat (2-5 detik masih acceptable).
*   **Strategi Hardware**:
    *   Kapasitas memori (Total VRAM) lebih penting daripada bandwidth murni.
    *   Memungkinkan concurrent requests yang besar.
*   **Strategi Model**:
    *   **Continuous Batching**: Wajib menggunakan backend seperti **vLLM** atau **SGLang**.
    *   **Trade-off Ukuran**: Turunkan ukuran model (misal dari 70B ke 32B atau tingkatkan kuantisasi ke Q3_K_M) untuk menyisakan ruang VRAM masif bagi **Batch Size** dan **KV Cache**.
    *   Batch size besar meningkatkan throughput total secara eksponensial dibandingkan sequential processing.

---

## 5. Panduan Kalkulasi Teknis

Gunakan rumus berikut untuk merencanakan kapasitas server (Capacity Planning).

### 5.1 Estimasi VRAM Model (Static Memory)
Estimasi paling dasar untuk memuat bobot model ke memori.

```text
VRAM (GB) ≈ Parameter_Count (B) * Size_Per_Param (Bytes) + Overhead
```

*   **Size Per Param**:
    *   FP16: 2 Bytes
    *   Q8_0: ~1.1 Bytes
    *   Q4_K_M: ~0.65 - 0.70 Bytes (tergantung metadata)
    *   Q2_K: ~0.4 Bytes

**Contoh (Llama-3 70B @ Q4_K_M):**
> 70 * 0.7 + 2 GB (Overhead CUDA/Context Buffer) ≈ **51 GB**

### 5.2 Estimasi KV Cache (Dynamic Memory)
Memori yang dibutuhkan untuk menyimpan konteks percakapan. Ini sering dilupakan dan menjadi penyebab OOM (Out of Memory).

```text
KV_Cache (Bytes) = 2 * Layers * Hidden_Dim * Context_Len * Batch_Size * Precision_Bytes
```

*   *Note: Faktor 2 untuk Key dan Value matrix.*
*   *Precision_Bytes: 2 untuk FP16 cache.*

**Rule of Thumb Cepat:**
> Untuk model 70B (GQA - Grouped Query Attention), KV Cache memakan sekitar **~1 GB per 16k context** (single user) di FP16.

### 5.3 Kalkulasi Bandwidth & Throughput
Kecepatan generasi teks dibatasi oleh seberapa cepat memori bisa "menyuapi" data ke compute unit.

```text
Max Token/s (Single User) = Memory_Bandwidth (GB/s) / Model_Size (GB)
```

**Implikasi:**
*   Model **10 GB** dijalankan di GPU **500 GB/s** bandwidth = Max **50 t/s**.
*   Model **50 GB** dijalankan di GPU **500 GB/s** bandwidth = Max **10 t/s**.
*   *Semakin besar model, semakin lambat generasinya, kecuali bandwidth dinaikkan.*

---

## 6. Studi Kasus Hardware: Ryzen AI Max 395 (Strix Halo)

Bagian ini menganalisis potensi implementasi pada *high-end mobile workstation* dengan arsitektur memori terpadu.

### 6.1 Spesifikasi Sistem
*   **Total RAM**: 128 GB LPDDR5X.
*   **Arsitektur**: Unified Memory (CPU & NPU/GPU berbagi pool memori yang sama).
*   **GPU VRAM Allocation**: Biasanya dinamis, namun untuk AI workload bisa dipaksa hingga **~96 GB** (menyisakan 32GB untuk OS & CPU).
*   **Estimasi Bandwidth**: 250 - 270 GB/s (sangat tinggi untuk mobile, namun lebih rendah dari Discrete GPU High-End seperti RTX 4090 yang mencapai 1000 GB/s).

### 6.2 Analisis Kelayakan Model (Feasibility)

#### A. Llama-3 (70B)
Model kelas "Medium-Large" yang menjadi standar industri saat ini.
*   **Format**: GGUF **Q4_K_M**
*   **Ukuran File**: ~43 GB
*   **Sisa VRAM**: 96 GB - 43 GB = **53 GB Free VRAM**
*   **Kesimpulan**: **SANGAT LAYAK**.
    *   Space sisa 53 GB sangat masif. Anda bisa menjalankan full context (128k) tanpa masalah.
    *   Bisa digunakan untuk **Multi-User** dengan *batch size* besar.

#### B. DeepSeek-R1 (Distilled Versions)
Mengingat model asli DeepSeek-R1 671B terlalu besar, fokus kita adalah varian Distill.
*   **Target**: DeepSeek-R1-Distill-Llama-70B.
*   **Format**: GGUF **Q5_K_M** (Agar lebih akurat untuk math/coding).
*   **Ukuran File**: ~48 GB.
*   **Sisa VRAM**: ~48 GB.
*   **Kesimpulan**: **OPTIMAL**.
    *   Bisa berjalan dengan presisi lebih tinggi (Q5/Q6) dibandingkan setup GPU standar 24GB.

#### C. Mixtral 8x22B (MoE)
Model Mixture of Experts besar.
*   **Ukuran (Q4)**: ~140 GB (Melebihi kapasitas).
*   **Ukuran (Q3_K_M)**: ~80-90 GB.
*   **Sisa VRAM**: ~6-16 GB.
*   **Kesimpulan**: **BERESIKO**.
    *   Hampir memenuhi VRAM penuh. Sisa ruang untuk KV Cache sangat tipis (hanya cukup untuk context pendek < 4k). Tidak disarankan kecuali menggunakan quantisasi Q2 yang merusak kualitas.

### 6.3 Analisis Skalabilitas Enterprise (5-50 User)

Skala 5-50 user memperkenalkan tantangan **"The Queueing Wall"**. Pada rentang ini, bottleneck berpindah dari kapasitas VRAM (Capacity Bound) ke stabilitas latensi (Latency Bound) dan antrian request.

#### A. Profiling User & Alokasi VRAM (Capacity Planning)
Dengan **Llama-3 70B Q4_K_M** (~43GB) pada Ryzen AI Max (96GB Allocation), kita memiliki sisa **~53GB** untuk operasional. Berikut adalah matriks alokasi untuk beban campuran:

| Grup User | Use Case | Avg. Context (In/Out) | Est. KV Cache/User | Max Concurrent (Memory)* |
| :--- | :--- | :--- | :--- | :--- |
| **Casual** | Chatbot HR, Email Drafting | 1k / 250 tokens | ~60 MB | >500 Slots |
| **Heavy** | Coding Assistant, Doc Summaries | 8k / 1k tokens | ~500 MB | ~100 Slots |
| **Power** | Legal/Finance Analysis, RAG | 32k / 4k tokens | ~2.5 GB | ~20 Slots |

*> Asumsi: Menggunakan GQA (Grouped Query Attention) dan FP16 KV Cache. Slot tersedia sebelum OOM (Out of Memory).*

#### B. Rumus Kalkulasi Latency & Antrian
Kapasitas memori bukan masalah utama di sini, melainkan **Time-to-First-Token (TTFT)** dan **Total Generation Time** saat antrian menumpuk.

Gunakan rumus estimasi berikut untuk SLA:

```text
Total_Latency = Queue_Wait_Time + (Generation_Time_Per_Token * Output_Tokens)
```

Dimana:
*   **Queue_Wait_Time**: Waktu tunggu dalam batching queue (meningkat eksponensial saat `Arrival_Rate > Service_Rate`).
*   **Service Rate (Token/s)**: Dibatasi oleh Memory Bandwidth.
    *   *Single User Speed* ≈ Bandwidth (270 GB/s) / Model Size (43 GB) ≈ **6.3 tokens/s**.
    *   *Load Degredation*: Pada 10 concurrent users, speed per user drop ke **~1-2 tokens/s** jika tanpa continuous batching yang efisien.

#### C. Skenario Beban Campuran (50 Users Total)
Simulasi beban puncak jam kerja:
*   30 Casual Users (Idle/Chat ringan)
*   15 Heavy Users (Active Coding/RAG)
*   5 Power Users (Deep Analysis)

**Impact Analysis:**
*   Total VRAM Used: `(30*0.06) + (15*0.5) + (5*2.5)` ≈ **21.8 GB KV Cache**.
*   **Total Memory Status**: 43 GB (Model) + 21.8 GB (Cache) = **64.8 GB**.
*   **Safety Margin**: 96 GB - 64.8 GB = **31.2 GB** (Aman).
*   **Performance Warning**: Meskipun VRAM aman, serving 20+ active requests bersamaan akan membuat *Token Generation Speed* turun drastis karena bandwidth terbagi. Output akan terasa "lambat" bagi user (teks muncul satu per satu dengan jeda).

### 6.4 Tantangan Implementasi & Strategi Mitigasi

#### 1. Masalah: Latency Spikes (Request Queueing)
Saat 5+ user melakukan request panjang bersamaan, user ke-6 akan mengalami "hang" sebelum token pertama muncul.
*   **Mitigasi**: Implementasi **Continuous Batching** (wajib via vLLM/SGLang). Ini memungkinkan scheduler menyisipkan request baru di sela-sela request lama yang sedang menunggu compute, meningkatkan throughput sistem meskipun latency per-user sedikit naik.

#### 2. Strategi: Dual Model Deployment (The "Big-Little" Strategy)
Memanfaatkan VRAM 96GB yang masif, Anda tidak harus terpaku pada satu model.
*   **Konfigurasi**: Jalankan **Llama-3 70B (Server A)** DAN **Llama-3 8B (Server B/Port B)** secara paralel di mesin yang sama.
*   **Mekanisme**:
    *   Route *Simple Requests* (chat, greeting, summarization pendek) ke **8B Model** (Sangat cepat, ~30-40 t/s).
    *   Route *Complex Requests* (coding, math, deep reasoning) ke **70B Model** (Lambat tapi cerdas).
*   **Memory Footprint**: 43 GB (70B) + 6 GB (8B) = 49 GB. Masih menyisakan ~47 GB untuk KV Cache! Ini adalah *killer feature* dari Ryzen AI Max 395 dibandingkan GPU 24GB.

#### 3. Rekomendasi Load Balancing
Jangan gunakan Round-Robin sederhana. Gunakan **Least-Connection** atau **Queue-Depth weighted balancing** jika Anda menskalakan ke node tambahan di masa depan. Untuk single node, percayakan pada scheduler vLLM.

---

## 7. Validasi Benchmark Empiris (Studi Kasus Qwen3 30B)

Bagian ini menyajikan data benchmark real-world menggunakan model **Qwen3:30b** (Text) dan **Qwen3-VL:30b** (Vision) untuk memvalidasi teori skalabilitas dan batasan hardware.

### 7.1 Text Benchmark (Chat, Coding, RAG)
Pengujian dilakukan dengan variasi konkurensi user dari 1 hingga 32 user.

*   **Single User Performance**: **~60 t/s** (Sangat Cepat).
*   **The Throughput Saturation**:
    *   **8 Users**: Melambatkan speed per user menjadi ~26 t/s, namun **Total System Throughput** naik drastis ke **~117 t/s**.
    *   **16 - 32 Users**: Total throughput sistem mengalami **saturasi** (mentok) di rentang **114 - 127 t/s**, tidak peduli berapa banyak user ditambahkan.

**Analisis Fenomena:**
1.  **Capacity Limit (Bandwidth Saturation)**: Sistem telah mencapai batas bandwidth memori efektif pada ~120 t/s. Penambahan user di atas angka 8 tidak lagi meningkatkan efisiensi total, melainkan hanya membagi sumber daya yang ada menjadi bagian-bagian yang semakin kecil (latency meningkat drastis).
2.  **The Timeout Wall (>16 Users)**:
    *   Pada titik **16 User**, mulai terdeteksi **Timeouts/Failures** pada task berat seperti Coding dan RAG.
    *   Pada **32 User**, request mengantri terlalu lama (Wait Time > 60s default timeout), menyebabkan **High Failure Rate**. Server pada dasarnya menolak melayani karena antrian penuh.

### 7.2 Vision Benchmark (VQA)
Workload multimodal menunjukkan karakteristik beban yang sedikit berbeda karena adanya proses *image encoding*.

*   **Throughput Datar**: Total throughput sistem stagnan di **~62 t/s** terlepas dari jumlah user.
*   **Latency Naik Linear**:
    *   1 User: ~1 detik
    *   8 Users: ~4.6 detik
    *   12 Users: ~6.7 detik
*   Vision encoder bersifat lebih *compute-intensive*, menyebabkan antrian yang berdampak langsung pada latensi linear tanpa peningkatan throughput sistem.

### 7.3 Rekomendasi Deployment
Berdasarkan data empiris di atas, berikut adalah batasan praktis untuk deployment satu instance model kelas 30B/70B:

*   **Max Concurrency Aman**: **8 - 12 Users**.
    *   Di rentang ini, throughput sistem maksimal namun latensi per user masih bisa ditoleransi.
*   **Zona Bahaya**: **>15 Users**.
    *   Resiko timeout sangat tinggi.
*   **Solusi Skaling**:
    *   Jika target user concurrent > 15, **WAJIB** menerapkan mekanisme **Load Balancing** (membagi traffic ke beberapa instance model/server) atau menggunakan multiple GPU replicas. Jangan memaksakan satu instance melayani >15 user secara paralel.

---

## 8. Penutup & Rekomendasi Cepat

Memilih model adalah tentang menyeimbangkan ambisi kecerdasan dengan realitas fisik hardware.

### Cheat Sheet Rekomendasi
| Hardware Profile | Model Rekomendasi | Use Case Utama |
| :--- | :--- | :--- |
| **8-16 GB VRAM** | Llama-3 8B, Gemma-2 9B (Q8/FP16) | Coding Assistant Ringan, Personal Chat |
| **24 GB VRAM** | Yi-34B (Q4), Llama-3 70B (IQ2_XXS - *Sangat Terbatas*) | Advanced Coding, Small RAG |
| **Ryzen AI Max (96GB VRAM)** | **Llama-3 70B (Q4/Q5)**, **DeepSeek-70B** | **Production Grade Server**, Heavy RAG, Multi-User |
| **Multi-GPU (2x24GB)** | Llama-3 70B (Q4) dengan Tensor Parallel | High Speed 70B Inference |

**Saran Terakhir:**
Untuk setup **Ryzen AI Max 395**, jangan ragu untuk menggunakan model **70B parameter** dengan kuantisasi **Q4_K_M**. Ini memberikan lompatan kecerdasan yang jauh lebih berharga daripada menjalankan model kecil (8B) dengan kecepatan kilat namun logika terbatas.
