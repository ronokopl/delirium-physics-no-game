@echo off
rem MODIFIED copy of Delirium Physics: starts the Playroom with NO Grand Theft Auto IV files.
rem The numbers and the body it runs on are stand-ins worked out from the source (see docs\no-game.md),
rem not the game's, so Homer moves differently from the real Delirium.
cd /d "%~dp0"
if not exist "target\release\delirium-room.exe" (
  where cargo >nul 2>nul
  if errorlevel 1 (
    echo The room has to be built once, and that needs Rust.
    echo Install it from https://rustup.rs ^(it also offers Microsoft's free C++ build tools^), then start this again.
    pause
    exit /b 1
  )
  echo Building the room. This happens once and takes a few minutes...
  cargo build --release -p delirium-room
  if errorlevel 1 (echo. & echo The build failed: the lines above say why. & pause & exit /b 1)
)
"target\release\delirium-room.exe" %*
if errorlevel 1 (echo. & echo The room stopped unexpectedly: the lines above say why. & pause)
