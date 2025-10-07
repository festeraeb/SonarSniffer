@echo off
echo CESAROPS Environment Launcher
call conda activate cesarops
cd /d "%~dp0"
echo Environment: cesarops activated
echo Directory: %CD%
echo.
echo Type: python sarops.py to run CESAROPS
cmd /k