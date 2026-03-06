Set shell = CreateObject("Shell.Application")
shell.ShellExecute "pythonw.exe", """" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\main.py""", "", "runas", 0
