@echo off
chcp 65001 >nul
REM ============================================================
REM  Compilação Local do Simulador Caldeira S7-1200 para Windows
REM  Basta executar este arquivo no terminal ou dar duplo clique.
REM ============================================================

echo ============================================================
echo   GERADOR DE EXECUTAVEL (.EXE) - CALDEIRA S7-1200
echo ============================================================
echo.

if not exist ".venv" (
    echo [1/3] Criando ambiente virtual Python (.venv)...
    python -m venv .venv 2>nul || py -m venv .venv
) else (
    echo [1/3] Ambiente virtual (.venv) localizado.
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo.
echo [2/3] Instalando dependencias e PyInstaller...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo [3/3] Gerando o executavel com PyInstaller...
pyinstaller simulador_caldeira.spec --noconfirm --clean

echo.
echo ============================================================
echo   COMPILACAO LOCAL CONCLUIDA!
echo   Executavel gerado em: dist\Simulador_Caldeira_S7_1200.exe
echo ============================================================
pause
