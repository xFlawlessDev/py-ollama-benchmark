# Dokumentasi Skrip Ollama Benchmark

## 1. Ikhtisar
Skrip ini (`benchmark-ollama.py`) dirancang untuk melakukan benchmark kinerja berbagai Large Language Models (LLM) yang berjalan secara lokal melalui Ollama. Skrip ini menguji beberapa model melalui berbagai skenario yang ditentukan untuk mengukur kecepatan generasi (Tokens Per Second/TPS) dan konsistensi.

## 2. Prasyarat
Sebelum menjalankan skrip, pastikan Anda memiliki hal-hal berikut:

-   **Ollama**: Terinstal dan berjalan secara lokal (port default: `11434`).
-   **Pustaka Python**:
    *   `requests` (Instal via `pip install requests`)
-   **Model Ollama**: Model-model berikut dikonfigurasi secara default dan harus di-pull di Ollama sebelum menjalankan skrip:
    *   `gpt-oss:20b`
    *   `qwen3-vl:30b`
    *   `gemma3:27b`
    *   `qwen3:30b`
    *   `deepseek-r1:32b`

    Anda dapat mengunduhnya menggunakan perintah `ollama pull <nama_model>`.

## 3. Konfigurasi
Skrip ini dapat dikonfigurasi melalui konstanta di bagian atas file:

### Model
Daftar `MODELS_TO_TEST` menentukan model mana yang akan di-benchmark.
```python
MODELS_TO_TEST = [
    "gpt-oss:20b",
    "qwen3-vl:30b",
    "gemma3:27b",
    "qwen3:30b",
    "deepseek-r1:32b",
]
```
Ubah daftar ini untuk menambah atau menghapus model yang ingin Anda uji.

### URL API
`OLLAMA_API_URL` mendefinisikan endpoint untuk instance Ollama.
```python
OLLAMA_API_URL = "http://localhost:11434/api/generate"
```

## 4. Skenario Pengujian
Skrip mengeksekusi 4 skenario berbeda untuk setiap model guna mengevaluasi kinerja di berbagai domain:

1.  **Creative Writing** (Penulisan Kreatif): Prompt cerita fiksi ilmiah mendetail tentang peradaban di bola Dyson. Menguji generasi bentuk panjang yang kreatif.
2.  **Coding Task** (Tugas Pemrograman): Permintaan untuk menulis skrip scraper Python BeautifulSoup. Menguji kemampuan pembuatan kode.
3.  **Logic Puzzle** (Teka-teki Logika): Teka-teki logika yang melibatkan teman dan warna baju. Menguji kemampuan penalaran.
4.  **JSON Data**: Meminta pembuatan dataset pengguna dummy dalam format JSON mentah. Menguji kepatuhan terhadap instruksi dan pembuatan output terstruktur.

## 5. Cara Menjalankan
Pastikan server Ollama Anda berjalan. Skrip ini mendukung argumen baris perintah (CLI) untuk fleksibilitas penggunaan. Berikut adalah beberapa cara menjalankannya:

### 1. Menjalankan dengan pengaturan default
Menggunakan daftar model dan URL yang dikonfigurasi di dalam file skrip (`MODELS_TO_TEST` dan `OLLAMA_API_URL`).
```bash
python benchmark-ollama.py
```

### 2. Menjalankan dengan model tertentu
Gunakan flag `--models` diikuti dengan nama-nama model yang ingin diuji (dipisahkan dengan spasi).
```bash
python benchmark-ollama.py --models llama2:7b mistral:7b
```

### 3. Menjalankan dengan URL API custom
Gunakan argumen `--url` untuk menargetkan server Ollama yang berjalan di alamat IP atau port berbeda (misalnya remote server).
```bash
python benchmark-ollama.py --url http://192.168.1.100:11434/api/generate
```

### 4. Kombinasi keduanya
Anda dapat menggabungkan kedua argumen untuk kontrol penuh.
```bash
python benchmark-ollama.py --models qwen:14b --url http://remote-pluto:11434/api/generate
```

