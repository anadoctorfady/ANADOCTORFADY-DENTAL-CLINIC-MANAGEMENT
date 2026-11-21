@echo off
chcp 65001 >nul
title ANADOCTORFADY - Dental Clinic
echo Starting ANADOCTORFADY...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python not found! Install Python 3.8+ from python.org
  pause
  exit /b
)
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
python main.py
pause
