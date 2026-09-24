@echo off
REM ============================================================
REM  StudyVerse – Full Stack Launcher
REM  Window 1: FastAPI backend  |  Window 2: Streamlit UI
REM ============================================================

echo.
echo  [StudyVerse] Starting FastAPI backend...
start "StudyVerse Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"

echo  [StudyVerse] Waiting 4 seconds for backend to initialise...
timeout /t 4 /nobreak > nul

echo  [StudyVerse] Starting Streamlit UI...
start "StudyVerse UI" cmd /k "cd /d %~dp0 && backend\.venv\Scripts\streamlit.exe run app.py --server.port 8501 --server.headless false"

echo.
echo  StudyVerse is starting!
echo    Backend:  http://127.0.0.1:8000
echo    UI:       http://localhost:8501
echo    API docs: http://127.0.0.1:8000/docs
echo.
pause
