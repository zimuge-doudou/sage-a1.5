## Sage-A1.5 — uncensored Q4_K_M GGUF (15 parts + vision projector)

A local `llama.cpp` build of **Qwen3.5-MoE** (`qwen35moe`, 256 routed experts, 35B-A3B class) with the
stock refusal direction edited out of the weights. The edit is **fused into the GGUF** — no adapter
file is needed at inference time.

### Contents (16 assets)

| Asset | Size (bytes) |
| --- | --- |
| `sage-a1.5-q4km-abl4.0.gguf.part-a` … `part-n` | 1,887,436,800 each |
| `sage-a1.5-q4km-abl4.0.gguf.part-o` | 1,133,062,368 |
| `sage-a1.5-mmproj.gguf` | 899,282,880 |
| `SHA256SUMS` | — |

Joined model: **27,557,177,568 bytes**, 753 tensors, Q4_K_M with 46 tensors re-quantized during the
merge.

### How the build was made

Rank-1 directional abliteration on the post-trained chat model, merged with `llama-export-lora` at
scale 4.0 (46 tensors modified). No fine-tuning on harmful data and no reward model; nothing else in
the model was changed.

### Verify, then run

```bash
gh release download v1.0 -R zimuge-doudou/sage-a1.5 -D ./parts
cd ./parts && cat sage-a1.5-q4km-abl4.0.gguf.part-{a..o} > sage-a1.5-q4km-abl4.0.gguf
shasum -a 256 -c SHA256SUMS          # Linux: sha256sum -c

llama-server -m sage-a1.5-q4km-abl4.0.gguf --mmproj sage-a1.5-mmproj.gguf \
  -c 73728 -ctk q8_0 -ctv q8_0 -ngl 999 -fa on --host 127.0.0.1 --port 8090
```

No `--lora` / `--lora-scaled`: the edit already lives in the weights, and stacking a second one
degrades output.

### Numbers we measured ourselves

- Refusal probe (5 policy-adjacent prompts): **0 / 5 refusals** — same prompts, base weights without
  the edit: **2 / 5**
- Coding smoke bench, code executed rather than pattern-matched: **3 / 3 pass**
- Decode: **~50 tok/s**, M4 Pro / 64 GB, single stream, Q4_K_M
- Function calling: OpenAI-style `tools` supported

These are our smoke tests on one machine, not a benchmark submission.

### Read before using

- This build answers what the base model refuses. It will also produce incorrect, offensive or unsafe
  text, including confident fabrications. There is no safety layer and no truthfulness guarantee.
- Not safety-tested. Do not put it in front of users without your own guardrails.
- Intended for research on refusal behaviour, offline inference and red-teaming your own filters.
  You are responsible for what you generate and for the law where you run it.

### License

Base model **Qwen3.5-MoE** and this derivative: **Apache-2.0**. Keep the Qwen attribution when
redistributing.
