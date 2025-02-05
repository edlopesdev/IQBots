@echo off
REM Verifica se o Python está no PATH
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python não está configurado no PATH. Por favor, configure-o antes de continuar.
    pause
    exit /b
)

REM Executa o script Python
python Sonic.2.1.py
pause
