' ZhaxxxxxxQAQ silent launcher (no console window). Autostart points here.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
shell.Run """" & root & "\venv\Scripts\pythonw.exe"" """ & root & "\app\main.py""", 0, False
