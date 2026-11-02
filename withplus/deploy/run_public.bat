@echo off
chcp 65001 >nul
REM 외부 공개 서버 실행 (Cloudflare Tunnel 이 http://127.0.0.1:8001 로 연결)
cd /d "%~dp0.."
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv run withplus-tax-calc --mode public
