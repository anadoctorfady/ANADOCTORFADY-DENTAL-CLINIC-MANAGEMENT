' Create a Desktop shortcut for ANADOCTORFADY with the clinic logo icon.
' Usage: double-click this file (or run: cscript create_shortcut.vbs)
'   after building the EXE with installer\build_exe.bat (or the x86/x64 one).
' PyInstaller onefile CANNOT create shortcuts itself, so this script does it.
' Target: installer\dist\ANADOCTORFADY.exe (falls back to the _x86 / _x64 copy).
' Icon:  assets\app.ico if present, otherwise the EXE itself (it embeds
'   the same .ico, so the shortcut still shows the gold-tooth logo).
Option Explicit
Dim fso, shell, scriptDir, distDir, exePath, icoPath, desk, link
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
distDir = fso.BuildPath(scriptDir, "dist")
exePath = fso.BuildPath(distDir, "ANADOCTORFADY.exe")
If Not fso.FileExists(exePath) Then exePath = fso.BuildPath(distDir, "ANADOCTORFADY_x86.exe")
If Not fso.FileExists(exePath) Then exePath = fso.BuildPath(distDir, "ANADOCTORFADY_x64.exe")
If Not fso.FileExists(exePath) Then
  MsgBox "EXE not found in " & distDir & vbCrLf & _
    "Build it first with installer\build_exe.bat", vbExclamation, "ANADOCTORFADY"
  WScript.Quit 1
End If
icoPath = fso.BuildPath(fso.GetParentFolderName(scriptDir), "assets\app.ico")
If Not fso.FileExists(icoPath) Then icoPath = exePath ' EXE embeds the same icon
desk = shell.SpecialFolders("Desktop")
Set link = shell.CreateShortcut(fso.BuildPath(desk, "ANADOCTORFADY.lnk"))
link.TargetPath = exePath
link.WorkingDirectory = distDir
link.Description = "ANADOCTORFADY - Dental Clinic"
link.IconLocation = icoPath & ",0"
link.Save
MsgBox "Desktop shortcut created: ANADOCTORFADY.lnk", vbInformation, "ANADOCTORFADY"
