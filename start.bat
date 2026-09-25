@echo off
REM LexPilot - Quick Start Script for Windows
REM Automates setup and startup process

echo ========================================
echo   LexPilot - AI Legal Assistant
echo   Quick Start Script
echo ========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Check .env file
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and add your API keys!
    echo    Required: OPENAI_API_KEY, ANTHROPIC_API_KEY
    echo.
    pause
)

REM Start server
echo.
echo ========================================
echo   Starting LexPilot Server...
echo ========================================
echo.
echo   API Docs: http://localhost:8000/docs
echo   Health:   http://localhost:8000/health
echo.
echo   Press Ctrl+C to stop
echo.

python main.py serve --reload
