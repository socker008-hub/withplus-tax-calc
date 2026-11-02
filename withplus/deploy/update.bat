@echo off
chcp 65001 >nul
REM 원본(업스테이지) 업데이트 반영 - GitHub에서 "Sync fork" 누른 뒤 실행
cd /d "%~dp0..\.."
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
git pull
cd withplus
uv sync
uv run --extra test pytest -q
echo 테스트가 모두 passed 이면 서버를 재시작하세요.
pause
