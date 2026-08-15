$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$html = Get-Content -Raw (Join-Path $root 'public/index.html')

foreach ($needle in @('id="loginView"', 'id="appView"', 'data-section="dashboard"', 'data-section="orders"', 'data-section="products"', 'data-section="customers"', 'data-section="chats"', 'data-section="mailings"', 'data-section="promos"', 'data-section="analytics"')) {
  if ($html -notmatch [regex]::Escape($needle)) { throw "CRM shell marker is missing: $needle" }
}

$scriptPath = Join-Path $root 'public/app.js'
if (-not (Test-Path $scriptPath)) { throw 'CRM API client is missing' }
$script = Get-Content -Raw $scriptPath
if ($script -notmatch [regex]::Escape('/api/v1')) { throw 'API client must use the relative /api/v1 route' }
if ($script -notmatch 'toggleTheme') { throw 'Theme switcher is missing' }
