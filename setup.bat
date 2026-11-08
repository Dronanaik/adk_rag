@echo off
REM ==============================================================================
REM ADK Agentic RAG + Knowledge Graph — Automated Project Setup (Windows)
REM Usage:
REM   setup.bat             Set up Python .venv, install backend + frontend deps, create .env
REM   setup.bat --with-docs Also install MkDocs Material documentation dependencies
REM   setup.bat --start     Run setup and immediately launch Backend (8000) + Frontend (5173)
REM ==============================================================================

setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "WITH_DOCS=0"
set "AUTO_START=0"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--with-docs" set "WITH_DOCS=1"
if /i "%~1"=="--start" set "AUTO_START=1"
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--help" goto show_help
shift
goto parse_args

:show_help
echo Usage: setup.bat [--with-docs] [--start]
echo   --with-docs  Install MkDocs Material documentation packages
echo   --start      Launch FastAPI backend (port 8000) and Vite UI (port 5173) after setup
exit /b 0

:args_done
echo ======================================================================
echo   ADK Agentic RAG + Knowledge Graph — Environment Setup (v2.2.0)
echo ======================================================================
echo.

REM ------------------------------------------------------------------------------
REM 1. Verify Prerequisites (Python 3.10+, Node.js 18+, npm)
REM ------------------------------------------------------------------------------
echo [1/5] Checking system prerequisites...

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python 3.10+ is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo   [OK] Found %PYTHON_VER%

where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js ^(v18+^) is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo   [OK] Found Node.js %NODE_VER%

where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm is not installed or not in PATH.
    exit /b 1
)
for /f "tokens=*" %%i in ('npm -v') do set NPM_VER=%%i
echo   [OK] Found npm v%NPM_VER%

REM ------------------------------------------------------------------------------
REM 2. Create & Configure Python Virtual Environment (.venv)
REM ------------------------------------------------------------------------------
echo.
echo [2/5] Setting up Python virtual environment (.venv)...

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create Python virtual environment.
        exit /b 1
    )
    echo   [OK] Created virtual environment at .venv
) else (
    echo   [OK] Existing virtual environment found at .venv
)

".venv\Scripts\python.exe" -m pip install --upgrade pip

REM ------------------------------------------------------------------------------
REM 3. Install Backend Dependencies (requirements.txt)
REM ------------------------------------------------------------------------------
echo.
echo [3/5] Installing Python backend dependencies...

".venv\Scripts\pip.exe" install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install Python dependencies from requirements.txt.
    exit /b 1
)

if "%WITH_DOCS%"=="1" (
    echo   Installing MkDocs Material documentation dependencies...
    ".venv\Scripts\pip.exe" install mkdocs mkdocs-material pymdown-extensions
)

echo   [OK] Backend Python packages installed.

REM ------------------------------------------------------------------------------
REM 4. Install React + Vite Frontend Dependencies
REM ------------------------------------------------------------------------------
echo.
echo [4/5] Installing React + Vite frontend dependencies (frontend\)...

call npm --prefix frontend install
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install frontend npm dependencies.
    exit /b 1
)
echo   [OK] Frontend npm packages installed.

REM ------------------------------------------------------------------------------
REM 5. Initialize .env Configuration
REM ------------------------------------------------------------------------------
echo.
echo [5/5] Checking environment configuration (.env)...

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    ".venv\Scripts\python.exe" -c "import secrets; p='.env'; t=open(p).read().replace('replace-with-a-long-random-secret-string', secrets.token_hex(32)); open(p,'w').write(t)"
    echo   [OK] Created .env from .env.example ^(with auto-generated JWT_SECRET_KEY^).
    echo   [!] IMPORTANT: Update GOOGLE_API_KEY, DATABASE_URL, and NEO4J_* in .env before running.
) else (
    echo   [OK] Existing .env file found ^(preserved without overwriting^).
)

echo.
echo ======================================================================
echo   Setup Complete!
echo ======================================================================
echo.
echo Next steps:
echo   1. Configure your credentials in .env ^(GOOGLE_API_KEY, DATABASE_URL, NEO4J_URI, NEO4J_PASSWORD^)
echo   2. Start the FastAPI backend ^(Terminal 1^):
echo        .venv\Scripts\activate ^&^& uvicorn app.api:app --reload --port 8000
echo   3. Start the React + Vite frontend ^(Terminal 2^):
echo        npm --prefix frontend run dev
echo   4. Open http://localhost:5173 in your browser.
echo.

if "%AUTO_START%"=="1" (
    echo Starting FastAPI backend ^(port 8000^) and Vite frontend ^(port 5173^)...
    start "ADK RAG Backend" cmd /k ".venv\Scripts\activate && uvicorn app.api:app --reload --port 8000"
    start "ADK RAG Frontend" cmd /k "npm --prefix frontend run dev"
)

endlocal
