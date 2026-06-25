@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
echo ========================================
echo  Douyin Livestream Monitor - Install
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请先安装 Python 3.10+ 并勾选 "Add to PATH"。
  pause
  exit /b 1
)

python --version

if not exist ".venv" (
  echo 创建虚拟环境 .venv ...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel

echo 安装 Python 依赖 ...
pip install -r requirements.txt
if errorlevel 1 (
  echo [WARN] 常规安装失败，尝试 Windows PyAudio 备用方案 ...
  pip install pipwin==0.5.2
  pipwin install pyaudio
  pip install -r requirements.txt
)

if not exist "recordings" mkdir recordings
if not exist "logs" mkdir logs
if not exist "state" mkdir state
if not exist "output" mkdir output

echo.
echo 安装完成。下一步：
echo   1. 编辑 config.json（stream_url、streamer_name、openai_api_key 等）
echo   2. 双击 run.bat 启动监控
echo.
pause
