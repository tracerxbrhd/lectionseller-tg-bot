param(
    [switch]$Rebuild,
    [switch]$SkipBuild,
    [switch]$SkipMigrations,
    [switch]$CreateAdmin,
    [string]$AdminUsername = "admin",
    [switch]$SkipEnvCheck
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Executable {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Executable "docker")) {
    throw "Docker is not installed or is not available in PATH."
}

$script:UseComposePlugin = $false
try {
    docker compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        $script:UseComposePlugin = $true
    }
}
catch {
    $script:UseComposePlugin = $false
}

if (-not $script:UseComposePlugin -and -not (Test-Executable "docker-compose")) {
    throw "Docker Compose is not available. Install Docker Desktop or docker-compose."
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    if ($script:UseComposePlugin) {
        & docker compose @Arguments
    }
    else {
        & docker-compose @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose command failed: $($Arguments -join ' ')"
    }
}

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -eq 2) {
            $values[$parts[0]] = $parts[1].Trim('"').Trim("'")
        }
    }
    return $values
}

function Assert-RequiredEnv {
    if ($SkipEnvCheck) {
        return
    }

    $envValues = Read-DotEnv ".env"
    $botToken = $envValues["BOT_TOKEN"]
    $secret = $envValues["APP_SECRET_KEY"]

    if ([string]::IsNullOrWhiteSpace($botToken) -or $botToken -eq "replace-with-telegram-bot-token") {
        throw "Set BOT_TOKEN in .env before starting bot. Use -SkipEnvCheck to bypass this check."
    }

    if ([string]::IsNullOrWhiteSpace($secret) -or $secret.StartsWith("change-me")) {
        throw "Set a strong APP_SECRET_KEY in .env before starting. Use -SkipEnvCheck to bypass this check."
    }
}

Write-Step "Checking .env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env was created from .env.example." -ForegroundColor Yellow
    throw "Fill .env with BOT_TOKEN, APP_SECRET_KEY and other secrets, then run this script again."
}
Assert-RequiredEnv

Write-Step "Checking Docker daemon"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon is not running. Start Docker Desktop and run this script again."
}

if (-not $SkipBuild) {
    if ($Rebuild) {
        Write-Step "Building web and bot images without cache"
        Invoke-Compose build --no-cache web bot
    }
    else {
        Write-Step "Building web and bot images"
        Invoke-Compose build web bot
    }
}

Write-Step "Starting PostgreSQL and Redis"
Invoke-Compose up -d postgres redis

if (-not $SkipMigrations) {
    Write-Step "Applying Alembic migrations"
    Invoke-Compose run --rm web alembic upgrade head
}

if ($CreateAdmin) {
    Write-Step "Creating or updating web admin"
    Invoke-Compose run --rm web python -m app.cli.create_admin --username $AdminUsername
}

Write-Step "Starting web and bot"
Invoke-Compose up -d web bot

Write-Step "Current services"
Invoke-Compose ps

Write-Host ""
Write-Host "Local startup completed." -ForegroundColor Green
Write-Host "Admin panel: http://localhost:8000/admin/login"
Write-Host "Healthcheck: http://localhost:8000/health"
Write-Host "Logs:"
Write-Host "  docker compose logs --tail=100 web"
Write-Host "  docker compose logs --tail=100 bot"
