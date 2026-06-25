@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM ============================================================
REM  Douyin Live Monitor Launcher
REM  Target: 四川低空百事通 老郭
REM  URL: https://v.douyin.com/15okSWnYiYs/
REM ============================================================

set "MONITOR_DIR=D:\mimocod\douyin_monitor"
set "SCRIPT_DIR=%~dp0"
set "DOUYIN_MONITOR_DIR=%MONITOR_DIR%"

if not exist "%MONITOR_DIR%" mkdir "%MONITOR_DIR%"
if not exist "%MONITOR_DIR%\logs" mkdir "%MONITOR_DIR%\logs"
if not exist "%MONITOR_DIR%\transcripts" mkdir "%MONITOR_DIR%\transcripts"

cd /d "%SCRIPT_DIR%"

echo.
echo ========================================
echo   抖音直播监控 - 四川低空百事通 老郭
echo ========================================
echo 输出目录: %MONITOR_DIR%
echo.

REM Check if monitor already running
if exist "%MONITOR_DIR%\monitor.pid" (
    for /f "tokens=2 delims=:," %%a in ('findstr /i "pid" "%MONITOR_DIR%\monitor.pid" 2^>nul') do (
        set "EXISTING_PID=%%a"
        set "EXISTING_PID=!EXISTING_PID:"=!"
        set "EXISTING_PID=!EXISTING_PID: =!"
    )
    if defined EXISTING_PID (
        tasklist /FI "PID eq !EXISTING_PID!" 2>nul | findstr /i "!EXISTING_PID!" >nul
        if not errorlevel 1 (
            echo [信息] 监控已在运行 PID=!EXISTING_PID!
            goto SHOW_STATUS
        )
    )
)

echo [启动] 后台启动 monitor.py ...
start "" /B pythonw "%SCRIPT_DIR%monitor.py" --daemon --output "%MONITOR_DIR%" --url "https://v.douyin.com/15okSWnYiYs/" --streamer "四川低空百事通 老郭"

timeout /t 3 /nobreak >nul

:SHOW_STATUS
echo.
python "%SCRIPT_DIR%monitor.py" --status --output "%MONITOR_DIR%"
echo.
echo 日志文件: %MONITOR_DIR%\logs\monitor.log
echo 状态文件: %MONITOR_DIR%\monitor_status.json
echo 会议纪要: %MONITOR_DIR%\meeting_minutes.md
echo.
echo 提示:
echo   - 停止监控: taskkill /F /PID ^<monitor.pid 中的 PID^>
echo   - 手动摘要: python summarizer.py
echo   - 单次检查: python monitor.py --once --output "%MONITOR_DIR%"
echo.
pause
