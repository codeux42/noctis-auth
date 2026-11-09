Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(folder)
sh.CurrentDirectory = root
' pyw ouvre l'interface de compilation sans console.
sh.Run "pyw -3 """ & folder & "\build_gui.py""", 0, False
