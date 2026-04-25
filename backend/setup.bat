@echo off
echo ============================================
echo   Folio PDF Chatbot - Windows Setup
echo ============================================
cd /d "%~dp0"

:: Check Python 3.11
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.11 not found.
    echo.
    echo Please download and install Python 3.11.9 from:
    echo https://www.python.org/downloads/release/python-3119/
    echo.
    echo  - Click "Windows installer (64-bit)"
    echo  - Check "Add Python to PATH"
    echo  - Check "Install for all users"
    echo.
    echo After installing, close this window and run setup.bat again.
    pause & exit /b 1
)

echo [OK] Python 3.11 found.

echo Removing old venv if exists...
if exist venv rmdir /s /q venv

echo Creating fresh venv with Python 3.11...
py -3.11 -m venv venv
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip --quiet

echo Installing packages...
pip install ^
  "fastapi==0.103.2" ^
  "uvicorn[standard]==0.23.2" ^
  "python-multipart==0.0.6" ^
  "motor==3.3.2" ^
  "pymongo==4.6.0" ^
  "pdfplumber==0.10.3" ^
  "PyPDF2==3.0.1" ^
  "python-jose[cryptography]==3.3.0" ^
  "bcrypt==4.0.1" ^
  "passlib==1.7.4" ^
  "httpx==0.25.2" ^
  "python-dotenv==1.0.0" ^
  "pydantic==2.3.0" ^
  "pydantic-settings==2.0.3" ^
  "aiofiles==23.2.1" ^
  "anyio==3.7.1"

if errorlevel 1 (
    echo [ERROR] Install failed. See errors above.
    pause & exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [INFO] Created .env from .env.example
    echo [ACTION] Open backend\.env and set your OPENROUTER_API_KEY
)

echo.
echo ============================================
echo  SUCCESS - run start.bat to launch server
echo ============================================
pause
