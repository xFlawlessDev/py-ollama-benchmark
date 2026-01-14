import requests
import time
import statistics
import csv
import argparse
from datetime import datetime

# --- KONFIGURASI ---
MODELS_TO_TEST = [
    "gpt-oss:20b",
    "qwen3-vl:30b",
    "gemma3:27b",
    "qwen3:30b",
    "deepseek-r1:32b",
]

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# --- SKENARIO TEST ---
TEST_SCENARIOS = {
    "Creative Writing": """
        Write a detailed sci-fi story about a civilization living on a dyson sphere. 
        Describe the environment, the technology, and a conflict over resources. 
        Write at least 400 words.
    """,
    "Coding Task": """
        Write a complete Python script to scrape a website using BeautifulSoup. 
        Include error handling (try-except), headers simulation, and comments.
    """,
    "Logic Puzzle": """
        Three friends (Alice, Bob, Charlie) are wearing red, blue, and green shirts. 
        Alice is not wearing red. Bob is not wearing blue. The person in green is 
        older than Alice. Who is wearing which color? Explain step-by-step.
    """,
    "JSON Data": """
        Generate a dummy user dataset for 10 people. 
        Return ONLY a raw JSON array. Each object must have: 
        id, full_name, email, job_title, and bio.
    """
}

def run_inference(model, prompt, scenario_name="Unknown", api_url=OLLAMA_API_URL):
    """Mengirim request ke Ollama."""
    print(f"   > Testing: {scenario_name}...", end="\r")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": -1}
    }

    try:
        start_time = time.time()
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        end_time = time.time()
        return response.json(), (end_time - start_time)
    except Exception as e:
        print(f"\n   [ERROR] {scenario_name}: {e}")
        return None, 0

def calculate_tps(data):
    if not data: return 0, 0
    eval_count = data.get('eval_count', 0)
    eval_duration_ns = data.get('eval_duration', 0)
    if eval_duration_ns > 0:
        return eval_count / (eval_duration_ns / 1e9), eval_count
    return 0, 0

def print_detailed_table(all_runs):
    """Menampilkan tabel breakdown per skenario."""
    print("\n" + "="*85)
    print(f"{'MODEL':<20} | {'SCENARIO':<20} | {'SPEED (T/s)':<12} | {'TOKENS':<8}")
    print("="*85)
    
    for run in all_runs:
        print(f"{run['model']:<20} | {run['scenario']:<20} | {run['tps']:<12.2f} | {run['tokens']:<8}")
    print("="*85)

def print_summary_table(model_stats):
    """Menampilkan tabel rata-rata akhir."""
    print("\n" + "="*65)
    print(f"{'MODEL SUMMARY':<20} | {'AVG T/s':<10} | {'MIN T/s':<10} | {'MAX T/s':<10}")
    print("="*65)
    
    sorted_stats = sorted(model_stats, key=lambda x: x['avg'], reverse=True)
    for stat in sorted_stats:
        print(f"{stat['model']:<20} | {stat['avg']:<10.2f} | {stat['min']:<10.2f} | {stat['max']:<10.2f}")
    print("="*65)

def save_to_csv(all_runs):
    filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["model", "scenario", "tps", "tokens"])
        writer.writeheader()
        writer.writerows(all_runs)
    print(f"\n[INFO] Hasil lengkap disimpan ke file: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Benchmark Ollama Models")
    parser.add_argument("--models", nargs='+', default=MODELS_TO_TEST, help="List of models to test")
    parser.add_argument("--url", default=OLLAMA_API_URL, help="Ollama API URL")
    
    args = parser.parse_args()
    
    models_to_test = args.models
    api_url = args.url

    print(f"--- BENCHMARK STARTED ({len(models_to_test)} Models) ---")
    print(f"API URL: {api_url}")
    print(f"Models: {models_to_test}\n")
    
    all_runs_data = [] # Untuk tabel detail
    model_stats = []   # Untuk tabel summary

    for model in models_to_test:
        print(f"[{model.upper()}] Processing...")
        
        # Warmup
        run_inference(model, "Hi", "Warmup", api_url=api_url)
        
        current_model_speeds = []
        
        for scenario, prompt in TEST_SCENARIOS.items():
            data, _ = run_inference(model, prompt, scenario, api_url=api_url)
            
            if data:
                tps, tokens = calculate_tps(data)
                if tps > 0:
                    # Simpan data per run
                    run_data = {
                        "model": model,
                        "scenario": scenario,
                        "tps": tps,
                        "tokens": tokens
                    }
                    all_runs_data.append(run_data)
                    current_model_speeds.append(tps)
                    print(f"   > {scenario:<20} : {tps:.2f} t/s")

        # Hitung statistik rata-rata model ini
        if current_model_speeds:
            model_stats.append({
                "model": model,
                "avg": statistics.mean(current_model_speeds),
                "min": min(current_model_speeds),
                "max": max(current_model_speeds)
            })
        print("") # Spasi antar model

    # --- TAMPILKAN HASIL ---
    print_detailed_table(all_runs_data)
    print_summary_table(model_stats)
    
    # Opsional: Simpan ke CSV
    save_to_csv(all_runs_data)

if __name__ == "__main__":
    main()