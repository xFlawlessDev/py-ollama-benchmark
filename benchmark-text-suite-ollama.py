import requests
import time
import concurrent.futures
import statistics
import csv
import os
import argparse
from datetime import datetime

# --- KONFIGURASI DEFAULT ---
# Ganti dengan model teks murni Anda (misal: qwen2.5:32b, llama3.1:70b, atau enterprise-main)
DEFAULT_MODEL_TEXT = "qwen3:30b"
DEFAULT_MODEL_EMBED = "qwen3-embedding:4b"
DEFAULT_OLLAMA_API = "http://localhost:11434/api"

# Variables that will be updated by args
MODEL_TEXT = DEFAULT_MODEL_TEXT
MODEL_EMBED = DEFAULT_MODEL_EMBED
OLLAMA_API = DEFAULT_OLLAMA_API
OUTPUT_FILE = f"text_benchmark_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

# Level Concurrency yang akan dites
USER_LEVELS = [1, 8, 16, 32] 

# --- PROMPTS ---
PROMPTS = {
    "CHAT_SHORT": "Explain clearly what is a Black Hole in 3 sentences.",
    "CODING_HARD": "Write a Python script to implement A* Search Algorithm with detailed comments explaining the heuristic function.",
    "LONG_SUMMARIZE": "Summarize the following text: " + ("This is a long dummy context about enterprise architecture. " * 200) # Simulasi input panjang
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_metrics(res_json):
    """Ekstrak metrik performa."""
    try:
        eval_count = res_json.get('eval_count', 0)
        eval_dur = res_json.get('eval_duration', 0) # ns
        prompt_eval_count = res_json.get('prompt_eval_count', 0)
        prompt_eval_dur = res_json.get('prompt_eval_duration', 0) # ns
        
        # Kecepatan Generate (Menulis)
        gen_tps = 0
        if eval_dur > 0:
            gen_tps = eval_count / (eval_dur / 1e9)
            
        # Kecepatan Membaca (Prompt Processing)
        prompt_tps = 0
        if prompt_eval_dur > 0:
            prompt_tps = prompt_eval_count / (prompt_eval_dur / 1e9)
            
        return {
            "gen_tps": gen_tps,
            "prompt_tps": prompt_tps,
            "latency": res_json.get('total_duration', 0) / 1e9,
            "tokens_out": eval_count
        }
    except:
        return None

def task_chat(user_id):
    """Skenario 1: Chat Ringan"""
    payload = {"model": MODEL_TEXT, "prompt": PROMPTS["CHAT_SHORT"], "stream": False}
    try:
        res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=60)
        if res.status_code == 200: return get_metrics(res.json())
    except Exception as e: log(f"Err {user_id}: {e}")
    return None

def task_coding(user_id):
    """Skenario 2: Coding (Logika Berat)"""
    payload = {"model": MODEL_TEXT, "prompt": PROMPTS["CODING_HARD"], "stream": False, "options": {"num_predict": 512}}
    try:
        res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=60)
        if res.status_code == 200: return get_metrics(res.json())
    except Exception as e: log(f"Err {user_id}: {e}")
    return None

def task_rag_sim(user_id):
    """Skenario 3: RAG Text Pipeline"""
    # 1. Embed
    start = time.time()
    requests.post(f"{OLLAMA_API}/embeddings", json={"model": MODEL_EMBED, "prompt": "Database query simulation"})
    embed_dur = time.time() - start
    
    # 2. Generate
    payload = {"model": MODEL_TEXT, "prompt": "Based on this context, answer usage policy.", "stream": False}
    try:
        res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=60)
        if res.status_code == 200:
            m = get_metrics(res.json())
            m['embed_latency'] = embed_dur
            return m
    except Exception as e: log(f"Err {user_id}: {e}")
    return None

