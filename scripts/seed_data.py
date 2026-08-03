# -*- coding: utf-8 -*-
"""为桌面应用批量填充测试条目：覆盖待办/已完成/记录/循环/提醒/网址全部功能。"""
import json
import uuid
from datetime import datetime, timedelta

P = r"D:\ZhaxxxxxxQAQ\data\data.json"
data = json.load(open(P, encoding="utf-8-sig"))
items = data["items"]
now = datetime.now()


def ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def new(type_, title, **kw):
    it = {
        "id": uuid.uuid4().hex[:12],
        "type": type_, "title": title,
        "created": kw.pop("created", ts(now)),
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


# ---------------- 待办（未完成：今天/明天/逾期/无期限，全部用上） ----------------
items.append(new("todo", "撰写季度工作总结", deadline=ts(now + timedelta(hours=2)),
                 priority="high", tags=["工作", "总结"]))
items.append(new("todo", "准备明日晨会材料", deadline=ts(now + timedelta(days=1, hours=-2)),
                 priority="high", tags=["会议"]))
items.append(new("todo", "学习 Qt 拖拽排序原理", tags=["学习"]))
items.append(new("todo", "整理桌面文件", priority="low", tags=["杂务"]))
items.append(new("todo", "更新周报模板", deadline=ts(now - timedelta(days=64)),
                 priority="high", tags=["周报"], created=ts(now - timedelta(days=65))))
items.append(new("todo", "报销上月发票", deadline=ts(now - timedelta(days=21)),
                 priority="high", tags=["财务"], created=ts(now - timedelta(days=30))))

# ---------------- 待办（已完成） ----------------
items.append(new("todo", "完成 v1.3.0 版本发布", done=True,
                 deadline=ts(now - timedelta(days=1)),
                 priority="low", tags=["版本"], created=ts(now - timedelta(days=2))))
items.append(new("todo", "修复 Explorer 崩溃恢复", done=True, priority="low",
                 tags=["稳定"], created=ts(now - timedelta(days=3))))
items.append(new("todo", "删除开机动画", done=True, priority="low",
                 tags=["优化"], created=ts(now - timedelta(days=4))))
items.append(new("todo", "实现滚轮防误触", done=True, priority="low",
                 tags=["优化"], created=ts(now - timedelta(days=5))))
items.append(new("todo", "实现网址直达功能", done=True, priority="low",
                 tags=["新功能"], created=ts(now - timedelta(days=6))))

# ---------------- 工作记录（跨 5/6/7/8 月，展示年月折叠） ----------------
items.append(new("record", "实现网址直达 + 拖拽排序", done=True,
                 created=ts(now)))
items.append(new("record", "测试滚轮防误触与开机动画移除", done=True,
                 created=ts(now - timedelta(days=1))))
items.append(new("record", "修复桌面嵌入崩溃恢复", done=True,
                 created=ts(now - timedelta(days=9))))
items.append(new("record", "优化启动速度与内存占用", done=True,
                 created=ts(now - timedelta(days=40))))
items.append(new("record", "完成 v1.2 打磨与回归", done=True,
                 created=ts(now - timedelta(days=75))))

# ---------------- 循环任务（每天/每周/每月/每季/每年 + 完成历史） ----------------
items.append(new("recur", "每日晨报", recur={"period": "day", "time": "09:00"},
                 tags=["日报"],
                 completed_instances=[ts(now - timedelta(days=1)),
                                      ts(now - timedelta(days=2)),
                                      ts(now - timedelta(days=3))]))
items.append(new("recur", "每日午休散步", recur={"period": "day", "time": "13:00"}))
items.append(new("recur", "每周周报", recur={"period": "week", "time": "17:00", "weekday": 4},
                 tags=["周报"]))
items.append(new("recur", "每月家庭聚餐", recur={"period": "month", "time": "12:00", "monthday": 1}))
items.append(new("recur", "每季度备份数据", recur={"period": "quarter", "time": "10:00", "monthday": 1}))
items.append(new("recur", "每年体检", recur={"period": "year", "time": "09:00", "month": 6, "monthday": 15}))

# ---------------- 提醒（未来/过去/已完成） ----------------
items.append(new("remind", "今天下午开会", remind_time=ts(now + timedelta(hours=2)),
                 remind_advance=15))
items.append(new("remind", "明早取快递", remind_time=ts(now + timedelta(days=1, hours=-3)),
                 remind_advance=30))
items.append(new("remind", "周末家庭聚会", remind_time=ts(now + timedelta(days=2, hours=3)),
                 remind_advance=60))
items.append(new("remind", "交房租", done=True, remind_time=ts(now - timedelta(days=1)),
                 notified_for=ts(now - timedelta(days=1))))

# ---------------- 网址直达（多种颜色竖条） ----------------
items.append(new("link", "哔哩哔哩", url="https://www.bilibili.com",
                 bar_color="#ff5c6c"))
items.append(new("link", "知乎", url="https://www.zhihu.com",
                 bar_color="#4fc3f7"))
items.append(new("link", "百度", url="https://www.baidu.com",
                 bar_color="#7bd88f"))
items.append(new("link", "掘金", url="https://juejin.cn",
                 bar_color="#f06292"))
items.append(new("link", "Stack Overflow", url="https://stackoverflow.com",
                 bar_color="#ffb84d"))
items.append(new("link", "GitHub 开源项目", url="github.com", bar_color="#b39ddb"))

json.dump(data, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"total items: {len(items)}")
