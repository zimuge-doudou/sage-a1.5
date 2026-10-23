#!/usr/bin/env bash
# Serve Sage-A1.5 Q4_K_M with the vision projector on an OpenAI-compatible port.
# Usage: ./serve.sh [model.gguf] [mmproj.gguf] [port] [ctx]
set -euo pipefail

MODEL="${1:-./sage-a1.5-q4km.gguf}"
MMPROJ="${2:-./sage-a1.5-mmproj.gguf}"
PORT="${3:-8090}"
CTX="${4:-65536}"
BIN="${LLAMA_SERVER:-llama-server}"

args=(-m "$MODEL" -c "$CTX" -ngl 999 -fa on --jinja --no-warmup -np 1
      --host 127.0.0.1 --port "$PORT")
[ -f "$MMPROJ" ] && args+=(--mmproj "$MMPROJ")
# Optional external LoRA (only if you keep the adapter separate from the merge):
[ -n "${SAGE_LORA:-}" ] && args+=(--lora-scaled "$SAGE_LORA" "${SAGE_LORA_SCALE:-4.0}")

echo "starting $BIN on :$PORT (ctx=$CTX)"
exec "$BIN" "${args[@]}"
