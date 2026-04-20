@echo off
echo ============================================
echo   Speech Analysis System - Starting...
echo ============================================
echo.

cd /d D:\Audio\speech_analysis_system

set KMP_DUPLICATE_LIB_OK=TRUE
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set TOKENIZERS_PARALLELISM=false

echo Starting FastAPI server...
echo Docs will be available at: http://localhost:8000/docs
echo.

.venv\Scripts\uvicorn.exe src.main:app --host 0.0.0.0 --port 8000 --reload

pause