## 6. Key Parameter & Cara Menilai
Bagian ini menjelaskan metrik evaluasi utama dan cara menginterpretasikan hasil benchmark untuk menilai performa model.

*   **`eval_count` (Tokens)**: Jumlah total token yang dihasilkan oleh model dalam responsnya. Ini menunjukkan panjang output.
*   **`eval_duration`**: Durasi waktu yang dibutuhkan model untuk menghasilkan respons tersebut.
*   **`TPS` (Tokens Per Second)**: Kecepatan kunci (Key Metric). Ini adalah jumlah token yang dapat dihasilkan model dalam satu detik.
    *   **Aturan Dasar**: Semakin tinggi nilai TPS, semakin responsif dan cepat model tersebut.

### Faktor yang Mempengaruhi Kecepatan (TPS)
Performa tidak hanya bergantung pada model itu sendiri, tetapi juga konfigurasi sistem:
1.  **Ukuran Model**: Model 7b (7 miliar parameter) akan jauh lebih cepat (TPS tinggi) dibandingkan model 70b, karena beban komputasinya lebih ringan.
2.  **Tingkat Kuantisasi**: Model yang dikuantisasi (misalnya 4-bit atau `q4_0`) lebih cepat daripada model presisi penuh (fp16), meskipun mungkin sedikit mengurangi akurasi.
3.  **RAM GPU vs CPU**: Kecepatan tertinggi dicapai jika seluruh model dimuat ke dalam VRAM GPU. Jika VRAM tidak cukup dan model berjalan sebagian/sepenuhnya di RAM sistem (CPU), TPS akan turun drastis.

### Menilai Kualitas vs Kecepatan
Benchmark ini memberikan data kecepatan kuantitatif, namun Anda harus menilainya bersamaan dengan kualitas output:
*   **Skenario Logic/Coding**: Cek apakah jawabannya benar dan kodenya valid. Kecepatan tinggi tidak berguna jika jawabannya salah (halusinasi).
*   **Trade-off**: Untuk *real-time chat*, Anda biasanya menginginkan TPS > 15-20. Untuk tugas analisis batch di latar belakang, TPS rendah dengan model yang lebih pintar (lebih besar) mungkin lebih disukai.

## 7. Output

### Output Konsol
Skrip memberikan tiga tingkat output selama eksekusi:
1.  **Progres Real-time**: Menampilkan model dan skenario yang sedang diuji saat ini, beserta hasil T/s (Token per detik) langsung.
2.  **Tabel Rinci**: Tabel komprehensif yang menampilkan setiap proses untuk setiap model, termasuk nama skenario, kecepatan (T/s), dan total token yang dihasilkan.
3.  **Tabel Ringkasan**: Peringkat tingkat tinggi model yang diurutkan berdasarkan kecepatan rata-rata, menunjukkan T/s Rata-rata, Minimum, dan Maksimum.

### Output CSV
File CSV dibuat secara otomatis setelah selesai untuk analisis lebih lanjut.
*   **Format Nama File**: `benchmark_results_YYYYMMDD_HHMMSS.csv`
*   **Kolom**: `model`, `scenario`, `tps` (token per detik), `tokens` (total jumlah token).

## 8. Struktur Kode
Fungsi utama dalam skrip meliputi:

*   `run_inference(model, prompt, scenario_name)`: Menangani permintaan API ke Ollama, mengukur waktu eksekusi, dan mengembalikan respons.
*   `calculate_tps(data)`: Menghitung Token Per Detik berdasarkan `eval_count` dan `eval_duration` dari respons Ollama.
*   `print_detailed_table(all_runs)`: Memformat dan menampilkan hasil baris demi baris di terminal.
*   `print_summary_table(model_stats)`: Mengagregasi statistik untuk menampilkan performa rata-rata per model.
*   `save_to_csv(all_runs)`: Mengekspor data yang dikumpulkan ke file CSV.