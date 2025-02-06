@echo off
color 0a
:menu
cls
echo ================================
echo Multi Launcher
echo ================================
echo.
echo Pressione 1 para Lançar Capybara
echo Pressione 2 para Lançar Sonic
echo Pressione 3 para Lançar Ambos
echo Pressione 4 para Sair
echo.
choice /c 1234 /n /m "Escolha uma opção: "
if errorlevel 4 goto exit
if errorlevel 3 goto select_both
if errorlevel 2 goto select_sonic
if errorlevel 1 goto select_capybara

:select_capybara
set /p instances=Quantas instâncias de Capybara?: 
goto launch_capybara

:select_sonic
set /p instances=Quantas instâncias de Sonic?: 
goto launch_sonic

:select_both
set /p instances=Quantas instâncias de Capybara e Sonic?: 
goto launch_both

:launch_capybara
for /l %%i in (1,1,%instances%) do (
    start cmd /c python Capybara.7.1.py
)
goto menu

:launch_sonic
for /l %%i in (1,1,%instances%) do (
    start cmd /c python Sonic.2.1.py
)
goto menu

:launch_both
for /l %%i in (1,1,%instances%) do (
    start cmd /c python Capybara.7.2.py
    start cmd /c python Sonic.2.1.py
)
goto menu

:exit
echo Saindo...
pause
exit
