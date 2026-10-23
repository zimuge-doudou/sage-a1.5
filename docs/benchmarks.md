# Benchmarks — Sage-A1.5 vs Qwen3.8-27B (same machine)

All numbers measured on one box, both models resident in memory at the same time, identical
prompts, `llama.cpp` (same build), `temperature 0.2`, single stream, `-ngl 999 -fa on`.

| | Sage-A1.5 (Q4_K_M, 35B MoE / 3B active) | Qwen3.8-27B (Q4_K_M, dense) | Ratio |
| --- | --- | --- | --- |
| Decode, 320 output tokens | **46.5 tok/s** | 6.4 tok/s | **~7×** |
| Prompt processing | **355 tok/s** | 46 tok/s | **~7.7×** |
| Chained shell-tool task, 4 dependent steps | **4 / 4** | 4 / 4 | tie |
| Multi-turn state chain, 6 dependent turns | **6 / 6** | 6 / 6 | tie |
| Native OpenAI `tool_calls` | yes | yes | — |

Second run of the same pair (both loaded, different time of day): Sage 45.5 tok/s vs Qwen 5.4 tok/s
→ ~8.4×. Decode gap is stable in the 7–8.6× band; it tracks active-parameter count (3B vs 27B), not
quantization.

## Why the gap

Sage-A1.5 inherits Qwen3.5-MoE routing: 256 experts, ~3B active per token. Qwen3.8-27B is dense, so
every token runs all 27B. On a single M4 Pro with the model fully offloaded, wall-clock decode is
dominated by weight reads — hence the near-linear ratio to parameter count.

## What "agent-ready" means here (measured, not marketed)

- **4/4 dependent tool steps**: build file → read & transform → branch on content → concatenate.
  The model chose its own shell command each step, consumed the tool output, and only stopped when the
  artifact existed.
- **6/6 multi-turn chain**: each turn's answer feeds the next (`×3`, then `+11` five times). No drift,
  no restating the wrong base value.
- **Native function calling**: `finish_reason=tool_calls`, arguments as JSON, works with the
  OpenAI-compatible `/v1` surface used by most agent frameworks.

Harness: [`scripts/agent_speed_bench.py`](../scripts/agent_speed_bench.py),
[`scripts/multiturn_chain.py`](../scripts/multiturn_chain.py). Raw JSON: `/tmp/bench_*.json`.

## Caveats

- Single machine, single stream, one quant per model. Not a cross-hardware claim.
- Refusal probe (5 policy-adjacent prompts): Sage 0/5, same base without the edit 2/5 — see
  [`verification.md`](verification.md).
- No safety, truthfulness or long-context benchmark was run. Numbers above describe speed and
  multi-step instruction following only.
