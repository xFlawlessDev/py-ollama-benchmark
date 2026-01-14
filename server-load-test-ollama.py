import requests
import time
import concurrent.futures
import statistics
import argparse

# Prompt yang cukup berat untuk memaksa GPU bekerja
# Kita pakai prompt coding/reasoning agar processing time-nya nyata.
PROMPT = "Write a python function to calculate fibonacci sequence up to n terms. Explain the logic briefly."

def simulate_user_request(user_id, model_name, api_url):
    """Fungsi ini mensimulasikan satu user."""
    print(f"   [User {user_id}] \U0001F680 Request sent... waiting for response...")
    start_time = time.time()
    
    payload = {
        "model": model_name,
        "prompt": PROMPT,
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.7
        }
    }
    
    try:
        # Kirim request
        response = requests.post(api_url, json=payload, timeout=300) # Timeout panjang untuk antrian
        response.raise_for_status()
        data = response.json()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Ambil metrik
        eval_count = data.get('eval_count', 0)
        eval_duration_ns = data.get('eval_duration', 0)
        
        # Hitung T/s spesifik user ini
        tps = 0
        if eval_duration_ns > 0:
            tps = eval_count / (eval_duration_ns / 1e9)
            
        return {
            "success": True,
            "user_id": user_id,
            "duration": total_duration,
            "tokens": eval_count,
            "tps": tps
        }

    except Exception as e:
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }

def print_results(results, model_name, concurrent_users):
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print("\n" + "="*60)
    print(f" HASIL LOAD TEST: {concurrent_users} USERS SIMULTAN")
    print("="*60)
    print(f" Model           : {model_name}")
    print(f" Sukses          : {len(successful)} / {len(results)}")
    print(f" Gagal/Timeout   : {len(failed)}")
    print("-" * 60)
    
    if successful:
        durations = [r['duration'] for r in successful]
        tokens_per_seconds = [r['tps'] for r in successful]
        total_tokens = sum([r['tokens'] for r in successful])
        
        avg_latency = statistics.mean(durations)
        max_latency = max(durations)
        min_latency = min(durations)
        avg_tps = statistics.mean(tokens_per_seconds)
        
        # Total System Throughput (Total token yang diproduksi server per detik gabungan)
        # Ini menunjukkan kekuatan asli Ryzen AI Max Anda
        system_throughput = total_tokens / max_latency 

        print(f" RATA-RATA WAKTU TUNGGU (Latency) : {avg_latency:.2f} detik")
        print(f" WAKTU TUNGGU TERLAMA (Worst Case): {max_latency:.2f} detik")
        print("-" * 60)
        print(f" KECEPATAN PER USER (Avg Speed)   : {avg_tps:.2f} tokens/sec")
        print(f" TOTAL SYSTEM THROUGHPUT          : {system_throughput:.2f} tokens/sec")
    
    if failed:
        print("\n[ERROR LOG]")
        for f in failed:
            print(f" User {f['user_id']}: {f['error']}")
    print("="*60)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ollama Server Load Tester")
    parser.add_argument("-m", "--model", default="qwen3-vl:30b", help="Model name (default: qwen3-vl:30b)")
    parser.add_argument("-u", "--users", type=int, default=10, help="Number of concurrent users (default: 10)")
    parser.add_argument("--url", default="http://localhost:11434/api/generate", help="Ollama API URL")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    print(f"--- KONFIGURASI ---")
    print(f" Model           : {args.model}")
    print(f" URL             : {args.url}")
    print(f" Users           : {args.users}")
    print("-------------------")
    
    print(f"--- MEMULAI SIMULASI SERANGAN {args.users} USER ---\n")
    
    results = []
    
    # Menggunakan ThreadPool untuk mengirim request bersamaan
    print(f"   >>> Submitting {args.users} concurrent requests to server...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as executor:
        future_to_user = {
            executor.submit(simulate_user_request, i+1, args.model, args.url): i
            for i in range(args.users)
        }
        
        for future in concurrent.futures.as_completed(future_to_user):
            user_id = future_to_user[future]
            try:
                data = future.result()
                results.append(data)
                status = "SUKSES" if data['success'] else "GAGAL"
                print(f"   [User {user_id}] Selesai. Status: {status} ({data.get('duration', 0):.2f}s)")
            except Exception as exc:
                print(f"   [User {user_id}] Exception: {exc}")

    print_results(results, args.model, args.users)

if __name__ == "__main__":
    main()