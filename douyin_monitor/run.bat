@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
) else (
  echo [WARN] 未检测到 .venv，使用系统 Python。建议先运行 install_deps.bat
)

if exist "DONE.txt" del /f /q "DONE.txt"

echo 启动 Douyin 直播监控 monitor.py ...
python monitor.py

if errorlevel 1 (
  echo [ERROR] monitor.py 异常退出，错误码 %errorlevel%
  pause
  exit /b %errorlevel%
)

pause
