# Panduan Komprehensif Pemilihan Model LLM dan Embedding untuk Infrastruktur Lokal

**Versi Dokumen:** 1.1
**Tanggal Update:** 14 Januari 2026
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
*   **KV Cache Quantization**: Pada konteks sangat panjang (long-context RAG), pertimbangkan menggunakan **FP8 KV Cache** (opsi tersedia di vLLM/llama.cpp) untuk menghemat VRAM hingga 2x tanpa degradasi berarti.

---

## 3. Strategi Pemilihan Model Embedding

Model embedding mengubah teks menjadi vektor numerik untuk pencarian semantik (RAG). Pemilihannya sering diabaikan, padahal krusial untuk akurasi retrieval.

### 3.1 Kriteria Seleksi (MTEB Leaderboard)
Gunakan acuan **MTEB (Massive Text Embedding Benchmark)**. Jangan terpaku pada model OpenAI (text-embedding-3). Model open-source seringkali lebih performant dan efisien.

### 3.2 Pertimbangan Teknis
1.  **Sequence Length**:
    *   **512 tokens**: Cukup untuk pencarian kalimat/paragraf pendek.
    *   **8192 tokens**: Diperlukan untuk *full document retrieval* atau legal/medical docs (Contoh: `nomic-embed-text-v1.5`, `jina-embeddings-v3`).
    *   **32K - 40K tokens**: Model embedding terbaru seperti `qwen3-embedding` mendukung konteks sangat panjang, ideal untuk whole-document indexing.
2.  **Dimensi Vektor**:
    *   Semakin besar dimensi (misal: 1024 vs 384), semakin akurat nuansa semantiknya, TAPI memperbesar ukuran indeks Vector DB dan memperlambat pencarian (latency).
    *   **Rekomendasi Klasik**: Dimensi 768 (sekelas `bge-base-en-v1.5`) adalah keseimbangan terbaik untuk mayoritas aplikasi enterprise.
    *   **Rekomendasi Modern**: Model seperti `qwen3-embedding` mendukung dimensi fleksibel (32 hingga 4096), memungkinkan Anda menyesuaikan trade-off akurasi vs efisiensi sesuai kebutuhan spesifik.

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

---

## 9. Referensi & Sumber Pendukung

Bagian ini menyediakan referensi artikel dan dokumentasi teknis yang mendukung rekomendasi dalam panduan ini.

