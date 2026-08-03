"""修复 1.3.0 测试数据的 ISO 时间格式（T 分隔 → 空格分隔）
背景：seed 脚本生成数据时 created/deadline/remind_time 用了 ISO 格式，
而 core.parse_dt 期望 "%Y-%m-%d %H:%M"（空格），导致所有条目落入今天分组。
注意：completed_instances 保持 ISO 格式（循环任务内部比较用）。
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "data", "data.json")

d = json.load(open(p, encoding="utf-8-sig"))
TIME_KEYS = ("created", "deadline", "remind_time", "notified_for")
n = 0
for it in d["items"]:
    for k in TIME_KEYS:
        v = it.get(k)
        if isinstance(v, str) and "T" in v:
            it[k] = v.replace("T", " ")
            n += 1
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"转换字段数: {n}")

ok = 0
for it in d["items"]:
    c = it.get("created", "")
    try:
        datetime.datetime.strptime(c, "%Y-%m-%d %H:%M")
        ok += 1
    except Exception:
        pass
print(f"created 可解析: {ok}/{len(d['items'])}")
