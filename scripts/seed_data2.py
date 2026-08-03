# -*- coding: utf-8 -*-
"""补充跨年份/月份的测试条目（2023-2026），覆盖多年度折叠展示。"""
import json
import uuid
from datetime import datetime, timedelta

P = r"D:\ZhaxxxxxxQAQ\data\data.json"
data = json.load(open(P, encoding="utf-8-sig"))
items = data["items"]


def ts(y, m, d, hh=10, mm=0):
    return datetime(y, m, d, hh, mm).strftime("%Y-%m-%d %H:%M")


def new(type_, title, **kw):
    it = {
        "id": uuid.uuid4().hex[:12],
        "type": type_, "title": title,
        "created": kw.pop("created", ts(2026, 8, 3)),
        "priority": kw.pop("priority", "mid"),
        "tags": kw.pop("tags", []),
        "folder": kw.pop("folder", None),
        "folder_rule": kw.pop("folder_rule", None),
        "order": kw.pop("order", 0),
        "deadline": kw.pop("deadline", None),
        "remind_advance": kw.pop("remind_advance", None),
        "remind_time": kw.pop("remind_time", None),
        "notified_for": kw.pop("notified_for", None),
        "done": kw.pop("done", False),
        "notified": False,
        "recur": kw.pop("recur", None),
        "completed_instances": kw.pop("completed_instances", []),
        "url": kw.pop("url", None),
        "bar_color": kw.pop("bar_color", None),
    }
    it.update(kw)
    return it


# ---------------- 2025 年 ----------------
items.append(new("todo", "年度总结初稿", deadline=ts(2025, 12, 31, 18),
                 priority="high", tags=["总结"], created=ts(2025, 12, 5)))
items.append(new("todo", "年会筹备", done=True, priority="low", tags=["活动"],
                 created=ts(2025, 12, 10)))
items.append(new("record", "上线 v1.1 版本", done=True, created=ts(2025, 12, 8)))
items.append(new("record", "年会节目彩排", done=True, created=ts(2025, 12, 20)))
items.append(new("todo", "秋季大扫除", done=True, priority="low",
                 created=ts(2025, 9, 15)))
items.append(new("record", "整理秋季项目资料", done=True, created=ts(2025, 9, 12)))
items.append(new("record", "客户演示与复盘", done=True, created=ts(2025, 6, 18)))
items.append(new("todo", "年中规划评审", deadline=ts(2025, 6, 30, 17),
                 priority="high", tags=["规划"], created=ts(2025, 6, 2)))
items.append(new("record", "春季新品发布支持", done=True, created=ts(2025, 3, 20)))

# ---------------- 2024 年 ----------------
items.append(new("record", "双十一活动保障", done=True, created=ts(2024, 11, 11)))
items.append(new("todo", "双十一复盘报告", done=True, priority="low", tags=["活动"],
                 created=ts(2024, 11, 15)))
items.append(new("record", "搬迁新办公室", done=True, created=ts(2024, 8, 6)))
items.append(new("todo", "夏季空调维护", done=True, priority="low", tags=["杂务"],
                 created=ts(2024, 8, 2)))

# ---------------- 2023 年 ----------------
items.append(new("record", "第一次年会筹备", done=True, created=ts(2023, 12, 15)))
items.append(new("record", "入职培训完成", done=True, created=ts(2023, 12, 1)))
items.append(new("record", "年度体检", done=True, created=ts(2023, 6, 10)))

# ---------------- 2026 年上半年 ----------------
items.append(new("record", "春节假期归来整理", done=True, created=ts(2026, 1, 5)))
items.append(new("todo", "新年目标拆解", deadline=ts(2026, 1, 31, 23),
                 priority="high", tags=["规划"], created=ts(2026, 1, 6)))
items.append(new("record", "春季户外团建", done=True, created=ts(2026, 4, 18)))

# ---------------- 跨年历史：循环任务完成记录 ----------------
items.append(new("recur", "每月读书打卡", recur={"period": "month", "time": "21:00", "monthday": 5},
                 completed_instances=[ts(2025, 11, 5), ts(2025, 12, 5),
                                      ts(2026, 1, 5), ts(2026, 2, 5),
                                      ts(2026, 3, 5), ts(2026, 4, 5),
                                      ts(2026, 5, 5), ts(2026, 6, 5),
                                      ts(2026, 7, 5)]))

# ---------------- 跨年网址（旧创建时间） ----------------
items.append(new("link", "GitHub 首页", url="https://github.com",
                 bar_color="#4fc3f7", created=ts(2025, 1, 3)))

# ---------------- 历史提醒（已完成） ----------------
items.append(new("remind", "缴纳水电费", done=True, remind_time=ts(2025, 10, 1, 9),
                 notified_for=ts(2025, 10, 1, 9)))
items.append(new("remind", "母亲节祝福", done=True, remind_time=ts(2026, 5, 10, 8),
                 notified_for=ts(2026, 5, 10, 8)))

json.dump(data, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"total items: {len(items)}")
