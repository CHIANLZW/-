# 重庆苍凌工作室 — inchian.top

纯静态个人作品集网站。部署时将**根目录**作为 Web 根路径即可（`index.html` 为首页）。

---

## 项目总览

| 路径 | 类型 | 说明 |
|------|------|------|
| `index.html` | 页面 | 首页：品牌介绍、FPV / 低空 / 影视 / 工程入口 |
| `about.html` | 页面 | 关于页 |
| `contact.html` | 页面 | 联系页（微信等） |
| `low-altitude.html` | 页面 | 低空产业专页（适航 / eVTOL / 无人机 / 培训 四大板块） |
| `portfolio.html` | 页面 | 作品集总览 |
| `css/style.css` | 样式 | 全站样式（导航、板块、证件画廊、响应式等） |
| `js/main.js` | 脚本 | 导航菜单、滚动动画、通用交互 |
| `js/credentials.js` | 脚本 | 从 manifest 动态加载证件展示画廊 |
| `projects/mazda323.html` | 页面 | Mazda 323 改装项目详情 |
| `scripts/process_credentials.py` | 工具 | 证件分类、隐私打码、生成展示图与 manifest |
| `assets/` | 资源 | **网站公开素材**（图片、视频、数据，可部署） |
| `_source/` | 素材库 | **原始素材与备份**（不直接对外发布，含敏感证件） |
| `_archive/` | 归档 | 与本站无关的旧项目，保留备查 |

---

## 目录结构（完整列表）

```
inchian.top/
│
├── index.html                  # 首页
├── about.html                  # 关于
├── contact.html                # 联系
├── low-altitude.html           # 低空产业（四板块专页）
├── portfolio.html              # 作品集
├── README.md                   # 本文件：项目说明与目录索引
│
├── css/
│   └── style.css               # 全站 CSS
│
├── js/
│   ├── main.js                 # 全站交互
│   └── credentials.js          # 证件画廊加载（读取 assets/data/manifest）
│
├── projects/
│   └── mazda323.html           # 汽车改装子项目页
│
├── scripts/
│   └── process_credentials.py  # 证件处理流水线（见下方「维护命令」）
│
├── assets/                     # ── 网站公开资源 ──
│   ├── data/
│   │   └── credentials-manifest.json   # 证件展示元数据（标题、路径、来源）
│   ├── images/
│   │   ├── caac/               # 低空·适航板块配图（8 张）
│   │   ├── car/                # Mazda 323 项目照片（10 张）
│   │   ├── credentials/        # 证件展示图（脚本生成，已打码）
│   │   │   ├── training/       #   培训资质（合格证、大纲、手册等）
│   │   │   ├── airspace/       #   空域批件 / 批复
│   │   │   └── operation/      #   运营合格证
│   │   ├── electronics/        # 电子工程 / 3D 打印（hero + project）
│   │   ├── film/               # 影视制作配图
│   │   ├── fpv/                # FPV 穿越机摄影主图
│   │   ├── low-altitude/       # 低空通用配图（预留）
│   │   └── portfolio/          # 作品集杂项图库（17 张）
│   └── videos/
│       ├── fpv/
│       │   ├── fpv-showreel.mp4   # FPV 飞行集锦
│       │   └── fpv-flight.mp4     # FPV 短片段
│       └── film/
│           └── film-behind.mp4    # 影视拍摄花絮
│
├── _source/                    # ── 原始素材（勿直接部署）──
│   ├── README.md               # 素材库说明
│   ├── wordpress/
│   │   └── WordPress.2023-11-21.xml    # 旧 WordPress 站点导出备份
│   └── photos/
│       ├── credentials/        # 证件原始 PDF / 图片（含客户资料，敏感）
│       │   └── caac培训资质/   #   按业务分子目录（已获证、运营合格证等）
│       └── portfolio/          # 作品集原始照片（与 assets/images/portfolio 同源）
│
└── _archive/                   # ── 归档项目（与 inchian.top 无关）──
    └── ScribbleHub-backstage/  # 旧小程序后台 UniApp 工程
```

---

## 页面与资源对应关系

| 页面 | 主要引用资源 |
|------|----------------|
| `index.html` | `assets/images/fpv`、`film`、`electronics`；`assets/videos/fpv/`、`film/` |
| `low-altitude.html` | `assets/images/caac`；`credentials.js` → `assets/data/credentials-manifest.json` |
| `portfolio.html` | 各板块 `assets/images/*`；`projects/mazda323.html` |
| `projects/mazda323.html` | `assets/images/car/*` |

---

## 低空产业四板块（`low-altitude.html`）

| 锚点 | 板块 | 内容 |
|------|------|------|
| `#sector-airworthiness` | 01 适航 | TC / PC / AC / STC 审定与标准文件（折叠目录） |
| `#sector-manufacturing` | 02 制造 | 运动类 eVTOL 硬件制造 |
| `#sector-training` | 03 培训资质 | CCAR-92、培训合格证 / 大纲 / 手册案例 |
| `#sector-operations` | 04 空域 · OC | 空域批复、运营合格证（CCAR-92）、申请平台 |

---

## 维护命令

### 本地预览

```bash
npx serve -l 8080
```

浏览器打开 `http://localhost:8080`。

### 重新生成证件展示图

新增或更新 `_source/photos/credentials/` 中的原始文件后：

```bash
py scripts/process_credentials.py
```

脚本会：

1. 扫描 `_source/photos/credentials/` 并按规则分类（training / airspace / operation）
2. 对二维码、手机号、姓名字段做精准打码
3. 输出到 `assets/images/credentials/`
4. 更新 `assets/data/credentials-manifest.json`

依赖：`opencv-python`、`PyMuPDF`、`Pillow`、`rapidocr-onnxruntime`（OCR 可选）。

---

## 已整理的重复项

以下文件曾散落在根目录，已与 `assets/` 合并或删除：

| 原位置 | 处理 |
|--------|------|
| `car/`（根目录） | 与 `assets/images/car/` 完全重复，已删除 |
| `个人web/` | 已迁入 `_source/photos/portfolio/`（网站使用 `assets/images/portfolio/`） |
| `照片素材/证件/` | 已迁入 `_source/photos/credentials/` |
| `0bf2amaiyaaawaakx6nfcrpvaa6drqbqbdaa.f10002.mp4` | 已整理为 `assets/videos/fpv/fpv-showreel.mp4` |
| `WordPress.2023-11-21.xml` | 已迁入 `_source/wordpress/` |
| `ScribbleHub-backstage/` | 已迁入 `_archive/`（与本站无关） |

---

## 部署说明

- 上传至静态托管时，上传**除 `_source/`、`_archive/`、`scripts/` 以外**的文件即可（或整包上传，服务器不暴露 `_` 前缀目录亦可）。
- `_source/photos/credentials/` 含客户敏感信息，**切勿**作为公开静态资源部署。
