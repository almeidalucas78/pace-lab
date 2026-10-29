@echo off
rem Abre o servico do Treino (API + sincronizacao com o celular). Feche a janela para parar.
cd /d "%~dp0"
title Treino
".venv\Scripts\treino.exe" servico
pause
