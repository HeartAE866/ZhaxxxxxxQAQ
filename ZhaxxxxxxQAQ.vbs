' ZhaxxxxxxQAQ silent launcher (no console window). Autostart points here.
' 虚拟环境位于源码目录上一级的 Temp\opencode\venv
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
venv = root & "\venv\Scripts\pythonw.exe"
shell.CurrentDirectory = root
shell.Run """" & venv & """ """ & root & "\app\main.py""", 0, False