### 9.1 Kuantisasi Model (GGUF, Q4_K_M)

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **Unsloth Dynamic GGUFs Benchmark** | Analisis performa kuantisasi dinamis pada Aider Polyglot Benchmark, menunjukkan bahwa 4-bit quantization mempertahankan ~98% akurasi model asli. | [unsloth.ai](https://unsloth.ai/docs/basics/unsloth-dynamic-2.0-ggufs/unsloth-dynamic-ggufs-on-aider-polyglot) |
| **Green LLM Techniques (arXiv)** | Studi akademis tentang efek kuantisasi terhadap konsumsi energi dan trade-off akurasi pada edge inference. | [arxiv.org/html/2601.02512v1](https://arxiv.org/html/2601.02512v1) |
| **RTX 4090 vs RX 7900 XTX Local LLM** | Perbandingan langsung performa Q4_K_M pada hardware berbeda, mengkonfirmasi "sweet spot" kuantisasi Q4-Q5. | [alibaba.com](https://www.alibaba.com/product-insights/nvidia-rtx-4090-vs-amd-rx-7900-xtx-for-local-llm-inference-which-gpu-delivers-smoother-chatbot-performance.html) |

> **Kutipan Kunci**: *"Start with Q4_K_M for 7B models and Q5_K_S for 13B. Avoid Q2_K or Q3_K unless VRAM is critically constrained—they degrade coherence more than they improve speed."* — Alibaba Product Insights

### 9.2 Model Embedding & MTEB Benchmark

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **Qwen3-Embedding MTEB #1** | Dokumentasi resmi SiliconFlow mengkonfirmasi Qwen3-Embedding-8B sebagai #1 di MTEB Multilingual Leaderboard (skor 70.58, Juni 2025). | [siliconflow.com/models/llm](https://www.siliconflow.com/models/llm) |
| **C2LLM MTEB-Code Benchmark** | Technical report menunjukkan perbandingan model embedding pada code retrieval tasks. | [arxiv.org/pdf/2512.21332](https://arxiv.org/pdf/2512.21332) |
| **Best Embedding Models 2026** | Review komprehensif 10 model embedding terbaik termasuk Qwen3, BGE-M3, dan Nomic Embed. | [openxcell.com/blog/best-embedding-models](https://www.openxcell.com/blog/best-embedding-models/) |
| **MTEB Official Repository** | Repository resmi benchmark MTEB dengan hasil evaluasi terbaru. | [github.com/embeddings-benchmark/mteb](https://github.com/embeddings-benchmark/mteb/releases) |
| **EmbeddingRWKV MTEB Comparison** | Tabel perbandingan detail model embedding pada MTEB English v2. | [arxiv.org/html/2601.07861v1](https://arxiv.org/html/2601.07861v1) |

> **Kutipan Kunci**: *"The 4B and 8B Qwen3 models outperform others and fit well with RAG and enterprise pipelines... multilingual capabilities supporting over 100 languages."* — OpenXCell Blog

### 9.3 KV Cache & Manajemen Memori

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **DigitalOcean AMD Technical Deep Dive** | Panduan praktis penggunaan FP8 KV Cache untuk ~50% VRAM reduction dengan vLLM. | [digitalocean.com/blog](https://www.digitalocean.com/blog/technical-deep-dive-character-ai-amd) |
| **GPU-Accelerated INT8 KV Cache (arXiv)** | Studi implementasi INT8 quantization untuk KV cache dengan 4x memory savings. | [arxiv.org/html/2601.04719v1](https://arxiv.org/html/2601.04719v1) |
| **PyTorch/torchao Serving Guide** | Dokumentasi resmi PyTorch tentang quantization dan memory optimization. | [docs.pytorch.org/ao/stable/serving](https://docs.pytorch.org/ao/stable/serving.html) |

> **Kutipan Kunci**: *"Using FP8 for KV cache explicitly has some benefits, including lower VRAM usage (~50% reduction), better throughput due to reduced memory bandwidth pressure, and more capacity for handling a higher number of concurrent users."* — DigitalOcean Technical Blog

### 9.4 vLLM & Continuous Batching

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **Serving LLMs with vLLM: A Practical Guide** | Panduan komprehensif vLLM termasuk PagedAttention, continuous batching, dan quantization support. | [nebius.com/blog](https://nebius.com/blog/posts/serving-llms-with-vllm-practical-guide) |
| **Choosing the Right LLM Inference Framework** | Perbandingan 6 framework inferensi utama dengan benchmark throughput dan latency. | [ranjankumar.in](https://ranjankumar.in/choosing-the-right-llm-inference-framework-a-practical-guide/) |
| **LLM Serving with vLLM (Medium)** | Studi kasus implementasi vLLM dengan hasil 5x throughput improvement. | [medium.com](https://ammarab.medium.com/llm-serving-with-vllm-23e3b1e0c617) |
| **PagedAttention Paper (SOSP 2023)** | Paper akademis asli tentang algoritma PagedAttention. | arXiv:2309.06180 |
| **Qwen3-30B Consumer-Grade Benchmark** | Benchmark empiris PagedAttention dan continuous batching pada hardware konsumer. | [arxiv.org/html/2512.23029v1](https://arxiv.org/html/2512.23029v1) |

> **Kutipan Kunci**: *"In published benchmarks and production deployments, vLLM typically delivers throughput in the 120-160 requests per second range with 50-80ms time to first token. What makes vLLM special isn't raw speed—but how well it handles concurrency."* — Choosing the Right LLM Inference Framework

### 9.5 AMD Ryzen AI Max 395 (Strix Halo)

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **TechPowerUp Strix Halo Coverage** | Kompilasi berita tentang Strix Halo termasuk spesifikasi 128GB unified memory dan 96GB VRAM allocation. | [techpowerup.com](https://www.techpowerup.com/news-tags/Strix%20Halo) |
| **Running DeepSeek-OCR on Strix Halo** | Studi kasus real-world menjalankan VLM pada Ryzen AI Max+ 395 dengan 105GB+ VRAM allocation. | [linkedin.com](https://www.linkedin.com/pulse/running-deepseek-ocr-locally-amd-strix-halo-journey-local-wong-b83ve) |
| **Best Hardware for Running Local AI** | Review perbandingan Ryzen AI Max+ 395 vs NVIDIA DGX Spark untuk local LLM workloads. | [tweaktown.com](https://www.tweaktown.com/articles/11301/the-best-hardware-for-running-local-ai/index.html) |
| **Corsair AI Workstation 300** | Spesifikasi sistem berbasis Strix Halo untuk AI workflows dengan dukungan LM Studio. | [techpowerup.com](https://www.techpowerup.com/news-tags/Strix%20Halo) |

> **Kutipan Kunci**: *"With up to 128 GB of unified LPDDR5X memory (96 GB can be dynamically allocated as VRAM), it supports large-scale model inference workloads that standard desktop GPUs simply can't handle."* — TechPowerUp

### 9.6 Model LLM (Llama-3, DeepSeek-R1)

| Referensi | Deskripsi | URL |
| :--- | :--- | :--- |
| **DeepSeek R1 Local Deployment Guide** | Panduan lengkap VRAM requirements untuk semua varian DeepSeek-R1 Distill. | [jan.ai](https://jan.ai/post/deepseek-r1-locally) |
| **DeepSeek-R1 Fine-tuning Technical Guide** | Penjelasan teknis arsitektur dan kuantisasi DeepSeek-R1. | [oreateai.com](https://www.oreateai.com/blog/indepth-explanation-of-deepseekr1-inference-model-finetuning-technology/2d17841e19e04313f6211eef1f6aa757) |
| **Local Computer Use Agents Performance** | Benchmark performa berbagai model termasuk DeepSeek-R1, Qwen3, Llama pada berbagai GPU. | [tallyfy.com](https://tallyfy.com/products/pro/integrations/computer-ai-agents/local-computer-use-agents/) |
| **IBM watsonx Foundation Models** | Dokumentasi spesifikasi DeepSeek-R1-Distill-Llama-70B dengan 131K context window. | [ibm.com](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-models-details.html) |

> **Kutipan Kunci**: *"DeepSeek-R1-Distill-Llama-70B is a model fine-tuned based on the open-source model Llama-3.1-70B using data generated by DeepSeek-R1... Context window length: 131,072 tokens."* — IBM watsonx Docs

### 9.7 Referensi Akademis

| Paper | Penulis/Institusi | Tahun |
| :--- | :--- | :--- |
| **Efficient Memory Management for LLM Serving with PagedAttention** | Kwon et al., UC Berkeley | SOSP 2023 |
| **BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity** | Chen et al., BAAI | 2024 |
| **MTEB: Massive Text Embedding Benchmark** | Muennighoff et al. | 2023 |
| **Orca: A Distributed Serving System for Transformer-Based Models** | Yu et al. | OSDI 2022 |
| **MMTEB: Massive Multilingual Text Embedding Benchmark** | Enevoldsen et al. | ICLR 2025 |

---

**Catatan Validasi:**
Semua rekomendasi dalam dokumen ini telah divalidasi dengan referensi industri dan akademis terkini (per Januari 2026). Untuk update terbaru, disarankan untuk memantau MTEB Leaderboard, vLLM GitHub repository, dan dokumentasi resmi vendor hardware.
