Option Explicit
Dim shell, files, root, launcher, shortcutPath, shortcut
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
launcher = files.BuildPath(root, "jugar.vbs")
If Not files.FileExists(launcher) Then
    MsgBox "No se encontro jugar.vbs. Extrae todos los archivos del juego antes de continuar.", vbExclamation, "Juego PID"
    WScript.Quit 1
End If
shortcutPath = files.BuildPath(shell.SpecialFolders("Desktop"), "Juego PID.lnk")
On Error Resume Next
Set shortcut = shell.CreateShortcut(shortcutPath)
shortcut.TargetPath = files.BuildPath(files.GetSpecialFolder(0), "System32\wscript.exe")
shortcut.Arguments = Chr(34) & launcher & Chr(34)
shortcut.WorkingDirectory = root
shortcut.Description = "Juego PID en pantalla completa y sin consola"
shortcut.IconLocation = files.BuildPath(files.GetSpecialFolder(0), "System32\shell32.dll") & ",25"
shortcut.Save
If Err.Number <> 0 Then
    MsgBox "No se pudo crear el acceso directo: " & Err.Description, vbExclamation, "Juego PID"
    WScript.Quit 1
End If
On Error GoTo 0
If Not WScript.Arguments.Named.Exists("silencioso") Then
    MsgBox "Acceso directo Juego PID creado en el escritorio.", vbInformation, "Juego PID"
End If
