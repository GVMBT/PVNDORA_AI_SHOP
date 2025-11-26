# PowerShell script to run tests
Write-Host "Checking Python installation..." -ForegroundColor Yellow

# Try different Python commands
$pythonCmd = $null
$commands = @("python", "python3", "py", "py -3")

foreach ($cmd in $commands) {
    try {
        $result = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -or $result -match "Python") {
            $pythonCmd = $cmd
            Write-Host "Found Python: $cmd" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Host "Python not found! Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Red
    Write-Host "Or use Windows Store to install Python" -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $pythonCmd -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies!" -ForegroundColor Red
    exit 1
}

Write-Host "Running tests..." -ForegroundColor Yellow
& $pythonCmd -m pytest tests/ -v --tb=short

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed!" -ForegroundColor Red
}

