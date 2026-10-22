@echo off
chcp 65001 >nul
title Gerar instalador do PlusEduc
cd /d "%~dp0"

rem Python do ambiente virtual do projeto (PLUSEDUC_PYTHON permite usar outro interpretador).
if not defined PLUSEDUC_PYTHON set "PLUSEDUC_PYTHON=.venv\Scripts\python.exe"
if not exist "%PLUSEDUC_PYTHON%" (
    echo Criando o ambiente virtual .venv ...
    py -3.12 -m venv .venv || py -3 -m venv .venv
)

echo Instalando dependencias ...
"%PLUSEDUC_PYTHON%" -m pip install -q -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto falhou

echo Compilando a interface, o aplicativo e o instalador (leva alguns minutos) ...
"%PLUSEDUC_PYTHON%" scripts\build_exe.py --installer
if errorlevel 1 goto falhou

echo.
echo Pronto. O instalador esta em %CD%\dist\installer
explorer dist\installer
pause
exit /b 0

:falhou
echo.
echo A compilacao falhou. Veja as mensagens acima.
echo Se faltar o Inno Setup: winget install JRSoftware.InnoSetup
pause
exit /b 1
