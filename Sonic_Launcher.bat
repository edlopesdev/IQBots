:: filepath: /f:/Users/xdgee/Downloads/IQ bots/venv_name/Capybara_Launcher.bat
@echo off
color 0a
:menu
cls
echo ================================
echo Sonic Launcher
echo ================================
echo.
set /p instances=Instâncias: 
echo.
echo Pressione 3 para Lançar
echo Pressione 4 para Sair
echo.
choice /c 34 /n /m "Escolha uma opção: "
if errorlevel 2 goto exit
if errorlevel 1 goto launch


:launch
echo Lançando %instances% instâncias...
for /l %%i in (1,1,%instances%) do (
    start cmd /c python Sonic.2.3.py
    timeout /t 60 /nobreak >nul
)
pause
goto menu

:exit
echo Saindo...
pause
exit