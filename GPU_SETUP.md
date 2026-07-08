# Local GPU Setup Guide

Mnemosyne agents (Sage, Nova, Vera, Haiku) support GPU-accelerated local inference via Ollama, vLLM, or llama.cpp. Run the full agent pipeline locally without cloud costs or API dependencies.

## Quick Start: Ollama + GPU (Recommended)

**Best for:** Most users. Automatic GPU detection, easy model management.

```bash
# Install Ollama (automatically detects GPU: CUDA, ROCm, Metal)
# https://ollama.ai

# Pull a capable model for local Sage/Nova/Vera
ollama pull llama2:70b
ollama pull llama2:13b  # For Vera (smaller, faster for review)
ollama pull qwen2.5:1.5b  # For Haiku (fast utility tasks)

# Start Ollama server (GPU auto-selected)
ollama serve
```

**Configure mnemosyne:**
```bash
# .env
MNEMOSYNE_AGENT_PROFILE=local-only
MNEMOSYNE_OLLAMA_HOST=http://localhost:11434
```

**Result:** Sage/Nova/Vera use llama2:70b, Haiku uses qwen2.5:1.5b — all GPU-accelerated, zero cloud cost.

---

## Advanced: vLLM + NVIDIA GPU

**Best for:** High throughput, batch workloads, large models (70B+).

**Requirements:** NVIDIA GPU with CUDA 11.8+.

```bash
# Install vLLM with CUDA support
pip install vllm

# Start vLLM server with Llama 2 70B
vllm serve meta-llama/Llama-2-70b-hf \
  --port 8000 \
  --dtype auto \
  --tensor-parallel-size 1  # Use 1 GPU; increase if you have multiple

# Or with faster-inference framework
vllm serve meta-llama/Llama-2-70b-hf \
  --port 8000 \
  --gpu-memory-utilization 0.9 \
  --dtype float16
```

**Configure mnemosyne:**
```bash
# .env
MNEMOSYNE_AGENT_PROFILE=local-only
MNEMOSYNE_CHAT_PROVIDER=openai
MNEMOSYNE_OPENAI_CHAT_BASE_URL=http://localhost:8000/v1
```

---

## Advanced: llama.cpp + Any GPU

**Best for:** CPU-heavy users, Metal (macOS), older GPUs, resource-constrained setups.

**Requirements:** NVIDIA CUDA, AMD ROCm, or Apple Metal (via build flags).

```bash
# Install with GPU support
# CUDA (NVIDIA)
pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir \
  -C cmake.args="-DLLAMA_CUDA=on"

# ROCm (AMD)
pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir \
  -C cmake.args="-DLLAMA_HIPBLAS=on"

# Metal (macOS)
pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir \
  -C cmake.args="-DLLAMA_METAL=on"

# Start llama.cpp server
python -m llama_cpp.server \
  --model ./models/llama-2-70b.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n-gpu-layers 50  # Adjust based on VRAM
```

**Configure mnemosyne:**
```bash
# .env
MNEMOSYNE_AGENT_PROFILE=local-only
MNEMOSYNE_CHAT_PROVIDER=openai
MNEMOSYNE_OPENAI_CHAT_BASE_URL=http://localhost:8080/v1
```

---

## Remote GPU Server (Private Infrastructure)

**Scenario:** GPU cluster, on-premise server, or private cloud infrastructure.

**Setup:**
1. Deploy vLLM, Ollama, or llama.cpp on your GPU server
2. Expose OpenAI-compatible `/v1/chat/completions` endpoint
3. Configure mnemosyne to point to it

```bash
# .env
MNEMOSYNE_AGENT_PROFILE=hybrid
MNEMOSYNE_OPENAI_CHAT_BASE_URL=http://your-gpu-server:8000/v1
MNEMOSYNE_OPENAI_API_KEY=optional-if-authenticated

# Or use Ollama endpoint
MNEMOSYNE_OLLAMA_HOST=http://your-gpu-server:11434
```

**Security notes:**
- Use TLS (HTTPS) for remote endpoints in production
- Protect with authentication if exposed on a network
- Never commit API keys or credentials to git

---

## Hybrid Mode (Cloud + Local GPU)

Best of both worlds: expensive thinking on local GPU, fast utility tasks on cloud.

