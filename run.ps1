# ─── CodeContext AI — Start / Stop ───────────────────────────
# Usage:
#   .\run.ps1          → start both backend + frontend
#   .\run.ps1 stop     → kill all running backend + frontend processes

param(
    [string]$Action = "start"
)

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BE   = Join-Path $ROOT "backend"
$FE   = Join-Path $ROOT "frontend"

function Stop-All {
    Write-Host "`n🛑 Stopping all CodeContext processes..." -ForegroundColor Yellow

    # Kill uvicorn / python backends
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        try { $_.MainModule.FileName -and $_.CommandLine -match "uvicorn" } catch { $false }
    } | ForEach-Object { Stop-Process -Id $_.Id -Force; Write-Host "   Killed python PID $($_.Id)" }

    # Kill node / npm frontends
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        try { $_.MainModule.FileName -and $_.CommandLine -match "vite|next" } catch { $false }
    } | ForEach-Object { Stop-Process -Id $_.Id -Force; Write-Host "   Killed node PID $($_.Id)" }

    # Brute-force: kill anything on ports 8000 and 5173
    foreach ($port in @(8000, 5173)) {
        $procIds = netstat -ano | Select-String ":$port\s" | ForEach-Object {
            ($_ -split '\s+')[-1]
        } | Sort-Object -Unique | Where-Object { $_ -ne "0" }

        foreach ($procId in $procIds) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Write-Host "   Killed PID $procId (port $port)" -ForegroundColor DarkGray
            } catch {}
        }
    }

    Write-Host "✅ All processes stopped.`n" -ForegroundColor Green
}

function Start-All {
    Stop-All

    Write-Host "🚀 Starting CodeContext AI...`n" -ForegroundColor Cyan

    # Start backend
    Write-Host "   [BE] Starting backend on :8000..." -ForegroundColor Blue
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BE'; python -m uvicorn app.main:app --reload --port 8000 --log-level info" -WindowStyle Normal

    Start-Sleep -Seconds 2

    # Start frontend
    Write-Host "   [FE] Starting frontend on :5173..." -ForegroundColor Magenta
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FE'; npm run dev" -WindowStyle Normal

    Write-Host "`n✅ Both services launched in separate windows." -ForegroundColor Green
    Write-Host "   Backend  → http://localhost:8000" -ForegroundColor DarkGray
    Write-Host "   Frontend → http://localhost:5173" -ForegroundColor DarkGray
    Write-Host "   Stop all → .\run.ps1 stop`n" -ForegroundColor DarkGray
}

# ── Main ────────────────────────────────────────────────────
switch ($Action.ToLower()) {
    "stop"  { Stop-All }
    "start" { Start-All }
    default { Write-Host "Usage: .\run.ps1 [start|stop]" -ForegroundColor Yellow }
}
