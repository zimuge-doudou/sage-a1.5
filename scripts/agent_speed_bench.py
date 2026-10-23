#!/usr/bin/env python3
"""同机 A/B：Sage-A1.5（融合版）vs Qwen3.8-27B —— 速度 + 真实多轮 agent 执行力。

用法: python3 agent_speed_bench.py <port> <label>

三轮测试，同一套提示词两端都跑：
  1. speed   —— 320 token 生成，取 llama.cpp timings（decode / prefill tok/s）
  2. agent   —— 4 步依赖任务，每步模型自己决定调 shell、读输出、再继续（每步最多 4 个 assistant 回合）
  3. multiturn —— 6 轮纯对话依赖链（每轮答案依赖上一轮），看跨轮记忆是否掉线
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8090"
LABEL = sys.argv[2] if len(sys.argv) > 2 else "model"
BASE = f"http://127.0.0.1:{PORT}"


def chat(messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 320) -> dict:
    payload: dict = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def speed() -> dict:
    prompt = ("Write a Python function that merges two sorted lists without using sort(), "
              "then a second function that does an in-place heapify.")
    t0 = time.time()
    r = chat([{"role": "user", "content": prompt}], max_tokens=320)
    wall = time.time() - t0
    t = r.get("timings") or {}
    return {"wall_s": round(wall, 2),
            "out_tokens": t.get("predicted_n", 0),
            "decode_tok_s": round(t.get("predicted_per_second", 0.0), 1),
            "prefill_tok_s": round(t.get("prompt_per_second", 0.0), 1)}


TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Run one shell command in the working directory and return stdout.",
        "parameters": {"type": "object",
                       "properties": {"cmd": {"type": "string", "description": "Command line"}},
                       "required": ["cmd"]},
    },
}]

STEPS = [
    ("建 round1.txt，内容写 17", "round1.txt"),
    ("读 round1.txt，值乘 3，写进 round2.txt", "round2.txt"),
    ("读 round2.txt，判断是否质数，结论写进 round3.txt", "round3.txt"),
    ("读 round1..3.txt，拼成一行写入 final.txt 并打印", "final.txt"),
]


def agent_rounds() -> dict:
    workdir = tempfile.mkdtemp(prefix="agentbench_")
    messages = [{"role": "system",
                 "content": (f"You are an autonomous agent with the run_shell tool. Working directory: "
                             f"{workdir}. For each instruction, call run_shell (one command), read its "
                             f"output, and keep calling until the file exists — then reply DONE.")}]
    per_step, ok, t_all = [], 0, time.time()
    for step, (instr, artifact) in enumerate(STEPS, 1):
        messages.append({"role": "user", "content": instr})
        turns, made, last = 0, False, ""
        while turns < 4:
            turns += 1
            r = chat(messages, tools=TOOLS, max_tokens=400)
            msg = r["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            if not calls:
                last = (msg.get("content") or "")[:120]
                messages.append({"role": "assistant", "content": msg.get("content") or ""
                                 or "(no content)"})
                made = os.path.exists(os.path.join(workdir, artifact))
                break
            messages.append({"role": "assistant", "content": msg.get("content"),
                             "tool_calls": calls})
            for c in calls:
                try:
                    cmd = json.loads(c["function"]["arguments"]).get("cmd", "")
                except Exception:
                    cmd = ""
                p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True,
                                   timeout=30, cwd=workdir) if cmd else None
                out = ((p.stdout or "") + (p.stderr or ""))[:400] if p else "no cmd parsed"
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                last = (last + " | cmd=" + cmd[:60] + " out=" + out.strip()[:60])[-160:]
            made = os.path.exists(os.path.join(workdir, artifact))
            if made:
                break
        ok += made
        per_step.append({"step": step, "turns": turns, "file_ok": made, "tail": last.strip()[:150]})
    return {"steps_ok": ok, "steps_total": len(STEPS),
            "wall_s": round(time.time() - t_all, 1), "detail": per_step}


def multiturn() -> dict:
    """6 轮依赖链：答错即链条断，检验跨轮状态是否稳定。"""
    msgs = [{"role": "system", "content": "Answer with the number only, nothing else."}]
    vals, ok = [], 0
    seed = 7
    for i in range(6):
        if i == 0:
            q = f"Start with {seed}. Multiply by 3. Answer the number."
            expect = seed * 3
        else:
            q = "Take the previous answer, add 11, answer the number."
            expect = vals[-1] + 11 if vals and vals[-1] is not None else None
        msgs.append({"role": "user", "content": q})
        r = chat(msgs, max_tokens=24)
        txt = (r["choices"][0]["message"].get("content") or "").strip()
        num = None
        for tok in txt.replace(",", " ").split():
            t = "".join(ch for ch in tok if ch.isdigit() or ch == "-")
            if t not in ("", "-"):
                num = int(t)
                break
        good = expect is not None and num == expect
        ok += good
        vals.append(num)
        msgs.append({"role": "assistant", "content": txt})
    return {"correct": ok, "rounds": 6, "values": vals}


def main() -> int:
    print(f"### {LABEL} (:{PORT})", flush=True)
    s = speed(); print("速度:", json.dumps(s), flush=True)
    a = agent_rounds(); print("agent:", json.dumps({k: v for k, v in a.items() if k != "detail"}), flush=True)
    for d in a["detail"]:
        print("   ", json.dumps(d, ensure_ascii=False), flush=True)
    m = multiturn(); print("多轮链:", json.dumps(m), flush=True)
    json.dump({"label": LABEL, "port": PORT, "speed": s, "agent": a, "multiturn": m},
              open(f"/tmp/bench_{LABEL}.json", "w"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