```bash
# .env
MNEMOSYNE_AGENT_PROFILE=hybrid
ANTHROPIC_API_KEY=your-key

# Point Haiku (routine tasks) to local GPU
MNEMOSYNE_OLLAMA_HOST=http://localhost:11434

# Sage/Nova/Vera use Claude (cloud fallback in hybrid profile)
# If Claude is unavailable, they automatically fall back to Ollama
```

**Result:**
- Sage (planning): Claude Opus (fast, high-quality analysis)
- Nova (implementation): Claude Opus (best code generation)
- Vera (review): Claude Opus (thorough correctness checks)
- Haiku (routine): Ollama llama2:1.5b locally (zero cost)
- Fallback: All agents → Ollama if Claude is down

---

## Performance Tuning

### GPU Memory Optimization

**Reduce memory usage:**
```bash
# Use quantized models (4-bit, 8-bit)
ollama pull llama2:7b  # Instead of 70b
vllm serve meta-llama/Llama-2-13b-hf --load-in-8bit

# Lower precision
vllm serve meta-llama/Llama-2-70b-hf --dtype float16
```

**Speed vs Quality:**
| Model | Inference Speed | Quality | VRAM |
|-------|-----------------|---------|------|
| llama2:1.5b | Very fast | Low | 3GB |
| llama2:7b | Fast | Medium | 14GB |
| llama2:13b | Medium | Good | 26GB |
| llama2:70b | Slower | Excellent | 140GB |

### Batch Processing

Use `vllm` for batch workloads where latency is less critical:
```python
# vLLM auto-batches multiple requests
# Ideal for eval runs, bulk ingestion, etc.
MNEMOSYNE_OPENAI_CHAT_BASE_URL=http://localhost:8000/v1
```

### Multi-GPU Setup

**vLLM with multiple GPUs:**
```bash
vllm serve meta-llama/Llama-2-70b-hf \
  --port 8000 \
  --tensor-parallel-size 2  # Use 2 GPUs
```

---

## Troubleshooting

**"Connection refused" errors:**
- Verify server is running: `curl http://localhost:11434/api/tags`
- Check endpoint URL in `.env` matches your server
- Ensure firewall allows access

**Out of memory (OOM):**
- Reduce model size: `ollama pull llama2:13b` instead of 70b
- Enable quantization: `--load-in-8bit`
- Reduce batch size or `--tensor-parallel-size`

**Slow inference:**
- Check GPU is actually being used: `nvidia-smi` (NVIDIA) or `rocm-smi` (AMD)
- Increase `--n-gpu-layers` (llama.cpp) or `--tensor-parallel-size` (vLLM)
- Use faster models (qwen, mistral, neural-chat) instead of llama2

---

## Model Recommendations

| Use Case | Model | VRAM | Speed | Quality |
|----------|-------|------|-------|---------|
| **Sage** (planning) | llama2:70b | 140GB | Slow | Excellent |
| **Sage** (smaller) | llama2:13b | 26GB | Medium | Good |
| **Nova** (implementation) | llama2:70b | 140GB | Slow | Excellent |
| **Nova** (balanced) | neural-chat:7b | 15GB | Fast | Good |
| **Vera** (review) | llama2:13b | 26GB | Medium | Good |
| **Haiku** (routine) | qwen2.5:1.5b | 3GB | Very fast | OK |

---

## References

- **Ollama**: https://ollama.ai (auto GPU detection)
- **vLLM**: https://github.com/lm-sys/vllm (high throughput)
- **llama.cpp**: https://github.com/ggerganov/llama.cpp (lightweight)
- **CUDA**: https://developer.nvidia.com/cuda-toolkit (NVIDIA GPU)
- **ROCm**: https://rocmdocs.amd.com (AMD GPU)

---

## Cost Comparison

| Setup | Sage/Nova/Vera | Haiku | Cost per Session* |
|-------|-----------------|-------|-------------------|
| Local GPU (your hardware) | Ollama llama2:70b | Ollama qwen2.5 | $0.00 |
| Hybrid (GPU + Claude) | Claude Opus | Ollama qwen2.5 | $0.05-0.20 |
| Cloud-only (Claude) | Claude Opus | Claude Haiku | $0.20-1.00 |

\* Estimated for a 10-turn planning/implementation/verification cycle
