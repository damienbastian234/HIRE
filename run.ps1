$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "Starting backend..."
Set-Location $backendDir
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $backendDir

Write-Host "Starting frontend..."
Set-Location $frontendDir
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run dev -- --host 0.0.0.0" -WorkingDirectory $frontendDir

Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173"
