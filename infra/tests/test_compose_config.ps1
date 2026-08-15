$ErrorActionPreference = 'Stop'

$config = docker compose config 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "docker compose config failed: $config"
}

foreach ($service in 'postgres', 'redis', 'backend', 'bot', 'worker', 'admin-web', 'nginx') {
    if ($config -notmatch "(?m)^\s{2}$([regex]::Escape($service)):") {
        throw "Missing Compose service: $service"
    }
}

if (-not (Test-Path '.gitignore') -or (Get-Content '.gitignore' -Raw) -notmatch '(?m)^\.env\r?$') {
    throw '.env must be ignored by Git'
}
