# -*- coding: utf-8 -*-
"""AST 扫描未使用的 import（简化版：检查 import 名是否在文件其他地方出现）。"""
import ast
import os
import sys

root = os.path.join(os.path.dirname(__file__), "..", "app")

for f in sorted(os.listdir(root)):
    if not f.endswith(".py"):
        continue
    path = os.path.join(root, f)
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            pass
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                used.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                used.add(a.asname or a.name.split(".")[0])
    unused = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                nm = a.asname or a.name.split(".")[0]
                # 统计真实使用次数（import 行本身不算）
                count = src.count(nm)
                if count <= 1:
                    unused.append(nm)
    if unused:
        print(f"{f}: 疑似未使用 import: {unused}")
