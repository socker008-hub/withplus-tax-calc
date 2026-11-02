@echo off
chcp 65001 >nul
REM Windows 로그인 시 공개 서버 자동 실행 등록 (작업 스케줄러)
schtasks /Create /TN "WithplusTaxCalc" /TR "\"%~dp0run_public.bat\"" /SC ONLOGON /RL LIMITED /F
echo 등록 완료. 해제: schtasks /Delete /TN "WithplusTaxCalc" /F
pause
