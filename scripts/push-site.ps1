# 一键推送脚本（需已安装 Git，且已配置 GitHub 远程仓库）
# 用法：
#   .\scripts\push-site.ps1
#   .\scripts\push-site.ps1 -Message "更新首页文案"
param(
  [string]$Message = "站点更新"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".git")) {
  Write-Error "未找到 .git，请先在项目根目录执行 git init"
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
  Write-Host ""
  Write-Host "尚未配置 GitHub 远程仓库。请先执行：" -ForegroundColor Yellow
  Write-Host '  git remote add origin https://github.com/YOUR_USERNAME/inchian-top.git' -ForegroundColor Cyan
  Write-Host '  git push -u origin main' -ForegroundColor Cyan
  Write-Host ""
  exit 1
}

git add -A
$status = git status --porcelain
if (-not $status) {
  Write-Host "没有需要提交的更改。" -ForegroundColor Green
  exit 0
}

git commit -m $Message
git push origin main

Write-Host ""
Write-Host "已推送到 $remote" -ForegroundColor Green
Write-Host "GitHub Pages 与 Cloudflare Pages 将在数分钟内自动更新。" -ForegroundColor Green
