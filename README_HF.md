---
license: apache-2.0
library_name: llama.cpp
pipeline_tag: text-generation
tags:
  - gguf
  - llama.cpp
  - qwen3.5-moe
  - moe
  - abliterated
  - uncensored
  - vision
language:
  - en
  - zh
base_model: Qwen3.5-MoE
---

# Sage-A1.5 (Q4_K_M, uncensored)

A locally-runnable, refusal-suppressed build of the **Qwen3.5-MoE** family (256 routed experts,
35B-A3B class), packaged as a single Q4_K_M GGUF plus an F16 vision projector.

- **This repo (Hugging Face):** single-file GGUF, easiest download
- **GitHub mirror (split parts + scripts):** https://github.com/zimuge-doudou/sage-a1.5

| File | Size | What |
| --- | --- | --- |
| `sage-a1.5-q4km-abl4.0.gguf` | 27.56 GB | **Abliteration already merged into the weights** (LoRA scale 4.0 baked in), 753 tensors |
| `sage-a1.5-mmproj.gguf` | 899 MB | F16 vision projector |

> ⚠️ The plain Q4_K_M base (`sage-a1.5-q4km.gguf`) is **not** shipped: that file is the stock
> quantization and refuses like the original model. Download the `abl4.0` file above.

- **Base architecture:** `qwen35moe` (Qwen3.5-MoE) — Apache-2.0
- **Context:** trained/exported for long context; we run 73,728 tokens with q8_0 KV cache
- **Serving:** llama.cpp `llama-server` (OpenAI-compatible `/v1`)
- **No adapter needed at serve time:** `-m sage-a1.5-q4km-abl4.0.gguf` is enough.

## What we changed

1. **Refusal-direction abliteration** on the post-training chat model (no fine-tuning on harmful
   data, no reward model): the refusal direction is projected out of the residual stream.
2. **The edit is fused into the shipped weights.** We first produced a rank-1 abliteration adapter,
   found scale 4.0 to be the sweet spot (higher starts to degrade reasoning), then merged it into
   the GGUF with `llama-export-lora --lora-scaled …:4.0`. Loading the file needs no `--lora` flag.
3. **No safety layer, no system-prompt filtering** is added by us.

Verification we ran on the merged file itself (not on the adapter path): 5 policy-adjacent prompts →
**0 refusals**, identical to the un-merged serving setup, and the coding bench still passes 3/3.

The result keeps the base model's coding/reasoning ability while dropping most stock refusals.
It is *not* a new pretrain and it is not aligned — see **Limitations**.

## Benchmarks (our own smoke tests, not a leaderboard submission)

Measured 2026-10-23 on a MacBook Pro M4 Pro / 64 GB, llama.cpp, `temp=0.4`,
`enable_thinking=false`, same prompts for every model we compared.

| Test | Result |
| --- | --- |
| Coding smoke bench (3 tasks: positional arithmetic, branchless max, small Python driver) | **3 / 3** |
| Refusal probe (5 policy-adjacent prompts) | **0 / 5 refusals** |
| Decode speed (Q4_K_M, M4 Pro, single stream) | **~50 tok/s** |
| OpenAI `tools` / function calling | **supported** (`finish_reason=tool_calls`) |
| Same bench on Qwen3.8-27B abliterated (Q4) | 3 / 3, ~11 tok/s |
| Same bench on Qwen3.5-27B abliterated (Q4) | 2 / 3, ~56 tok/s |

Raw per-task notes: https://github.com/zimuge-doudou/sage-a1.5/blob/main/docs/eval.md

## Download

```bash
# whole file, resumable
hf download amy-sage/sage-a1.5 sage-a1.5-q4km-abl4.0.gguf --local-dir .
hf download amy-sage/sage-a1.5 sage-a1.5-mmproj.gguf --local-dir .
```

GitHub (split into 15 parts, 14 × 1.8 GiB + one 1.06 GiB, with SHA256SUMS):

```bash
gh release download v1.0 -R zimuge-doudou/sage-a1.5 -D ./parts
cd ./parts && cat sage-a1.5-q4km-abl4.0.gguf.part-{a..o} > sage-a1.5-q4km-abl4.0.gguf
sha256sum -c ./parts/SHA256SUMS      # macOS: shasum -a 256 -c
```

## Run

```bash
llama-server \
  -m sage-a1.5-q4km-abl4.0.gguf \
  --mmproj sage-a1.5-mmproj.gguf \
  -c 73728 -ctk q8_0 -ctv q8_0 -ngl 999 -fa on \
  --host 127.0.0.1 --port 8090
```

OpenAI-compatible client:

```python
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:8090/v1", api_key="local")
print(c.chat.completions.create(
    model="sage-a1.5",
    messages=[{"role": "user", "content": "Explain MoE routing in two sentences."}],
    max_tokens=512,
).choices[0].message.content)
```

## Hardware notes

- 25.7 GiB of weights: needs **≥ 32 GB unified memory** to load comfortably at 8K context;
  64K context with q8_0 KV needs roughly 40 GB.
- On Apple silicon, `-ngl 999 --flash-attn on` puts everything on the GPU.
- On a 24 GB machine, use `-c 8192` and expect slower prompt processing.

## Limitations

- **Uncensored by construction.** It will answer things the base model refuses. That is the point,
  but it also means it will happily produce wrong, offensive, or unsafe text — including confident
  hallucinations. It has no truthfulness guarantee.
- **Numbers are the weak spot.** We measured it inventing disk-usage figures when asked about the
  host machine; feed it real values (or a tool result) instead of trusting recall.
- **Self-reports are unreliable** — treat any "I did X" from this model as a claim to verify.
- Not evaluated on safety benchmarks; not for user-facing deployment without your own guardrails.

## License

Base model and this derivative: **Apache-2.0** (see `LICENSE`).
You must keep the Qwen attribution when redistributing.

## Citation

```
Sage-A1.5 (2026). Abliterated Q4_K_M build of Qwen3.5-MoE, Apache-2.0.
https://huggingface.co/amy-sage/sage-a1.5
https://github.com/zimuge-doudou/sage-a1.5
```
