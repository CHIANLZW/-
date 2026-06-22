# inchian.top 本地启动（Windows）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host " inchian.top 本地预览" -ForegroundColor Cyan
Write-Host " ====================" -ForegroundColor Cyan
Write-Host ""
Write-Host " 切勿直接双击 HTML 文件。" -ForegroundColor Yellow
Write-Host " 启动后请在浏览器打开：" -ForegroundColor Gray
Write-Host ""
Write-Host "   http://localhost:8080" -ForegroundColor Green
Write-Host ""
Write-Host " 二级站点：" -ForegroundColor Gray
Write-Host "   /studio/    工作室" -ForegroundColor Gray
Write-Host "   /resume/    简历" -ForegroundColor Gray
Write-Host "   /zichan/    资产分析" -ForegroundColor Gray
Write-Host "   /guandian/  公司财务分析" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path "node_modules\serve")) {
  Write-Host "首次运行，正在安装 serve..." -ForegroundColor Yellow
  npm install --no-fund --no-audit 2>&1 | Out-Host
}

npm run start
