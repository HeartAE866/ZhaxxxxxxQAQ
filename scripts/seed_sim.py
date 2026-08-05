# -*- coding: utf-8 -*-
"""生成模拟用户数据：各类型事项、提醒、循环任务、跨时间分布（两个版本共用）。"""
import json
import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import core

FMT = core.FMT
now = core.now()


def iso(dt):
    return dt.strftime(FMT)


def mk(ty, title, **kw):
    it = core.new_item(ty, title, **kw)
    it["created"] = iso(now - timedelta(days=kw.pop("days_ago", 0)))
    return it


items = []

# ---- 工作记录（10 条，跨度 60 天）
for i, (d, t) in enumerate([
    (1, "撰写季度报告初稿"), (3, "评审代码 PR #42"), (5, "整理会议纪要"),
    (8, "客户需求调研"), (12, "修复登录超时 bug"), (15, "部署测试环境"),
    (20, "周报汇总"), (25, "数据库备份验证"), (30, "性能压测"), (45, "年度规划草稿"),
]):
    items.append(mk("record", t, days_ago=d, priority=["high", "mid", "low"][i % 3],
                    tags=["工作"] if i % 2 else ["工作", "重要"]))

# ---- 待办事项（12 条，不同截止时间：今天稍晚/明天/本周/下月/长期——全部在未来）
for i, (d, t, p) in enumerate([
    (0, "提交报销单", "high"), (0, "预约牙医", "mid"), (1, "给客户回邮件", "high"),
    (2, "更新简历", "low"), (3, "缴纳水电费", "mid"), (5, "采购办公用品", "mid"),
    (7, "健身三次", "low"), (10, "读完技术书籍", "mid"), (15, "规划旅行", "low"),
    (30, "续签合同", "high"), (60, "年度体检", "mid"), (90, "换新身份证", "low"),
]):
    dl = now + timedelta(days=d, hours=2 + i % 20, minutes=i * 7 % 60)  # 未来时间
    items.append(mk("todo", t, days_ago=max(0, 2 - i), priority=p,
                    deadline=iso(dl), remind_advance=[0, 5, 15][i % 3],
                    tags=["家庭"] if i % 4 == 0 else ["工作"]))

# ---- 循环任务（5 条：每天/每周/每月/每季/每年）
items.append(mk("recur", "每日站会", recur={"period": "day", "time": "09:30"}))
items.append(mk("recur", "每周团队例会", recur={"period": "week", "time": "15:00", "weekday": 1}))
items.append(mk("recur", "每月账单核对", recur={"period": "month", "time": "10:00", "monthday": 5}))
items.append(mk("recur", "每季度绩效自评", recur={"period": "quarter", "time": "17:00", "monthday": 20}))
items.append(mk("recur", "年度设备盘点", recur={"period": "year", "time": "14:00", "month": 12, "monthday": 25}))

# ---- 提醒（5 条：全部未来时间）
for i, (d, t) in enumerate([
    (1, 9), (1, 15), (2, 18), (4, 12), (8, 17),
]):
    rt = now + timedelta(days=d)
    rt = rt.replace(hour=t, minute=0, second=0, microsecond=0)
    items.append(mk("remind", f"提醒:{t}点", days_ago=0,
                    remind_time=iso(rt), remind_advance=10,
                    tags=["提醒"]))

# ---- 网址直达（5 条，仅当前版渲染，1.2.1 忽略未知类型）
for t, u in [("GitHub", "https://github.com"), ("文档", "https://docs.python.org"),
             ("知乎", "https://zhihu.com"), ("博客", "https://example.com/blog"),
             ("工具", "https://www.google.com")]:
    items.append(mk("link", t, url=u, bar_color="#4fc3f7"))

print(f"共 {len(items)} 条数据")
for it in items:
    print(f"  [{it['type']}] {it['title']}")

out = {"items": items}
root = r"C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ"
with open(os.path.join(root, "data", "data.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("已写入", os.path.join(root, "data", "data.json"))
