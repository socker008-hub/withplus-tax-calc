@echo off
chcp 65001 >nul
REM 위드플러스 세금계산기 - 최초 설치 (withplus\deploy 폴더에서 더블클릭)
cd /d "%~dp0.."
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo [1/3] uv 설치 중...
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
echo [2/3] 프로그램 설치 중 (처음 1~3분)...
uv sync
if errorlevel 1 ( echo 설치 실패 - 위 오류 메시지를 확인하세요 & pause & exit /b 1 )
if not exist .env copy .env.example .env >nul
echo [3/3] 완료. 다음: withplus\.env 파일을 메모장으로 열어 값을 채우세요.
pause
