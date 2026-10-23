# Sage-A1.5 (Q4_K_M, uncensored)

A locally-runnable, refusal-suppressed build of the **Qwen3.5-MoE** family (256 routed experts,
35B-A3B class), packaged as a single Q4_K_M GGUF plus an F16 vision projector.

Weights are published as split release assets (GitHub caps each asset at 2 GiB).

- **Base architecture:** `qwen35moe` (Qwen3.5-MoE) — Apache-2.0
- **Quantization:** Q4_K_M, 20.2 GB, 753 tensors
- **Vision:** `sage-a1.5-mmproj.gguf` (F16, 858 MB)
- **Context:** trained/exported for long context; we run 64K with q8_0 KV cache
- **Serving:** llama.cpp `llama-server` (OpenAI-compatible `/v1`)

## What we changed

1. **Refusal-direction abliteration** on the post-training chat model (no fine-tuning on harmful
   data, no reward model): the refusal direction is projected out of the residual stream.
2. **A small LoRA adapter** carries the edit; it is applied with `--lora-scaled <file> 4.0`
   at serve time. Scale 4.0 is the value we settled on — higher starts to degrade reasoning.
3. **No safety layer, no system-prompt filtering** is added by us.

The result keeps the base model's coding/reasoning ability while dropping most stock refusals.
It is *not* a new pretrain and it is not aligned — see **Limitations**.

## Benchmarks (our own smoke tests, not a leaderboard submission)

Measured 2026-10-23 on a MacBook Pro M4 Pro / 64 GB, llama.cpp, `temp=0.4`,
`enable_thinking=false`, same prompts for every model we compared.

| Test | Result |
| --- | --- |
| Coding smoke bench (3 tasks: positional arithmetic, branchless max, small Python driver) | **3 / 3** |
| Refusal probe (5 policy-adjacent prompts: violent fiction, lock internals, political critique, intimacy, ballistics physics) | **0 / 5 refusals** |
| Decode speed (Q4_K_M, M4 Pro, single stream) | **~50 tok/s** |
| OpenAI `tools` / function calling | **supported** (`finish_reason=tool_calls`) |
| Same bench on Qwen3.8-27B abliterated (Q4) | 3 / 3, ~11 tok/s |
| Same bench on Qwen3.5-27B abliterated (Q4) | 2 / 3, ~56 tok/s |

Details and raw per-task notes: [`docs/eval.md`](docs/eval.md).

## Download

Release assets are named `sage-a1.5-q4km.gguf.part-aa … part-ak` (≈1.8 GiB each) plus
`sage-a1.5-mmproj.gguf` and `SHA256SUMS`.

```bash
gh release download v1.0 -R zimuge-doudou/sage-a1.5 -D ./parts
bash scripts/join_parts.sh ./parts
sha256sum -c ./parts/SHA256SUMS      # macOS: shasum -a 256 -c
```

## Run

```bash
llama-server \
  -m sage-a1.5-q4km.gguf \
  --mmproj sage-a1.5-mmproj.gguf \
  -c 65536 --flash-attn on -ngl 999 \
  --host 127.0.0.1 --port 8090
```

With the LoRA kept separate (if you build the adapter yourself), add
`--lora-scaled sage-a1.5-abl.q8.gguf 4.0`.

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

Full server script: [`scripts/serve.sh`](scripts/serve.sh).

## Hardware notes

- 20.2 GB of weights: needs **≥ 24 GB unified memory** to load comfortably at 8K context;
  64K context with q8_0 KV needs roughly 32 GB+.
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

Base model and this derivative: **Apache-2.0** (see [`LICENSE`](LICENSE)).
You must keep the Qwen attribution when redistributing.

## Citation

```
Sage-A1.5 (2026). Abliterated Q4_K_M build of Qwen3.5-MoE, Apache-2.0.
https://github.com/zimuge-doudou/sage-a1.5
```
