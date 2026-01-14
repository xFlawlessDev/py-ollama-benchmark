import requests
import time
import concurrent.futures
import statistics
import csv
import os
import argparse
from datetime import datetime

# --- KONFIGURASI DEFAULT ---
# Pastikan nama model sesuai dengan yang berhasil tadi
DEFAULT_MODEL_VISION = "qwen3-vl:30b"
DEFAULT_OLLAMA_API = "http://localhost:11434/api"

MODEL_VISION = DEFAULT_MODEL_VISION
OLLAMA_API = DEFAULT_OLLAMA_API
OUTPUT_FILE = f"vision_benchmark_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

# Level Concurrency
# Kita tes beban bertahap dari 1 sampai 12 user
USER_LEVELS = [1, 4, 8, 12]

# --- SAFE IMAGE (JPEG 32x32) ---
# Menggunakan teknik chunking agar string tidak rusak saat copy-paste
img_parts = [
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a",
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy",
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAgACADASIA",
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA",
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3",
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm",
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA",
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx",
    "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK",
    "U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3",
    "uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5/ooo",
    "oAKKKKACiiigAooooA//2Q=="
]
TEST_IMAGE_B64 = "".join(img_parts)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_vision_metrics(res_json):
    """Ekstrak metrik khusus vision."""
    try:
        eval_count = res_json.get('eval_count', 0)
        eval_dur_ns = res_json.get('eval_duration', 0)
        # Prompt eval duration = Waktu memproses gambar (Vision Encoder)
        image_process_dur_ns = res_json.get('prompt_eval_duration', 0)
        total_dur_ns = res_json.get('total_duration', 0)
        
        gen_tps = 0
        if eval_dur_ns > 0:
            gen_tps = eval_count / (eval_dur_ns / 1e9)
            
        return {
            "gen_tps": gen_tps,
            "image_process_time": image_process_dur_ns / 1e9,
            "total_latency": total_dur_ns / 1e9,
            "tokens_out": eval_count
        }
    except:
        return None

def task_vqa_standard(user_id):
    """Skenario: Visual QA"""
    payload = {
        "model": MODEL_VISION,
        "prompt": "Describe this image.",
        "images": [TEST_IMAGE_B64],
        "stream": False,
        "options": {"num_predict": 64}
    }
    try:
        # Timeout diperpanjang ke 300s agar antrian 12 user tidak putus
        res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=300)
        if res.status_code == 200: return get_vision_metrics(res.json())
        else: log(f"Err {user_id}: HTTP {res.status_code}")
    except Exception as e: log(f"Err {user_id}: {e}")
    return None

def run_scenario(name, func, concurrency):
    log(f"--- RUNNING VISION TEST: {name} ({concurrency} Users) ---")
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(func, i) for i in range(concurrency)]
        for f in concurrent.futures.as_completed(futures):
            if f.result(): results.append(f.result())
            
    if not results:
        log("No results captured.")
        return {
            "scenario": name,
            "users": concurrency,
            "success": 0,
            "fail": concurrency,
            "avg_tps": 0.0,
            "avg_img_proc": 0.0,
            "sys_throughput": 0.0
        }

    # Agregasi
    success_count = len(results)
    fail_count = concurrency - success_count

    avg_gen_tps = statistics.mean([r['gen_tps'] for r in results])
    avg_img_time = statistics.mean([r['image_process_time'] for r in results])
    avg_latency = statistics.mean([r['total_latency'] for r in results])
    
    model_speeds = [r['gen_tps'] for r in results]
    min_tps = min(model_speeds) if model_speeds else 0
    max_tps = max(model_speeds) if model_speeds else 0

    total_tokens = sum([r['tokens_out'] for r in results])
    max_duration = max([r['total_latency'] for r in results])
    sys_throughput = total_tokens / max_duration if max_duration > 0 else 0

    print(f"   > Success/Fail         : {success_count}/{fail_count}")
    print(f"   > Avg Gen Speed (User) : {avg_gen_tps:.2f} t/s")
    print(f"   > Avg Image Proc Time  : {avg_img_time:.2f} s")
    print(f"   > Avg Total Latency    : {avg_latency:.2f} s")
    print(f"   > System Throughput    : {sys_throughput:.2f} t/s")
    print("-" * 60)
    
    # Save CSV
    write_header = not os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'scenario', 'users', 'successes', 'failures', 'avg_tps', 'min_tps', 'max_tps', 'img_proc_time', 'latency', 'sys_throughput', 'total_tokens'])
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
            'img_proc_time': avg_img_time,
            'latency': avg_latency,
            'sys_throughput': sys_throughput,
            "total_tokens": total_tokens
        })

    return {
        "scenario": name,
        "users": concurrency,
        "success": success_count,
        "fail": fail_count,
        "avg_tps": avg_gen_tps,
        "avg_img_proc": avg_img_time,
        "sys_throughput": sys_throughput
    }

def print_summary_table(all_stats, start_time):
    # Print Configuration Block
    print("\n" + "=" * 95)
    print(f"{'BENCHMARK VISION SUITE - CONFIGURATION':^95}")
    print("=" * 95)
    print(f" Date Running Test: {start_time}")
    print(f" Model Vision     : {MODEL_VISION}")
    print(f" API Endpoint     : {OLLAMA_API}")
    print(f" Concurrency      : {USER_LEVELS}")
    print("=" * 95)

    print("\n" + "="*95)
    print(f"{'FINAL VISION SUMMARY REPORT':^95}")
    print("="*95)
    print(f"{'Scenario':<20} | {'Users':<6} | {'Pass':<5} | {'Fail':<5} | {'Avg TPS':<8} | {'Img Proc(s)':<12} | {'Sys T/s':<8} | {'Status':<10}")
    print("-" * 95)
    
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
        if fail > (users * 0.2) and users > 1:
            status = f"{RED}FAIL{RESET}"
        if fail == users:
            status = f"{RED}CRITICAL{RESET}"
            
        print(f"{stat['scenario']:<20} | {stat['users']:<6} | {stat['success']:<5} | {stat['fail']:<5} | {stat['avg_tps']:<8.2f} | {stat['avg_img_proc']:<12.2f} | {stat['sys_throughput']:<8.2f} | {status}")
    print("="*95 + "\n")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Benchmark Vision Suite for Ollama")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL_VISION, help="Vision model name (default: %(default)s)")
    parser.add_argument("--url", default=DEFAULT_OLLAMA_API, help="Ollama API URL (default: %(default)s)")
    return parser.parse_args()

def main():
    global MODEL_VISION, OLLAMA_API
    args = parse_arguments()
    MODEL_VISION = args.model
    OLLAMA_API = args.url

    # Detailed Header
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("=" * 60)
    print(f"{'BENCHMARK VISION SUITE - CONFIGURATION':^60}")
    print("=" * 60)
    print(f" Date Running Test: {start_time}")
    print(f" Model Vision : {MODEL_VISION}")
    print(f" API Endpoint : {OLLAMA_API}")
    print(f" Concurrency  : {USER_LEVELS}")
    print("=" * 60)
    print("")

    # Warmup
    print("Warming up VRAM...")
    task_vqa_standard(0) 
    time.sleep(2)
    
    all_stats = []
    for users in USER_LEVELS:
        all_stats.append(run_scenario("VQA_STANDARD", task_vqa_standard, users))
        time.sleep(3)

    print_summary_table(all_stats, start_time)

if __name__ == "__main__":
    main()