#!/usr/bin/env python3
"""GitHub Release 分片完整性核验：匿名下载 15 片 → 逐片 SHA256 对比本地 → 拼回整文件对比总 SHA256。"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

REPO = "zimuge-doudou/sage-a1.5"
TAG = "v1.0"
SRC = os.path.expanduser("~/.hermes/models/sage-a1.5-q4km-abl4.0.gguf")
NAME = "sage-a1.5-q4km-abl4.0.gguf"
CHUNK = 1887436800
PARTS = 15
DL = "/tmp/ghverify"

os.makedirs(DL, exist_ok=True)
log = open("/tmp/gh_verify.log", "a", buffering=1)


def say(msg: str) -> None:
    print(msg, flush=True)
    log.write(msg + "\n")


def local_slice_sha(idx: int) -> str:
    h = hashlib.sha256()
    with open(SRC, "rb") as f:
        f.seek(idx * CHUNK)
        remain = CHUNK if idx < PARTS - 1 else os.path.getsize(SRC) - idx * CHUNK
        while remain > 0:
            b = f.read(min(1 << 22, remain))
            if not b:
                break
            h.update(b)
            remain -= len(b)
    return h.hexdigest()


def main() -> int:
    total_src = os.path.getsize(SRC)
    say(f"本地 {SRC} {total_src} B")
    ok = 0
    for i in range(PARTS):
        letter = chr(ord("a") + i)
        fn = f"{NAME}.part-{letter}"
        path = os.path.join(DL, fn)
        url = f"https://github.com/{REPO}/releases/download/{TAG}/{fn}"
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            r = subprocess.run(["curl", "-sL", "--retry", "3", "-o", path, url],
                               env={k: v for k, v in os.environ.items()
                                    if k.lower() not in ("https_proxy", "http_proxy", "all_proxy")})
            if r.returncode != 0:
                say(f"FAIL 下载 {fn} rc={r.returncode}")
                continue
        remote = hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.getsize(path) < (1 << 31) else ""
        if not remote:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""):
                    h.update(b)
            remote = h.hexdigest()
        local = local_slice_sha(i)
        sz = os.path.getsize(path)
        flag = "OK" if remote == local else "MISMATCH"
        if flag == "OK":
            ok += 1
        say(f"{flag} {fn} {sz} B sha={remote[:16]}…")
    say(f"分片通过 {ok}/{PARTS}")
    if ok == PARTS:
        h = hashlib.sha256()
        for i in range(PARTS):
            fn = f"{NAME}.part-{chr(ord('a')+i)}"
            with open(os.path.join(DL, fn), "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""):
                    h.update(b)
        joined = h.hexdigest()
        hs = hashlib.sha256()
        with open(SRC, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""):
                hs.update(b)
        say(f"拼回 SHA256 = {joined}")
        say(f"本地 SHA256 = {hs.hexdigest()}")
        say("整体一致 ✅" if joined == hs.hexdigest() else "整体不一致 ❌")
        return 0 if joined == hs.hexdigest() else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
