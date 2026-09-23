@echo off
cd /d "%~dp0"
title Auto Bot - LinkedIn Job Discord Bot
echo ===================================================
echo   Auto Bot LinkedIn Job - Discord Bot Service
echo ===================================================
echo Starting Discord bot...
echo Keep this window open so the bot can respond to /hunt and other slash commands in Discord.
echo.
python -m engine.discord_bot
pause
