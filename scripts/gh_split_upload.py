#!/usr/bin/env python3
"""把融合后 GGUF 切片并上传到 GitHub Release v1.0，边传边删以节省磁盘。

用法: python3 gh_split_upload.py
"""
import os
import subprocess
import sys
import threading
import queue
import time

SRC = "/Users/liuqiang002/.hermes/models/sage-a1.5-q4km-abl4.0.gguf"
STAGE = "/tmp/gparts"
REPO_DIR = "/Users/liuqiang002/projects/sage-a1.5"
TAG = "v1.0"
CHUNK = 1800 * 1024 * 1024          # 1.8 GiB，低于 GitHub 2 GiB 限制
MAX_INFLIGHT = 3

os.makedirs(STAGE, exist_ok=True)
size = os.path.getsize(SRC)
n = (size + CHUNK - 1) // CHUNK
print(f"src={size} chunk={CHUNK} parts={n}", flush=True)

suffix = None


def name_for(i: int) -> str:
    letters = ""
    i += 1
    while i > 0:
        i, r = divmod(i - 1, 26)
        letters = chr(ord("a") + r) + letters
    return f"sage-a1.5-q4km-abl4.0.gguf.part-{letters}"


work = queue.Queue()
for i in range(n):
    work.put(i)

results = {}
lock = threading.Lock()
inflight = threading.Semaphore(MAX_INFLIGHT)


def worker():
    while True:
        try:
            i = work.get_nowait()
        except queue.Empty:
            return
        with inflight:
            path = os.path.join(STAGE, name_for(i))
            off = i * CHUNK
            length = min(CHUNK, size - off)
            t0 = time.time()
            with open(SRC, "rb") as f, open(path, "wb") as out:
                f.seek(off)
                left = length
                while left > 0:
                    buf = f.read(min(8 << 20, left))
                    if not buf:
                        break
                    out.write(buf)
                    left -= len(buf)
            r = subprocess.run(["gh", "release", "upload", TAG, path, "--clobber"],
                               cwd=REPO_DIR, capture_output=True, text=True)
            ok = r.returncode == 0
            dt = time.time() - t0
            with lock:
                results[i] = ok
                print(f"{time.strftime('%H:%M:%S')} {'OK' if ok else 'FAIL'} {os.path.basename(path)} "
                      f"{length/1e6:.0f}MB {dt:.0f}s {length/1e6/dt:.2f}MB/s"
                      + ("" if ok else " err=" + (r.stderr or "")[-160:].replace("\n", " ")), flush=True)
            os.remove(path)


threads = [threading.Thread(target=worker, daemon=True) for _ in range(MAX_INFLIGHT)]
for t in threads:
    t.start()
for t in threads:
    t.join()

bad = [k for k, v in results.items() if not v]
print(f"DONE ok={len(results)-len(bad)}/{n} failed={sorted(bad)}", flush=True)
sys.exit(1 if bad else 0)
