param(
    [switch]$DryRun,
    [switch]$Inactive
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

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

$argsList = @("run", "--rm", "web", "python", "-m", "app.cli.seed_demo_catalog")
if ($DryRun) {
    $argsList += "--dry-run"
}
if ($Inactive) {
    $argsList += "--inactive"
}

Invoke-Compose @argsList
