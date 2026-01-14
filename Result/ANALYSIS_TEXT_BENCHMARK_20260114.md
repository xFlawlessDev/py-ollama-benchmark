# Benchmark Analysis Report: Qwen Text Assessment (2026-01-14)

## 1. Overview
This report analyzes the performance data from the text benchmark run conducted on January 14, 2026. The test evaluated the system's capabilities across three distinct scenarios: `CHAT_LIGHT` (short interactions), `CODING_HEAVY` (complex generation), and `RAG_FLOW` (context-intensive retrieval), under varying levels of user concurrency (1, 8, 16, and 32 users).

**Date:** 2026-01-14
**Model/Engine:** Qwen (Text)

## 2. Concurrency Analysis

### Single User (1 User)
*   **Status:** ✅ Excellent
*   **Performance:** 100% Reliability (0 failures).
*   **Speed:** Consistently high throughput (~60-61 t/s).
*   **Latency:** Minimal (7-14s).
*   **Observation:** The system performs optimally without load, delivering rapid responses across all task types.

### Medium Load (8 Users)
*   **Status:** ⚠️ Early Signs of Stress
*   **Performance:**
    *   `CHAT_LIGHT`: 100% Success.
    *   `CODING_HEAVY`: ~87% Success (1 failure).
    *   `RAG_FLOW`: ~62% Success (3 failures).
*   **Observation:** The system begins to saturate. While simple chat remains stable, heavier computational tasks lead to dropped requests, indicating the queue or timeout limits are being reached.

### High Load (16 Users)
*   **Status:** ❌ Critical Degradation
*   **Performance:** Failure rates spike significantly.
    *   `CHAT_LIGHT`: ~31% Failure (5 failed).
    *   `CODING_HEAVY`: ~56% Failure (9 failed).
    *   `RAG_FLOW`: ~69% Failure (11 failed).
*   **Observation:** The system cannot handle this level of concurrency. The majority of heavy tasks fail, likely due to timeouts while waiting for GPU resources.

### Overload (32 Users)
*   **Status:** 💀 System Collapse
*   **Performance:** >65% failure rate across all categories.
    *   `CHAT_LIGHT`: 21 failures.
    *   `CODING_HEAVY`: 25 failures.
    *   `RAG_FLOW`: 28 failures.
*   **Observation:** The system is completely overwhelmed. Only a small fraction of requests are processed successfully.

## 3. Key Insight: The "60 t/s" Plateau

A critical anomaly is observed in the `avg_tps` metric:

| Scenario | 1 User TPS | 32 Users TPS |
| :--- | :--- | :--- |
| CHAT_LIGHT | 61.3 | 61.8 |
| CODING_HEAVY | 61.3 | 61.3 |

