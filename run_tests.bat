@echo off
echo Checking Python installation...
python --version 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.8+ from https://www.python.org/
    echo Or use: py -3 -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -r requirements.txt

echo Running tests...
python -m pytest tests/ -v --tb=short

pause

