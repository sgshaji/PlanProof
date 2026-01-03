# CORS Fix Script for PlanProof
# This script helps diagnose and fix CORS issues

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  PlanProof CORS Diagnostic & Fix Tool" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if backend is running
Write-Host "[1/6] Checking if backend is running..." -ForegroundColor Yellow
$pythonProcesses = Get-Process | Where-Object {$_.ProcessName -like "*python*"}
if ($pythonProcesses) {
    Write-Host "✓ Python process found (PID: $($pythonProcesses.Id -join ', '))" -ForegroundColor Green
} else {
    Write-Host "✗ No Python process found - backend may not be running" -ForegroundColor Red
}

# Test health endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Backend is responding on port 8000" -ForegroundColor Green
    Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Backend is NOT responding on port 8000" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "ACTION REQUIRED: Start the backend with:" -ForegroundColor Yellow
    Write-Host "  python run_api.py" -ForegroundColor White
    Write-Host "  OR" -ForegroundColor White
    Write-Host "  .\start_api.ps1" -ForegroundColor White
    exit 1
}

Write-Host ""

# Step 2: Check if .env file exists
Write-Host "[2/6] Checking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "✗ .env file NOT found" -ForegroundColor Red
    Write-Host ""
    Write-Host "ACTION REQUIRED: Create .env file with:" -ForegroundColor Yellow
    Write-Host "  API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501" -ForegroundColor White
    exit 1
}

Write-Host ""

# Step 3: Check API_CORS_ORIGINS in .env
Write-Host "[3/6] Checking API_CORS_ORIGINS configuration..." -ForegroundColor Yellow
$envContent = Get-Content ".env" -Raw
if ($envContent -match "API_CORS_ORIGINS\s*=\s*(.+)") {
    $corsOrigins = $matches[1].Trim()
    Write-Host "✓ API_CORS_ORIGINS found: $corsOrigins" -ForegroundColor Green
    
    # Check if it includes common development ports
    $requiredOrigins = @("http://localhost:3000", "http://localhost:3002", "http://localhost:8501")
    $missingOrigins = @()
    
    foreach ($origin in $requiredOrigins) {
        if ($corsOrigins -notlike "*$origin*") {
            $missingOrigins += $origin
        }
    }
    
    if ($missingOrigins.Count -gt 0) {
        Write-Host "⚠ Warning: Some common origins are missing:" -ForegroundColor Yellow
        foreach ($missing in $missingOrigins) {
            Write-Host "  - $missing" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "RECOMMENDATION: Add missing origins to .env:" -ForegroundColor Yellow
        Write-Host "  API_CORS_ORIGINS=$corsOrigins,$($missingOrigins -join ',')" -ForegroundColor White
    }
} else {
    Write-Host "✗ API_CORS_ORIGINS NOT found in .env" -ForegroundColor Red
    Write-Host ""
    Write-Host "ACTION REQUIRED: Add to .env file:" -ForegroundColor Yellow
    Write-Host "  API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501" -ForegroundColor White
    
    # Offer to add it automatically
    Write-Host ""
    $response = Read-Host "Would you like to add it automatically? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Add-Content -Path ".env" -Value "`nAPI_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8501"
        Write-Host "✓ Added API_CORS_ORIGINS to .env" -ForegroundColor Green
        Write-Host "⚠ You must restart the backend for changes to take effect" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""

# Step 4: Test CORS preflight
Write-Host "[4/6] Testing CORS preflight request..." -ForegroundColor Yellow
try {
    $headers = @{
        "Origin" = "http://localhost:3002"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "Content-Type"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/applications" -Method OPTIONS -Headers $headers -TimeoutSec 5 -ErrorAction Stop
    
    $allowOrigin = $response.Headers["Access-Control-Allow-Origin"]
    $allowMethods = $response.Headers["Access-Control-Allow-Methods"]
    $allowCredentials = $response.Headers["Access-Control-Allow-Credentials"]
    
    if ($allowOrigin) {
        Write-Host "✓ CORS is configured correctly" -ForegroundColor Green
        Write-Host "  Allow-Origin: $allowOrigin" -ForegroundColor Gray
        Write-Host "  Allow-Methods: $allowMethods" -ForegroundColor Gray
        Write-Host "  Allow-Credentials: $allowCredentials" -ForegroundColor Gray
    } else {
        Write-Host "✗ CORS headers not present in response" -ForegroundColor Red
        Write-Host "  This means the origin is not allowed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ CORS preflight request failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "This usually means:" -ForegroundColor Yellow
    Write-Host "  1. The origin http://localhost:3002 is not in API_CORS_ORIGINS" -ForegroundColor White
    Write-Host "  2. The backend needs to be restarted after .env changes" -ForegroundColor White
}

Write-Host ""

# Step 5: Check frontend ports
Write-Host "[5/6] Checking which ports are in use..." -ForegroundColor Yellow
$portsToCheck = @(3000, 3001, 3002, 5173, 8000, 8501)
foreach ($port in $portsToCheck) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $processId = $connection.OwningProcess | Select-Object -First 1
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        Write-Host "  Port $port : ACTIVE ($($process.ProcessName))" -ForegroundColor Green
    } else {
        Write-Host "  Port $port : not in use" -ForegroundColor Gray
    }
}

Write-Host ""

# Step 6: Summary and recommendations
Write-Host "[6/6] Summary and Recommendations" -ForegroundColor Yellow
Write-Host ""

$allGood = $true

# Check if backend is healthy
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
} catch {
    $allGood = $false
    Write-Host "❌ Backend is not responding" -ForegroundColor Red
    Write-Host "   → Start backend: python run_api.py" -ForegroundColor Yellow
}

# Check if .env has CORS config
if (-not (Test-Path ".env") -or -not ((Get-Content ".env" -Raw) -match "API_CORS_ORIGINS")) {
    $allGood = $false
    Write-Host "❌ API_CORS_ORIGINS not configured" -ForegroundColor Red
    Write-Host "   → Add to .env: API_CORS_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:8501" -ForegroundColor Yellow
}

if ($allGood) {
    Write-Host "✓ Everything looks good!" -ForegroundColor Green
    Write-Host ""
    Write-Host "If you're still seeing CORS errors:" -ForegroundColor Yellow
    Write-Host "  1. Restart the backend: Get-Process | Where-Object {`$_.ProcessName -like '*python*'} | Stop-Process; python run_api.py" -ForegroundColor White
    Write-Host "  2. Clear browser cache and reload the page" -ForegroundColor White
    Write-Host "  3. Check browser console for the exact error message" -ForegroundColor White
    Write-Host "  4. Verify frontend is using the correct API URL (http://localhost:8000)" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Please fix the issues above and run this script again." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "For detailed help, see: CORS_FIX_GUIDE.md" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

