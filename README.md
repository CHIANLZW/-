# inchian.top

个人网站。访问根目录 `index.html` 进入站点选择页。

## 本地运行

### 观点 / 小米分析（guandian）— 推荐

与 `resume/` 同级，**无需 npm start**：

| 打开方式 | 文件 |
|---------|------|
| **Cursor 软件内预览** | `guandian/小米分析-本地单页.html` → `Ctrl+Shift+P` → `Simple Browser: Show` → 拖入该文件 |
| 双击本地打开 | `guandian/index.html` 或 `guandian/打开小米分析.bat` |
| Cursor 工作区 | 双击打开 `inchian.top.code-workspace` |

改 `guandian/data/*.json` 后运行 `guandian/scripts/sync-data-bundle.ps1`（会同步单页版）。

### 全站预览（可选）

需要同时预览工作室等多站点时：

```powershell
npm install
npm start
```

浏览器打开 http://localhost:8080

内部维护文档见 `_maintain/` 目录。
