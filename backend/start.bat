@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] venv not found. Run setup.bat first.
    pause & exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo  Folio Backend starting on http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo  Press Ctrl+C to stop
echo.

:: ✅ Run directly — NO --reload flag (causes Windows crash)
python main.py
pause