def run_scenario(name, func, concurrency):
    log(f"--- RUNNING: {name} ({concurrency} Users) ---")
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(func, i) for i in range(concurrency)]
        for f in concurrent.futures.as_completed(futures):
            if f.result(): results.append(f.result())
            
    if not results:
        return {
            "scenario": name,
            "users": concurrency,
            "success": 0,
            "fail": concurrency,
            "avg_tps": 0.0,
            "sys_throughput": 0.0
        }

    # Agregasi
    success_count = len(results)
    fail_count = concurrency - success_count

    avg_gen_tps = statistics.mean([r['gen_tps'] for r in results])
    avg_prompt_tps = statistics.mean([r['prompt_tps'] for r in results])
    avg_lat = statistics.mean([r['latency'] for r in results])
    
    # Kalkulasi Throughput
    model_speeds = [r['gen_tps'] for r in results]
    min_tps = min(model_speeds) if model_speeds else 0
    max_tps = max(model_speeds) if model_speeds else 0

    # Total token yang diproduksi seluruh sistem per detik
    total_tokens = sum([r['tokens_out'] for r in results])
    max_duration = max([r['latency'] for r in results])
    sys_throughput = total_tokens / max_duration

    print(f"   > Success/Fail     : {success_count}/{fail_count}")
    print(f"   > Avg Speed (User) : {avg_gen_tps:.2f} t/s")
    print(f"   > Prompt Reading   : {avg_prompt_tps:.2f} t/s")
    print(f"   > System Throughput: {sys_throughput:.2f} t/s")
    print("-" * 50)
    
    # Save CSV
    write_header = not os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'scenario', 'users', 'successes', 'failures', 'avg_tps', 'min_tps', 'max_tps', 'prompt_tps', 'sys_throughput', 'latency', 'total_tokens'])
        if write_header: writer.writeheader()
        writer.writerow({
            'time': datetime.now().strftime('%H:%M:%S'),
            'scenario': name,
            'users': concurrency,
            'successes': success_count,
            'failures': fail_count,
            'avg_tps': avg_gen_tps,
            "min_tps": min_tps,
            "max_tps": max_tps,
            'prompt_tps': avg_prompt_tps,
            'sys_throughput': sys_throughput,
            'latency': avg_lat,
            "total_tokens": total_tokens
        })

    return {
        "scenario": name,
        "users": concurrency,
        "success": success_count,
        "fail": fail_count,
        "avg_tps": avg_gen_tps,
        "sys_throughput": sys_throughput
    }

def print_summary_table(all_stats, start_time):
    # Print Configuration Block
    print("\n" + "=" * 85)
    print(f"{'BENCHMARK TEXT SUITE - CONFIGURATION':^85}")
    print("=" * 85)
    print(f" Date Running Test: {start_time}")
    print(f" Model Text       : {MODEL_TEXT}")
    print(f" Model Embed      : {MODEL_EMBED}")
    print(f" API Endpoint     : {OLLAMA_API}")
    print(f" Concurrency      : {USER_LEVELS}")
    print("=" * 85)

    print("\n" + "="*85)
    print(f"{'FINAL SUMMARY REPORT':^85}")
    print("="*85)
    print(f"{'Scenario':<25} | {'Users':<6} | {'Pass':<5} | {'Fail':<5} | {'Avg TPS':<10} | {'Sys T/s':<10} | {'Status':<10}")
    print("-" * 85)
    
    for stat in all_stats:
        if not stat: continue
        
        # Color codes
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        RESET = "\033[0m"
        
        fail = stat['fail']
        users = stat['users']
        
        status = f"{GREEN}PASS{RESET}"
        if fail > 0:
            status = f"{YELLOW}WARN{RESET}"
        if fail > (users * 0.2) and users > 1: # >20% failures
            status = f"{RED}FAIL{RESET}"
        if fail == users:
            status = f"{RED}CRITICAL{RESET}"
            
        print(f"{stat['scenario']:<25} | {stat['users']:<6} | {stat['success']:<5} | {stat['fail']:<5} | {stat['avg_tps']:<10.2f} | {stat['sys_throughput']:<10.2f} | {status}")
    print("="*85 + "\n")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Benchmark Text Suite for Ollama")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL_TEXT, help="Text model name (default: %(default)s)")
    parser.add_argument("--embed-model", default=DEFAULT_MODEL_EMBED, help="Embedding model name (default: %(default)s)")
    parser.add_argument("--url", default=DEFAULT_OLLAMA_API, help="Ollama API URL (default: %(default)s)")
    return parser.parse_args()

def main():
    global MODEL_TEXT, MODEL_EMBED, OLLAMA_API
    args = parse_arguments()
    MODEL_TEXT = args.model
    MODEL_EMBED = args.embed_model
    OLLAMA_API = args.url

    # Detailed Header
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("=" * 60)
    print(f"{'BENCHMARK TEXT SUITE - CONFIGURATION':^60}")
    print("=" * 60)
    print(f" Date Running Test: {start_time}")
    print(f" Model Text   : {MODEL_TEXT}")
    print(f" Model Embed  : {MODEL_EMBED}")
    print(f" API Endpoint : {OLLAMA_API}")
    print(f" Concurrency  : {USER_LEVELS}")
    print("=" * 60)
    print("")
    
    # Warmup
    log("Status: Warming up models...")
    task_chat(0)
    
    all_stats = []
    for users in USER_LEVELS:
        all_stats.append(run_scenario("CHAT_LIGHT", task_chat, users))
        time.sleep(2)
        
        all_stats.append(run_scenario("CODING_HEAVY", task_coding, users))
        time.sleep(2)
        
        all_stats.append(run_scenario("RAG_FLOW", task_rag_sim, users))
        time.sleep(2)

    print_summary_table(all_stats, start_time)

if __name__ == "__main__":
    main()