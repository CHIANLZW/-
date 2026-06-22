# 将 data/*.json 合并为 js/data-bundle.js，供双击 HTML 本地打开（无需服务器）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Data = Join-Path $Root "data"
$Out = Join-Path $Root "js\data-bundle.js"

$core = Get-Content (Join-Path $Data "xiaomi.json") -Raw -Encoding UTF8
$research = Get-Content (Join-Path $Data "xiaomi-research.json") -Raw -Encoding UTF8
$agents = Get-Content (Join-Path $Data "xiaomi-agents.json") -Raw -Encoding UTF8

$content = "window.XIAOMI_REPORT_DATA = Object.assign({}, $core, $research, $agents);`n"
[System.IO.File]::WriteAllText($Out, $content, [System.Text.UTF8Encoding]::new($false))
Write-Host "OK: $Out"
$standalone = Join-Path (Split-Path -Parent $Data) "scripts\build-standalone.ps1"
if (Test-Path $standalone) { & $standalone }
