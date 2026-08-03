@echo off
rem ZhaxxxxxxQAQ 手动启动（带控制台，可看调试输出）
rem 虚拟环境位于源码目录上一级的 Temp\opencode\venv
cd /d %~dp0
"%~dp0venv\Scripts\python.exe" "%~dp0app\main.py"
pause
