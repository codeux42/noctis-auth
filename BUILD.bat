@echo off
cd /d "%~dp0"
wscript.exe //B //Nologo "%~dp0scripts\launch_build.vbs"
exit /b
