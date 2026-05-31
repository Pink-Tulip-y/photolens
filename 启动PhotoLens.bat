@echo off
chcp 65001 >nul
title PhotoLens - 智能照片评分
echo ================================
echo   PhotoLens
echo   正在启动服务器...
echo   浏览器访问 http://localhost:5001
echo   按 Ctrl+C 停止
echo ================================
cd /d "%~dp0"
start http://localhost:5001
python run_prod.py
pause
