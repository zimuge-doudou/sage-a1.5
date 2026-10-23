#!/usr/bin/env python3
"""6 轮依赖链记忆测试（修正版：给足 max_tokens，关思考，取最后一个数字）。

用法: python3 multiturn_chain.py <port> <label>
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

PORT = sys.argv[1]
LABEL = sys.argv[2]
BASE = f"http://127.0.0.1:{PORT}"


def chat(messages: list[dict], max_tokens: int = 220) -> dict:
    payload = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.0,
               "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer local"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


msgs = [{"role": "system",
         "content": "You are a calculator. Answer with one integer and nothing else."}]
vals: list[int | None] = []
ok = 0
for i in range(6):
    if i == 0:
        q, expect = "Multiply 7 by 3. Answer the integer.", 21
    else:
        q = "Take the previous answer, add 11. Answer the integer."
        expect = (vals[-1] + 11) if vals[-1] is not None else None
    msgs.append({"role": "user", "content": q})
    r = chat(msgs)
    txt = (r["choices"][0]["message"].get("content") or "").strip()
    nums = re.findall(r"-?\d+", txt.replace(",", ""))
    num = int(nums[-1]) if nums else None
    good = expect is not None and num == expect
    ok += good
    vals.append(num)
    msgs.append({"role": "assistant", "content": txt or "(empty)"})
    print(f"  r{i+1}: expect={expect} got={num} {'OK' if good else 'MISS'} raw={txt[:40]!r}")

print(json.dumps({"label": LABEL, "correct": ok, "rounds": 6, "values": vals}))
json.dump({"label": LABEL, "correct": ok, "values": vals}, open(f"/tmp/chain_{LABEL}.json", "w"))
