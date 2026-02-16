@echo off
REM Test connection between frontend and backend
echo Testing Intelligent Document Assistant Connection...
echo.

echo Step 1: Testing if backend is accessible
curl -s http://localhost:8000/health > nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Backend is running and accessible
    echo Response:
    curl -s http://localhost:8000/health
) else (
    echo ✗ Backend is NOT running or not accessible
    echo Make sure to run: python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
)

echo.
echo Step 2: Backend API endpoints available:
echo ✓ GET  http://localhost:8000/health
echo ✓ GET  http://localhost:8000/docs (Swagger UI)
echo ✓ POST http://localhost:8000/upload
echo ✓ POST http://localhost:8000/query
echo ✓ GET  http://localhost:8000/memory
echo ✓ POST http://localhost:8000/reset

echo.
echo Step 3: Frontend file
if exist "index.html" (
    echo ✓ index.html exists
    echo Open it with: index.html or file:///path/to/index.html
) else (
    echo ✗ index.html NOT found
)

echo.
echo Troubleshooting:
echo 1. Open http://localhost:8000/docs in browser - should see Swagger UI
echo 2. Check browser F12 Console for JavaScript errors
echo 3. Check browser F12 Network tab to see API requests
echo 4. Restart backend if getting "connection refused"
