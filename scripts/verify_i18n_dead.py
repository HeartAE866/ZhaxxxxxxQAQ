# -*- coding: utf-8 -*-
"""精确验证 i18n 死键：键文本在整个 app 目录出现次数（含单/双引号 tr、f-string 等）。"""
import ast
import os
import re
import sys

root = os.path.join(os.path.dirname(__file__), "..", "app")

texts = {}
for f in os.listdir(root):
    if f.endswith(".py"):
        texts[f] = open(os.path.join(root, f), encoding="utf-8").read()

i18n_src = texts["i18n.py"]
tree = ast.parse(i18n_src)
keys = []
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 \
            and isinstance(node.targets[0], ast.Name) \
            and node.targets[0].id == "_TRANSLATIONS":
        for k, v in zip(node.value.keys, node.value.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.append(k.value)

def appears(key):
    n = 0
    for fname, text in texts.items():
        if fname == "i18n.py":
            continue
        n += text.count(key)
    return n

dead = [(k, appears(k)) for k in keys if appears(k) == 0]
print(f"总键数: {len(keys)}, 全库零出现死键: {len(dead)}")
for k, n in dead:
    print("DEAD:", repr(k))
