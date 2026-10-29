@echo off
rem Abre o servico do Treino (painel + API + sincronizacao com o celular). Feche a janela para parar.
cd /d "%~dp0"
title Treino
if exist "web\dist\index.html" (
  rem abre o painel no navegador depois que o servico subir
  start "" /b cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
) else (
  echo Painel ainda nao compilado: rode "npm install" e "npm run build" na pasta web.
)
".venv\Scripts\treino.exe" servico
pause
