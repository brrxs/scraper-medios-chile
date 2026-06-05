Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run "cmd /c cd /d """ & root & """ && .venv\Scripts\streamlit run app.py", 0, False
