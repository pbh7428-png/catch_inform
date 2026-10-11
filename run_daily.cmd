@echo off
rem Run by Windows Task Scheduler every day. Log: output\run.log
rem Keep this file ASCII-only: cmd.exe reads it as CP949 and garbles UTF-8 Korean.
cd /d "%~dp0"
if not exist output mkdir output
>> output\run.log echo ==== %date% %time% ====
py daily_news.py >> output\run.log 2>&1
>> output\run.log echo exit=%errorlevel%
