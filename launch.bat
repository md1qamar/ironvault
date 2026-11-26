@echo off
title IronVault – High-Security Password Manager
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] IronVault closed with an error.
    pause
)
