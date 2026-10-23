# 发布记录

## v1.0 — 2026-10-23

| 项 | 结果 | 取证方式 |
| --- | --- | --- |
| 发布物 | `sage-a1.5-q4km-abl4.0.gguf`，27,557,177,568 B（融合版，非官方底座） | 本地 `stat` + 远端 size 对表 |
| GitHub | Release `v1.0`，15 片 `part-a…part-o` + `mmproj` + `SHA256SUMS`，共 17 资产 | `gh release view` + 页面 `expanded_assets` |
| GitHub 校验 | 逐片 SHA256 15/15 与本地切片一致；匿名 Range GET `part-a` 首 1 MB / 末 1 KB `HTTP 206` 且字节一致 | `.digest` 比对 + `curl -r` |
| HF | `amy-sage/sage-a1.5`，权重 27,557,177,568 B（与本地**逐字节同尺寸**） | HF API `/tree/main` |
| HF 抽检 | 头 100 MB、尾 100 MB 经 `Range` 拉回，与本地对应区间 SHA256 **完全一致**（head `e9444f19…`、tail `8b7e4cf1…`），首 4 字节 `GGUF` | `curl -r` + 本地切片比对 |
| X | https://x.com/AmyLinlbm0/status/2113660352764461453 | 登录态页面复核；两个 `t.co` 分别解析回 GitHub / HF |
| 同机 A/B | Sage 46.5 / 45.5 tok/s vs Qwen3.8-27B 6.4 / 5.4 tok/s（约 7–8.4×） | `scripts/agent_speed_bench.py` |
| Agent 实测 | 4 步依赖工具链 4/4；6 轮状态链 6/6；原生 `tool_calls` | 同上 + `scripts/multiturn_chain.py` |

备注：首条推文经 `execCommand` 注入后 GitHub 链接被断行、未生成短链，已删除重发；旧的那条 20.2 GB / ~50 tok/s 口径的推文同样作废删除。
