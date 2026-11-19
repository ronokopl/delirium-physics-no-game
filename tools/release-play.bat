@echo off
rem MODIFIED version of Delirium Physics: starts the Playroom with NO game files.
rem Source code (GPL-3.0-only): https://github.com/ronokopl/delirium-physics-no-game
cd /d "%~dp0"
"delirium-room.exe" %*
if errorlevel 1 (echo. & echo The room stopped unexpectedly: the lines above say why. & pause)
