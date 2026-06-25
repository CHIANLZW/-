@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo === Douyin Live Monitor (Audio + Transcription) ===

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

if "%DOUYIN_ROOM_ID%"=="" (
    if "%~1"=="" (
        echo.
        echo Usage: run.bat ^<room_id^>
        echo   room_id = number from https://live.douyin.com/^<room_id^>
        echo.
        echo Optional env vars:
        echo   DOUYIN_ROOM_ID          - live room id
        echo   DOUYIN_OUTPUT_DIR       - default D:\mimocod\douyin_monitor
        echo   OPENAI_API_KEY          - for meeting minutes summarization
        echo   WHISPER_MODEL           - tiny or base ^(default base^)
        echo.
        set /p ROOM_ID="Enter Douyin room ID: "
    ) else (
        set ROOM_ID=%~1
    )
) else (
    set ROOM_ID=%DOUYIN_ROOM_ID%
)

if "!ROOM_ID!"=="" (
    echo Error: room ID required.
    pause
    exit /b 1
)

echo.
echo Output directory: D:\mimocod\douyin_monitor
echo Room ID: !ROOM_ID!
echo.
echo Press Ctrl+C to stop monitoring.
echo.

python monitor.py !ROOM_ID!

pause
