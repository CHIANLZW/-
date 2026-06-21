# inchian.top 双平台静态部署指南

> **站点类型**：纯静态 HTML / CSS / JS，无构建步骤  
> **目标**：GitHub Pages + Cloudflare Pages 共用同一 GitHub 仓库，推送 `main` 后双站自动更新  
> **费用**：全程免费 · HTTPS 自动 · 无需备案 · 适合马来西亚等海外访问

---

## 1. 重要说明（请先读）

以下步骤**无法由 AI 代您完成**（涉及您的邮箱、密码、短信/2FA、OAuth 授权，属于平台安全边界）：

| 必须由账号持有人完成的唯一步骤 | 原因 |
|-------------------------------|------|
| 注册 GitHub 账号 | 需邮箱验证、人机验证 |
| 注册 Cloudflare 账号 | 需邮箱验证 |
| Cloudflare 授权连接 GitHub | 浏览器 OAuth 弹窗，需您点「Authorize」 |
| 首次创建 GitHub Personal Access Token（若用脚本推送） | 令牌绑定您的账号 |

**AI / 脚本可自动完成的部分**：整理可部署文件、初始化 Git、推送代码、生成配置、编写排错文档。

本地仓库已就绪：根目录即 Web 根路径，已含 `.nojekyll`、`404.html`、Cloudflare `_headers`，且已排除 `_source/`、`素材/` 等敏感大文件。

---

## 2. 部署架构

```text
本地修改 → git push origin main
                │
    ┌───────────┴───────────┐
    ▼                       ▼
GitHub Pages          Cloudflare Pages
*.github.io           *.pages.dev
（自动从 main 部署）   （关联同一仓库，自动部署）
```

**推送一次，两站同步** — 无需分别上传。

---

## 3. 全流程操作记录

### 阶段 A：GitHub 仓库与 Pages（第一套站点）

#### A1. 注册 GitHub（若尚无账号）

1. 打开 https://github.com/signup  
2. 使用常用邮箱注册，完成验证  
3. 建议开启 **Two-factor authentication（2FA）**

#### A2. 创建公开仓库

1. 登录后点击 **New repository**  
2. 仓库名建议：`inchian-top` 或 `inchian.top`  
3. 选择 **Public**（GitHub Pages 免费版要求公开库）  
4. **不要**勾选「Add README」（本地已有代码）  
5. 创建仓库，记下仓库地址，例如：  
   `https://github.com/YOUR_USERNAME/inchian-top.git`

#### A3. 推送本地代码

在项目根目录 `inchian.top` 打开终端，执行：

```powershell
git remote add origin https://github.com/YOUR_USERNAME/inchian-top.git
git branch -M main
git push -u origin main
```

