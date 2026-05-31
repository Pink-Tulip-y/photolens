@echo off
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $d = $ws.SpecialFolders('Desktop'); $s = $ws.CreateShortcut($d + '\PhotoLens.lnk'); $s.TargetPath = 'd:\VS Code\photo-scorer\启动PhotoLens.bat'; $s.WorkingDirectory = 'd:\VS Code\photo-scorer'; $s.Save(); Write-Host 'Done'"
echo 桌面快捷方式已创建！
pause
