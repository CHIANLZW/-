# inchian.top

个人网站。访问根目录 `index.html` 进入站点选择页。

## Agent 工作区（Cursor / mimocod）

| 项 | 路径 / 链接 |
|----|-------------|
| **本地仓库** | `D:\agent\inchian-top` |
| **GitHub** | https://github.com/CHIANLZW/- |
| **Agent 说明** | 根目录 `AGENTS.md` |
| **一键菜单** | 双击 `start-agent.bat` |
| **mimocod（在本仓库运行）** | `D:\mimocod\bin\mimocod-agent.cmd` |

在 Cursor 中：**文件 → 打开文件夹** → 选择 `D:\agent\inchian-top`，或打开 `inchian.top.code-workspace`。

## 本地运行

### 观点 / 小米分析（guandian）— 推荐

**无需 npm start**：

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
