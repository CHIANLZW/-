# 本地预览：在仓库根目录创建指向 studio/ 的目录联接，兼容旧书签 /css /js /assets
$root = Split-Path -Parent $PSScriptRoot
$links = @(
  @{ Name = 'assets'; Target = 'studio\assets' },
  @{ Name = 'css';    Target = 'studio\css' },
  @{ Name = 'js';     Target = 'studio\js' }
)

foreach ($link in $links) {
  $path = Join-Path $root $link.Name
  $target = Join-Path $root $link.Target
  if (Test-Path $path) {
    Write-Host "已存在，跳过: $($link.Name)"
    continue
  }
  if (-not (Test-Path $target)) {
    Write-Error "目标不存在: $target"
    exit 1
  }
  cmd /c mklink /J $path $link.Target | Out-Null
  Write-Host "已创建联接: $($link.Name) -> $($link.Target)"
}

Write-Host "完成。请访问 http://localhost:8080/studio/ 或 http://localhost:8080/ 入口页。"
