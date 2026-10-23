#!/usr/bin/env bash
# Reassemble sage-a1.5-q4km.gguf from release parts (part-aa, part-ab, ...).
# Usage: ./join_parts.sh <dir-with-parts> [output.gguf]
set -euo pipefail
DIR="${1:-./parts}"
OUT="${2:-./sage-a1.5-q4km.gguf}"

cd "$DIR"
ls sage-a1.5-q4km.gguf.part-* >/dev/null 2>&1 || { echo "no parts found in $DIR" >&2; exit 1; }

# Parts are named part-aa, part-ab, ...; sort by suffix so join order is stable.
parts=$(ls sage-a1.5-q4km.gguf.part-* | sort)
: > "$OUT.partial"
for p in $parts; do
  echo "  + $p"
  cat "$p" >> "$OUT.partial"
done
mv "$OUT.partial" "$OUT"
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"

if [ -f SHA256SUMS ]; then
  echo "verifying checksums..."
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c SHA256SUMS
  else
    sha256sum -c SHA256SUMS
  fi
fi
