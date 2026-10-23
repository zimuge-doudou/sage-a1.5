#!/usr/bin/env python3
"""发布守护：确保 HF 单文件上传与 GitHub 分片上传各有一个脱离会话的进程在跑。

设计要点：
- 子进程用 start_new_session=True 启，脱离 Hermes 会话的进程组，不会被会话回收带死；
- 幂等：已经在跑就不重复启；已完成就跳过；
- 供 cron 每 10 分钟调用一次，也可手动跑。
用法: python3 publish_daemon.py [--status]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

SRC = "/Users/liuqiang002/.hermes/models/sage-a1.5-q4km-abl4.0.gguf"
HF_DIR = "/tmp/hf2"
GH_SCRIPT = "/Users/liuqiang002/projects/sage-a1.5/scripts/gh_split_upload.py"
GH_REPO_DIR = "/Users/liuqiang002/projects/sage-a1.5"
REPO = "amy-sage/sage-a1.5"
TOKEN_FILE = "/tmp/hf_tok_raw.txt"
LOG_DIR = "/tmp"
PROXY = "http://127.0.0.1:10809"
PARTS = 15  # 26 GB / 1.8 GiB


def running(pattern: str) -> bool:
    """pgrep -f 是否命中（排除自身）。"""
    out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout.split()
    return any(int(p) != os.getpid() for p in out)


def hf_remote_size() -> int | None:
    """HF 上目标文件的大小（字节）；不存在返回 0，查询失败返回 None。"""
    try:
        tok = open(TOKEN_FILE).read().strip()
    except OSError:
        return None
    req = urllib.request.Request(f"https://huggingface.co/api/models/{REPO}/tree/main",
                                 headers={"Authorization": f"Bearer {tok}"})
    proxy = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    opener = urllib.request.build_opener(proxy)
    try:
        data = json.loads(opener.open(req, timeout=40).read())
    except Exception:
        return None
    for f in data:
        if f.get("path", "").endswith("abl4.0.gguf"):
            return int(f.get("size") or 0)
    return 0


def gh_assets() -> int | None:
    """Release 上 part-* 资产数量；查询失败返回 None。"""
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    r = subprocess.run(["gh", "release", "view", "v1.0", "--json", "assets",
                        "-q", '[.assets[] | select(.name | contains("abl4.0"))] | length'],
                       cwd=GH_REPO_DIR, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip() or 0)
    except ValueError:
        return None


def start_hf() -> str:
    env = dict(os.environ)
    env.update({"https_proxy": PROXY, "http_proxy": PROXY,
                "HF_XET_HIGH_PERFORMANCE": "1"})
    log = open(f"{LOG_DIR}/hf_up3.log", "ab")
    p = subprocess.Popen(["hf", "upload", REPO, HF_DIR, "--repo-type", "model"],
                         cwd=HF_DIR, env=env, stdout=log, stderr=log,
                         start_new_session=True)
    return f"HF 启动 pid={p.pid}"


def start_gh() -> str:
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    log = open(f"{LOG_DIR}/gh_up2.log", "ab")
    p = subprocess.Popen([sys.executable, "-u", GH_SCRIPT], cwd=GH_REPO_DIR, env=env,
                         stdout=log, stderr=log, start_new_session=True)
    return f"GitHub 启动 pid={p.pid}"


def main() -> int:
    status_only = "--status" in sys.argv
    quiet = "--quiet" in sys.argv
    want = os.path.getsize(SRC)
    hf_size = hf_remote_size()
    parts = gh_assets()
    lines = [f"本地融合文件 {want/1e9:.2f} GB",
             f"HF 远端 {('查询失败' if hf_size is None else f'{hf_size/1e9:.2f} GB')}",
             f"GitHub part-* {('查询失败' if parts is None else f'{parts}/{PARTS}')}"]

    hf_done = hf_size is not None and hf_size > want * 0.98
    gh_done = parts is not None and parts >= PARTS
    events: list[str] = []

    if not status_only:
        # 串行策略：HF 的 Xet 在带宽争用时必退避/停滞 ⇒ GitHub 未传完前不启 HF
        if not hf_done and gh_done:
            if running("hf upload amy-sage"):
                lines.append("HF 已在跑")
            else:
                lines.append(start_hf())
                events.append("HF 重启")
        elif not hf_done:
            lines.append("HF 等 GitHub 传完再启（避免带宽争用导致 Xet 停滞）")
        else:
            lines.append("HF 已完成，跳过")
            events.append(f"HF 完成 {hf_size/1e9:.2f} GB")
        if not gh_done:
            if running("gh_split_upload.py"):
                lines.append("GitHub 已在跑")
            else:
                lines.append(start_gh())
                events.append("GitHub 重启")
        else:
            lines.append("GitHub 已完成，跳过")
            events.append(f"GitHub 完成 {parts} 片")
    if quiet and not events:
        return 0
    print("\n".join(lines), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