**Analysis:**
The average tokens per second (TPS) for *successful* requests remains virtually constant at ~60 t/s, regardless of the load. This indicates:
1.  **Fixed Processing Speed:** The GPU is processing successful tokens at a fixed maximum rate.
2.  **Throughput vs. Latency:** The system is **not** parallelizing effectively in a way that slows down *everyone* to accommodate more users (which would lower per-user TPS). Instead, it processes a few users at full speed while others queue until they time out.
3.  **Capacity Limit:** The high failure rates combined with stable TPS suggests the failures are almost certainly caused by **timeouts** (likely connection/queue timeouts in Ollama or the Python script's timeout setting) rather than execution crashes.

## 4. Recommendations

1.  **Reduce Concurrency Settings:** The current "safe max" for this specific hardware/model configuration is approximately **4-6 concurrent users** for heavy workloads.
2.  **Adjust Timeout Configuration:**
    *   Increase the client-side timeout in the benchmark script (e.g., `requests.post(..., timeout=300)`).
    *   Check Ollama's server queue settings.
3.  **Ollama Configuration:**
    *   If using `OLLAMA_NUM_PARALLEL`, consider lowering it. While it allows more concurrent slots, if VRAM is limited, it splits context size or leads to queuing that exceeds standard HTTP timeouts.

---

# Benchmark Analysis Report: DeepSeek R1 (32B) Assessment (2026-01-14 17:23)

## 1. Overview (DeepSeek)
Following the Qwen assessment, the heavier `deepseek-r1:32b` model was evaluated under the same conditions. This test highlights the performance trade-offs when moving to a significantly larger model class (32B parameters) on the same hardware infrastructure.

**Date:** 2026-01-14 17:23:43
**Model:** `deepseek-r1:32b`
**Embedding:** `qwen3-embedding:4b`

## 2. Concurrency Analysis

### Single User (1 User)
*   **Status:** ✅ Acceptable
*   **Performance:** 100% Reliability.
*   **Speed:** ~10.7 TPS (Generation).
*   **RAG Effective Rate:** ~4.41 TPS.
*   **Observation:** The model functions correctly but matches the expected slower throughput of a 32B model compared to the lighter Qwen model (which achieved ~60 TPS). The RAG effective rate suggests significant overhead in the retrieval/embedding stage or context processing.

### Medium Load (8 Users)
*   **Status:** 💀 Critical Failure (Collapse)
*   **Performance:**
    *   `CHAT_LIGHT`: 12.5% Success (1/8 passed) at 5.37 TPS.
    *   `CODING_HEAVY`: 100% Failure (0/8 passed).
    *   `RAG_FLOW`: 100% Failure (0/8 passed).
*   **Observation:** The drastic drop to near-zero success rate indicates the hardware cannot support 8 concurrent streams for a model of this size. The single successful chat request ran at ~50% speed (5.37 TPS), suggesting heavy resource contention.

### High Load (16 & 32 Users)
*   **Status:** ❌ Total System Inoperability
*   **Performance:** High failure rate to Total failure.
*   **Observation:** Requests timed out completely.

## 3. Comparative Technical Analysis

### Single-Stream Efficiency
*   **Qwen:** ~60 TPS
*   **DeepSeek-R1 (32B):** ~10.7 TPS
*   **Insight:** DeepSeek is approximately **5.6x computationally heavier** per token on this hardware. This aligns with the transition from a smaller model (likely 7B-14B range) to a 32B model, plus potential overhead from the reasoning capabilities of R1.

### Concurrency Ceiling & Resource Contention
The behavior at Concurrency 8 reveals the hard limit of the current setup.
*   **Qwen:** At 8 users, mostly succeeded (dropping only heavy tasks).
*   **DeepSeek:** At 8 users, the system collapsed.
*   **Root Cause:**
    *   **Memory Bandwidth:** A 32B model requires significantly more bandwidth to move weights. Eight concurrent users likely saturate bandwidth so severely that generation stalls, causing timeouts.
    *   **Timeouts:** With a base speed of 10 TPS, even a modest queue creates delays that exceed the client benchmark timeout (usually 60s). If 8 users are serialized, the last user might wait `8 * (Latency)` which is far beyond the limit.

## 4. Recommendations for DeepSeek
1.  **Strict Serial Processing:** For `deepseek-r1:32b`, `OLLAMA_NUM_PARALLEL` should be set to 1. The hardware cannot handle parallel inference for this model size.
2.  **Timeout Extension:** If simple concurrency (2-3 users) is attempted, client timeouts must be increased significantly (e.g., to 300s+).
3.  **UseCase Selection:** This model should be reserved for high-value, complex reasoning tasks (Coding, RAG) in a single-user or queued pipeline, rather than real-time multi-user chatbots.

---

# Benchmark Analysis Report: GPT-OSS (20B) Assessment (2026-01-14 17:13)

## 1. Overview
The `gpt-oss:20b` model represents a middle-ground in parameter size, balancing the raw speed of smaller models with the capability of larger ones. This assessment evaluates its performance stability under load, specifically contrasting its scalability against the heavier DeepSeek 32B.

**Date:** 2026-01-14 17:13:42
**Model:** `gpt-oss:20b`
**Embed:** `qwen3-embedding:4b`

## 2. Concurrency Analysis

### Single User (1 User)
*   **Status:** ✅ Excellent
*   **Performance:** 100% Success.
*   **Speed:** ~48 TPS.
*   **Observation:** High-speed generation, only slightly slower than the lightweight Qwen model (60 TPS) and significantly faster than DeepSeek 32B (10 TPS).

### Medium Load (8 Users) - *The Sweet Spot*
*   **Status:** ✅ Robust Performance
*   **Performance:**
    *   **All Scenarios:** 100% PASS.
    *   **Per-User Speed:** ~20-22 TPS.
    *   **System Throughput:** ~87-99 TPS.
*   **Observation:** This is the model's peak efficiency zone. Unlike DeepSeek (which collapsed here) and Qwen (which showed minor errors), GPT-OSS 20B maintained stability across all task types with impressive aggregate throughput.

### High Load (16 Users)
*   **Status:** ⚠️ Mixed (Task Dependent)
*   **Performance:**
    *   `CHAT_LIGHT`: 100% Success (20.53 TPS).
    *   `CODING_HEAVY`: ~75% Success (12/16 pass).
    *   `RAG_FLOW`: ~37% Success (6/16 pass).
*   **Observation:** A clear divergence appears. Lightweight chat remains stable and fast (101 Sys TPS), but heavy context tasks begin to time out.

### Massive Load (32 Users)
*   **Status:** ❌ Heavy Task Failure / ⚠️ Chat Viable
*   **Performance:**
    *   `CHAT_LIGHT`: ~87% Success (28/32 pass).
    *   `CODING_HEAVY`: ~37% Success (12/32 pass).
    *   `RAG_FLOW`: ~18% Success (6/32 pass).
*   **Observation:** Remarkably, simple chat remains largely viable even at extreme concurrency. However, the system lacks the VRAM/Compute bandwidth to service 32 concurrent heavy coding/RAG requests.

## 3. Technical Analysis: The "Workhorse" Capability

### Efficiency vs. Size
At 20B parameters, this model hits a unique performance niche:
*   **Vs. 32B Models:** It offers **4x the single-stream speed** (48 vs 10 TPS) and **infinitely better scalability** (holding C8 where DeepSeek failed).
*   **Vs. Light Models:** It maintains higher reliability at C8 than the Qwen run, suggesting superior memory management or batching characteristics in the serving layer.

### Throughput Scaling
The system achieves nearly **100 System TPS** at concurrency levels 8, 16, and 32 (for surviving requests). This indicates the inference engine is fully maximizing the GPU compute cycles without hitting the memory wall that paralyzed the 32B model.

## 4. Recommendations
1.  **Ideal Deployment Target:** This is the recommended model for **general-purpose production** usage involving 8-12 concurrent users.
2.  **Task Separation:**
    *   **Chatbots:** Safe to scale up to **20-30 concurrent users**.
    *   **Coding/RAG:** Limit to **8 concurrent users** to ensure 100% reliability.
3.  **Configuration:** The stability at C8 suggests `OLLAMA_NUM_PARALLEL` is well-tuned for this model size on the current hardware.