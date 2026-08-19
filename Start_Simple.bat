@echo off
REM Foloseste acelasi setup verificat ca launcherul principal.
call "%~dp0Start_CaptionsUI.bat" %*
exit /b %ERRORLEVEL%
