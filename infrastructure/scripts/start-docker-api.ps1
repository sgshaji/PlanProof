# Start the PlanProof FastAPI Backend with Docker (PowerShell)

Write-Host "🐳 Starting PlanProof FastAPI Backend with Docker..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "   Visit: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is available
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    $composeVersion = docker compose version 2>$null
    if (-not $composeVersion) {
        Write-Host "❌ Docker Compose is not available." -ForegroundColor Red
        exit 1
    }
    $composeCmd = "docker compose"
} else {
    $composeCmd = "docker-compose"
}

# Create .env file if it doesn't exist
if (-not (Test-Path .env)) {
    Write-Host "⚠️  No .env file found. Creating from .env.example..." -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "✅ .env file created. Please update it with your configuration." -ForegroundColor Green
    } else {
        Write-Host "⚠️  No .env.example found. Using default configuration." -ForegroundColor Yellow
    }
}

# Stop any existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
& $composeCmd -f docker-compose.api.yml down 2>$null

# Build and start the services
Write-Host "🔨 Building Docker images..." -ForegroundColor Cyan
& $composeCmd -f docker-compose.api.yml build

Write-Host "🚀 Starting services..." -ForegroundColor Green
& $composeCmd -f docker-compose.api.yml up -d

# Wait for services to be ready
Write-Host ""
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if API is responding
Write-Host "🔍 Checking API health..." -ForegroundColor Cyan
$maxAttempts = 30
$apiReady = $false

for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host ""

if ($apiReady) {
    Write-Host "✅ PlanProof API is running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 API URL: http://localhost:8000" -ForegroundColor White
    Write-Host "📖 API Docs: http://localhost:8000/api/docs" -ForegroundColor White
    Write-Host "📊 Health Check: http://localhost:8000/api/health" -ForegroundColor White
    Write-Host ""
    Write-Host "To view logs: $composeCmd -f docker-compose.api.yml logs -f api" -ForegroundColor Cyan
    Write-Host "To stop: $composeCmd -f docker-compose.api.yml down" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  API did not respond within expected time. Checking logs..." -ForegroundColor Yellow
    Write-Host ""
    & $composeCmd -f docker-compose.api.yml logs --tail=20 api
    Write-Host ""
    Write-Host "Run '$composeCmd -f docker-compose.api.yml logs -f api' to see full logs" -ForegroundColor Cyan
    exit 1
}
