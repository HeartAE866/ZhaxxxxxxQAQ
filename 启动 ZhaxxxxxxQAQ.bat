@echo off
rem ZhaxxxxxxQAQ 手动启动（带控制台，可看调试输出）
cd /d %~dp0
"%~dp0venv\Scripts\python.exe" "%~dp0app\main.py"
pause
