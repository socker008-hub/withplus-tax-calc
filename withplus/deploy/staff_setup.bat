@echo off
chcp 65001 >nul
setlocal
title 위드플러스 세금계산기 설치
REM =====================================================================
REM  위드플러스 세금계산기 - 직원용 원클릭 설치 / 업데이트
REM  더블클릭만 하면 됩니다. 다시 실행하면 최신 버전으로 업데이트됩니다.
REM =====================================================================
set "REPO_ZIP=https://github.com/socker008-hub/withplus-tax-calc/archive/refs/heads/main.zip"
set "TARGET=%USERPROFILE%\withplus-tax-calc"
set "WORK=%TEMP%\withplus-setup"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo.
echo  ===== 위드플러스 세금계산기 설치 =====
echo  설치 위치: %TARGET%
echo.

echo [1/5] 프로그램 내려받는 중...
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri '%REPO_ZIP%' -OutFile '%WORK%\src.zip'; Expand-Archive -Path '%WORK%\src.zip' -DestinationPath '%WORK%' -Force"
if not exist "%WORK%\withplus-tax-calc-main\withplus\pyproject.toml" goto :fail_download

echo [2/5] 파일 복사 중... (기존 설정 .env 는 유지)
robocopy "%WORK%\withplus-tax-calc-main" "%TARGET%" /MIR /XD .venv logs .git /XF .env /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :fail_copy
if not exist "%TARGET%\withplus\.env" copy "%TARGET%\withplus\.env.example" "%TARGET%\withplus\.env" >nul

echo [3/5] 실행 도구(uv) 확인 중...
where uv >nul 2>nul
if errorlevel 1 powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
where uv >nul 2>nul
if errorlevel 1 goto :fail_uv

echo [4/5] 계산기 설치 중... (처음에는 1~3분)
cd /d "%TARGET%\withplus"
uv sync --quiet
if errorlevel 1 goto :fail_sync

:check_claude
tasklist /FI "IMAGENAME eq claude.exe" 2>nul | find /I "claude.exe" >nul
if errorlevel 1 goto :register
echo.
echo  [잠깐] Claude Desktop 이 켜져 있습니다.
echo         화면 오른쪽 아래 트레이의 Claude 아이콘 우클릭 - 종료 후
echo         이 창에서 아무 키나 누르세요.
pause >nul
goto :check_claude

:register
echo [5/5] Claude Desktop 에 등록 + 계산 테스트...
uv run python deploy\register_claude_desktop.py
if errorlevel 1 goto :fail_register
rmdir /s /q "%WORK%" 2>nul

echo.
echo  ===== 설치 완료 =====
echo  1. Claude Desktop 을 실행하세요.
echo  2. 새 대화에서 이렇게 물어보세요:
echo     "퇴직금 1억, 근속 15년, 2026년 퇴직 퇴직소득세"
echo  3. 도구 사용 허용 창이 뜨면 [항상 허용] 을 누르세요.
echo     2,175,000원 이 나오면 정상입니다.
echo.
pause
exit /b 0

:fail_download
echo.
echo  [오류] 프로그램을 내려받지 못했습니다. 인터넷 연결을 확인하고 다시 실행하세요.
goto :end_fail
:fail_copy
echo.
echo  [오류] 파일 복사에 실패했습니다. %TARGET% 폴더를 열고 있는 프로그램을 닫고 다시 실행하세요.
goto :end_fail
:fail_uv
echo.
echo  [오류] 실행 도구(uv) 설치에 실패했습니다. 창을 닫고 다시 실행하세요.
goto :end_fail
:fail_sync
echo.
echo  [오류] 계산기 설치(uv sync)에 실패했습니다. 위 메시지를 캡처해 조덕희 세무사에게 보내 주세요.
goto :end_fail
:fail_register
echo.
echo  [오류] Claude Desktop 등록 또는 계산 테스트에 실패했습니다. 위 메시지를 캡처해 조덕희 세무사에게 보내 주세요.
goto :end_fail
:end_fail
echo.
pause
exit /b 1
