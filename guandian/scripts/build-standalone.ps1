# 生成 guandian/小米分析-本地单页.html（CSS+JS+数据全部内嵌，Cursor 内置浏览器可直接打开）
$ErrorActionPreference = "Stop"
$g = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$css = Get-Content (Join-Path $g "css\styles.css") -Raw -Encoding UTF8
$data = Get-Content (Join-Path $g "js\data-bundle.js") -Raw -Encoding UTF8
$kline = Get-Content (Join-Path $g "js\kline-chart.js") -Raw -Encoding UTF8
$report = Get-Content (Join-Path $g "js\report-engine.js") -Raw -Encoding UTF8
$out = Join-Path $g "小米分析-本地单页.html"
$html = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>小米集团 · 分析师研究报（本地单页）</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
$css
  </style>
</head>
<body>
<div class="container">
  <div class="nav-bar">
    <span id="navTitle">小米集团</span>
    <span class="nav-bar__hint">本地单页 · Cursor 内置浏览器可直接打开</span>
  </div>
  <div id="app"><p class="hint" style="text-align:center;padding:48px 20px">正在加载…</p></div>
  <p class="disclaimer" id="disclaimer"></p>
</div>
<script>
$data
</script>
<script>
$kline
</script>
<script>
$report
</script>
</body>
</html>
"@
[System.IO.File]::WriteAllText($out, $html, [System.Text.UTF8Encoding]::new($false))
Write-Host "OK: $out ($((Get-Item $out).Length) bytes)"