首次推送时浏览器会弹出 GitHub 登录；或使用 [Personal Access Token](https://github.com/settings/tokens) 作为密码。

#### A4. 开启 GitHub Pages

1. 仓库 → **Settings** → **Pages**  
2. **Source**：Deploy from a branch  
3. **Branch**：`main` → 文件夹选 **`/ (root)`**  
4. 保存后等待 1～3 分钟  

**第一套访问地址（将 YOUR_USERNAME 换成您的用户名）：**

```text
https://YOUR_USERNAME.github.io/inchian-top/
```

若仓库名是 `YOUR_USERNAME.github.io`，则首页为：

```text
https://YOUR_USERNAME.github.io/
```

#### A5. 验证 GitHub Pages

- [ ] 首页 `index.html` 可打开  
- [ ] 浏览器地址栏显示 HTTPS 锁  
- [ ] `low-altitude.html`、图片、视频可加载  
- [ ] 故意访问错误路径，应显示 `404.html`

---

### 阶段 B：Cloudflare Pages（第二套站点）

#### B1. 注册 Cloudflare

1. 打开 https://dash.cloudflare.com/sign-up  
2. 免费计划（Free）即可，**无需绑定域名**也能用 Pages  

#### B2. 创建 Pages 项目并关联 GitHub

1. 左侧 **Workers & Pages** → **Create** → **Pages** → **Connect to Git**  
2. 首次需 **Connect GitHub**，在弹窗中授权 Cloudflare  
3. 选择仓库 `inchian-top` → **Begin setup**  

#### B3. 构建参数（纯静态，无 npm）

| 配置项 | 填写值 |
|--------|--------|
| Production branch | `main` |
| Framework preset | **None** |
| Build command | **留空** |
| Build output directory | **`/`** 或 **`.`** |

点击 **Save and Deploy**，约 1～3 分钟完成。

**第二套访问地址：**

```text
https://inchian-top.pages.dev
```

（实际子域以 Cloudflare 分配为准，可在项目 **Custom domains** 旁查看。）

#### B4. 验证 Cloudflare Pages

- [ ] `https://xxxx.pages.dev/` 可访问  
- [ ] SSL 证书有效（Full 默认即可）  
- [ ] 静态资源 `assets/`、`css/`、`js/` 正常  
- [ ] 从马来西亚/海外网络访问速度正常（Cloudflare 全球 CDN）

---

## 4. 日常更新网站（极简流程）

```powershell
cd c:\Users\28295\Desktop\inchian.top

# 1. 改完 HTML/CSS/JS/图片后
git add .
git commit -m "更新：简要说明改了什么"
git push origin main
```

**无需其他操作。** 通常 1～5 分钟内：

- GitHub Pages 自动刷新  
- Cloudflare Pages 检测到 push 后自动重新部署  

---

## 5. 双平台对比

| 对比项 | GitHub Pages | Cloudflare Pages |
|--------|--------------|------------------|
| 费用 | 免费（公开仓库） | 免费 |
| 默认域名 | `username.github.io/repo` | `项目名.pages.dev` |
| 自定义域名 | 支持（CNAME + 仓库 Settings） | 支持（DNS 接入 Cloudflare 更简单） |
| HTTPS | 自动 | 自动 |
| 流量 | 软限制（个人站足够） | 免费版流量充裕，全球 CDN |
| 海外访问（如马来西亚） | 尚可 | **更优**（边缘节点多） |
| 构建 | 本仓库无构建，直接托管静态文件 | 同上 |
| 与 Git 集成 | 原生 | 关联 GitHub 后 push 即部署 |
| 404 自定义 | 根目录 `404.html` | 根目录 `404.html` |
| 缓存 / 头信息 | 基础 | 可用 `_headers` 精细控制 |
| 备案 | 不需要 | 不需要 |

**推荐用法：**

- **GitHub Pages**：主展示、便于分享仓库与版本历史  
- **Cloudflare Pages**：海外访客主入口、备用域名  

---

## 6. 故障排查

### 6.1 404 页面问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 子路径 404 样式丢失 | 404 页用了相对路径 | 已使用 `/css/style.css` 绝对路径 |
| GitHub 子目录站首页 404 | 仓库名不是 `username.github.io` | 访问 URL 须含仓库名：`/inchian-top/` |
| SPA 式路由 404 | 纯静态多页站 | 确保链接指向真实 `.html` 文件 |

### 6.2 部署失败

| 现象 | 处理 |
|------|------|
| GitHub Pages 未更新 | Settings → Pages 确认 branch=main、folder=root；看 Actions 日志 |
| Cloudflare Build failed | 确认 Build command **为空**；Framework 选 None |
| push 被拒绝 | `git pull --rebase origin main` 后再 push |
| 文件过大 | 单文件勿超 100MB；`_source/` 已 gitignore，勿提交 |

### 6.3 资源加载异常

| 现象 | 处理 |
|------|------|
| CSS/JS 404 | 检查路径大小写；GitHub 对大小写敏感 |
| 图片不显示 | 确认文件已 `git add` 并 push；路径在 `assets/` 下 |
| 经典版 `/classic/` 数据加载失败 | 已用 `assetUrl()` 自动加 `../` 前缀 |
| 混合内容警告 | 外链资源改用 `https://` |
| Cloudflare 旧版缓存 | Pages 项目 → Deployments → Retry；或 Purge cache |

### 6.4 SSL / 安全锁异常

- GitHub Pages：等待证书签发（新站最多 24 小时，通常数分钟）  
- Cloudflare：SSL/TLS 模式选 **Full** 即可（静态站无源站证书问题）

---

## 7. 仓库安全清单

以下内容**已排除在 Git 之外**，请勿强行加入公开仓库：

- `_source/` — 原始证件与客户资料（约 1.8GB）  
- `素材/` — 内部审核材料  
- `_archive/` — 归档  

公开仓库仅包含 `assets/` 内已处理的展示图与 manifest。

---

## 8. 可选：自定义域名 inchian.top

若您拥有域名 `inchian.top`：

**GitHub Pages：** 仓库 Settings → Pages → Custom domain → 填 `inchian.top` → DNS 添加 CNAME。

**Cloudflare Pages：** 项目 → Custom domains → 添加域名 → 按提示改 NS 或 CNAME。

同一域名只能指向一个平台；可拆分为 `www` → Cloudflare、`github.` 子域 → GitHub Pages。

---

## 9. 交付物占位（部署完成后填写）

| 项目 | URL |
|------|-----|
| GitHub Pages | `https://YOUR_USERNAME.github.io/inchian-top/` |
| Cloudflare Pages | `https://YOUR_PROJECT.pages.dev/` |

完成 B3/B4 后，将上表中的占位符替换为真实地址即可交付。

---

*文档版本：2026-06-21 · 适配 inchian.top 纯静态站点*
