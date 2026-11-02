@echo off
chcp 65001 >nul
REM 접속 토큰 생성 - 출력된 값을 .env 의 WITHPLUS_TOKENS 에 "이름:토큰" 형태로 추가
cd /d "%~dp0.."
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
pause
