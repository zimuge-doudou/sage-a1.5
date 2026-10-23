# Sage-A1.5 (Q4_K_M, uncensored build)

A local GGUF build of the **Qwen3.5-MoE** family (`qwen35moe`, 256 routed experts, 35B-A3B class)
with the stock refusal behaviour edited out. Published as 15 split GGUF parts plus an F16 vision
projector, ready for `llama.cpp`.

- **Base architecture:** `qwen35moe` (Qwen3.5-MoE) — Apache-2.0
- **Quantization:** Q4_K_M base, 46 tensors re-quantized during the merge
- **File size:** 27,557,177,568 bytes (27.56 GB decimal / 25.7 GiB), 753 tensors
- **Vision:** `sage-a1.5-mmproj.gguf` (F16, 899,282,880 bytes)
- **Context:** 73,728 tokens with q8_0 KV cache (we serve at this value)
- **Serving:** llama.cpp `llama-server`, OpenAI-compatible `/v1`

## What we changed

1. **Directional abliteration** on the post-trained chat model: a rank-1 refusal-direction edit is
   estimated from paired prompt/response activations and projected out of the residual stream. No
   fine-tuning on harmful data, no reward model, no extra safety layer added by us.
2. **The edit is fused into the shipped weights.** We first trained a rank-1 adapter, found scale 4.0
   to be the point where refusals drop without degrading reasoning, then merged it into the GGUF with
   `llama-export-lora` (46 tensors modified, 753 written). **No adapter file is needed at inference
   time** — do not stack another LoRA on top of this build.
3. Nothing else was changed: tokenizer, chat template and tool-calling behaviour are the base model's.

This is a weight edit on an existing model, not a new pretrain and not an alignment run.
See **Limitations** before deploying.

## Verified results (our own smoke tests, not a leaderboard submission)

Measured 2026-10-23 on a MacBook Pro M4 Pro / 64 GB, `llama.cpp`, `temp=0.4`,
`enable_thinking=false`, identical prompts for every build compared.

| Test | Result |
| --- | --- |
| Refusal probe, 5 policy-adjacent prompts | **0 / 5 refusals** (same set: base with no edit → 2 / 5) |
| Chained shell-tool task, 4 dependent steps | **4 / 4** (model picks commands, reads output, self-terminates) |
| Multi-turn state chain, 6 dependent turns | **6 / 6** |
| Coding smoke bench, executed rather than string-matched | **3 / 3 pass** |
| Decode speed, Q4_K_M, M4 Pro, single stream | **46.5 tok/s** (Qwen3.8-27B dense, same box: 6.4 → **~7×**) |
| OpenAI-style `tools` / function calling | **supported** (`finish_reason=tool_calls`) |
| Merge integrity | 15 / 15 part SHA-256 values match the source file |

Per-prompt detail and method: [`docs/verification.md`](docs/verification.md).
Same-machine A/B against Qwen3.8-27B, harness and caveats: [`docs/benchmarks.md`](docs/benchmarks.md).
Earlier benchmark notes: [`docs/eval.md`](docs/eval.md).

## Download

The release holds 16 assets:

- `sage-a1.5-q4km-abl4.0.gguf.part-a` … `.part-o` — 15 parts, 14 × 1,887,436,800 B + 1,133,062,368 B
- `sage-a1.5-mmproj.gguf` — vision projector
- `SHA256SUMS` — checksums for every asset above

```bash
gh release download v1.0 -R zimuge-doudou/sage-a1.5 -D ./parts
cd ./parts && cat sage-a1.5-q4km-abl4.0.gguf.part-{a..o} > sage-a1.5-q4km-abl4.0.gguf
shasum -a 256 -c SHA256SUMS          # Linux: sha256sum -c
```

Join order matters: `part-a` → `part-o`, lexical order is correct for these names.

## Run

```bash
llama-server \
  -m sage-a1.5-q4km-abl4.0.gguf \
  --mmproj sage-a1.5-mmproj.gguf \
  -c 73728 -ctk q8_0 -ctv q8_0 -ngl 999 -fa on \
  --host 127.0.0.1 --port 8090
```

No `--lora`/`--lora-scaled` flag: the edit already lives in the weights. Passing one applies a
second edit and will degrade output.

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

Server launcher used here: [`scripts/serve.sh`](scripts/serve.sh).

## Hardware notes

- 25.7 GiB of weights: **≥ 32 GB unified memory** for 8K context; 64K context with q8_0 KV needs
  roughly 40 GB.
- Apple silicon: `-ngl 999 -fa on` offloads everything to the GPU; expect ~50 tok/s decode.
- 24 GB machines: use `-c 8192` and expect slower prompt processing.

## Limitations

- **Uncensored by construction.** It answers what the base model refuses. That is the purpose of this
  build, and it also means it will produce wrong, offensive or unsafe text — including confident
  fabrications. No truthfulness guarantee.
- **Numbers are the weak spot.** Observed inventing disk-usage figures when asked about the host
  machine; feed it real values or tool output instead of trusting recall.
- **Self-reports are unreliable.** Treat any "I did X" from the model as a claim to verify.
- Not evaluated on safety benchmarks. Not for user-facing deployment without your own guardrails.

## Intended use

Research on refusal behaviour, local/offline inference, red-teaming your own guardrails. You are
responsible for what you generate with it and for complying with the law where you run it.

## License

Base model and this derivative: **Apache-2.0** (see [`LICENSE`](LICENSE)). Keep the Qwen attribution
when redistributing.

## Citation

```
Sage-A1.5 (2026). Fused-abliteration Q4_K_M build of Qwen3.5-MoE, Apache-2.0.
https://github.com/zimuge-doudou/sage-a1.5
```
