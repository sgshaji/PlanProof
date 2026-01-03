# Start PlanProof API with environment variables
# This script sets required environment variables and starts the FastAPI server

# Set JWT secret key for authentication (change this in production!)
$env:JWT_SECRET_KEY = "dev-secret-key-change-in-production-12345"

# Set JWT algorithm
$env:JWT_ALGORITHM = "HS256"

# Set JWT expiration (in minutes)
$env:JWT_EXPIRATION_MINUTES = "1440"  # 24 hours

# Start the API
Write-Host "Starting PlanProof API..." -ForegroundColor Green
Write-Host "JWT authentication configured" -ForegroundColor Yellow
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""

python run_api.py

