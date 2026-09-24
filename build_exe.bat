@echo off
REM ============================================================
REM  Build do Simulador_Caldeira_S7_1200.exe para Windows
REM ============================================================

echo [1/3] Instalando dependencias do projeto...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [2/3] Gerando executavel standalone (Onefile) com PyInstaller...
python -m PyInstaller simulador_caldeira.spec --noconfirm --clean

echo [3/3] Concluido com sucesso!
echo ============================================================
echo   Executavel standalone gerado em: dist\Simulador_Caldeira_S7_1200.exe
echo   Pronto para copiar para pendrive ou distribuir para alunos!
echo ============================================================
pause
