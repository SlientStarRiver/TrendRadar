# TrendRadar 部署与使用指南

## 项目概述

TrendRadar 是一个 AI 资讯热点聚合工具，自动抓取各大平台热榜 + RSS 订阅，通过关键词/AI 筛选后推送到微信（PushPlus），同时生成 Obsidian 兼容的 Markdown 笔记用于归档。

**核心流程：**
```
爬虫抓取 → 关键词/AI 筛选 → 推送通知 → HTML 报告 → Obsidian Markdown
```

---

## 项目结构

```
TrendRadar/
├── trendradar/                  # Python 主程序
│   ├── __main__.py              # 入口，调度整个流程
│   ├── context.py               # 应用上下文（全局状态管理）
│   ├── core/                    # 核心模块
│   │   ├── config.py            # 配置加载与校验
│   │   ├── scheduler.py         # 调度系统（时间段控制）
│   │   ├── analyzer.py          # 数据分析（关键词匹配统计）
│   │   ├── frequency.py         # 热词频率统计
│   │   ├── loader.py            # 配置文件加载器
│   │   ├── data.py              # 数据模型
│   │   └── cdn.py               # CDN 加速 / 请求容错
│   ├── crawler/                 # 爬虫模块
│   │   ├── fetcher.py           # 热榜数据抓取（调用 newsnow API）
│   │   └── rss/                 # RSS 子模块
│   │       ├── fetcher.py       # RSS 抓取
│   │       └── parser.py        # RSS/Atom 解析
│   ├── ai/                      # AI 能力模块
│   │   ├── client.py            # LLM 客户端（LiteLLM 封装）
│   │   ├── analyzer.py          # AI 分析报告生成
│   │   ├── filter.py            # AI 智能筛选（替代关键词）
│   │   ├── translator.py        # AI 翻译
│   │   ├── formatter.py         # AI 输出格式化
│   │   └── prompt_loader.py     # 提示词模板加载
│   ├── notification/            # 推送通知模块
│   │   ├── dispatcher.py        # 推送调度（决定何时推）
│   │   ├── senders.py           # 各渠道发送实现
│   │   ├── formatters.py        # 消息格式化
│   │   ├── renderer.py          # Markdown 渲染
│   │   ├── splitter.py          # 长消息拆分
│   │   └── batch.py             # 批量推送
│   ├── report/                  # 报告生成模块
│   │   ├── generator.py         # 报告生成主逻辑
│   │   ├── formatter.py         # 文本报告格式化
│   │   ├── html.py              # HTML 报告生成
│   │   ├── rss_html.py          # RSS 专用 HTML
│   │   └── helpers.py           # 报告辅助函数
│   ├── storage/                 # 存储模块
│   │   ├── base.py              # 存储基类
│   │   ├── local.py             # 本地文件存储
│   │   ├── remote.py            # 远程 S3 存储
│   │   ├── manager.py           # 存储管理器
│   │   └── sqlite_mixin.py      # SQLite 混入
│   └── utils/                   # 工具函数
│       ├── time.py              # 时间处理
│       └── url.py               # URL 处理
├── config/                      # 配置文件
│   ├── config.yaml              # 主配置（数据源/筛选/推送/AI）
│   ├── frequency_words.txt      # 关键词列表（AI 聚焦版）
│   ├── ai_interests.txt         # AI 筛选兴趣描述
│   ├── ai_analysis_prompt.txt   # AI 分析提示词
│   ├── ai_translation_prompt.txt# AI 翻译提示词
│   ├── ai_filter/               # AI 筛选提示词模板
│   └── timeline.yaml            # 调度时间线定义
├── scripts/                     # 辅助脚本
│   └── generate_obsidian_md.py  # SQLite → Obsidian Markdown 转换
├── obsidian_vault/              # Obsidian Vault 目录
│   ├── .obsidian/               # Obsidian 配置
│   ├── Daily/                   # 每日热点汇总笔记
│   ├── AI/                      # 按来源分类的笔记
│   └── Templates/               # 笔记模板
├── output/                      # 运行输出（自动 git commit）
│   ├── news/                    # 热榜 SQLite 数据库
│   ├── rss/                     # RSS SQLite 数据库
│   ├── html/                    # HTML 报告
│   ├── markdown/                # Markdown 报告
│   └── index.html               # 最新 HTML 报告（根目录副本）
├── .github/workflows/
│   ├── crawler.yml              # 主爬虫 workflow（每天 2 次）
│   ├── clean-crawler.yml        # 清理旧数据
│   └── docker.yml               # Docker 构建
├── .gitignore                   # 排除 SQLite .db，保留 HTML/Markdown
├── pyproject.toml               # Python 依赖
└── requirements.txt             # 依赖列表
```

---

## 各模块功能详解

### 1. 爬虫模块 (`trendradar/crawler/`)

| 文件 | 功能 |
|------|------|
| `fetcher.py` | 调用 newsnow API 抓取各平台热榜数据，支持域名安全校验 |
| `rss/fetcher.py` | 抓取 RSS/Atom 订阅源 |
| `rss/parser.py` | 解析 RSS XML，提取标题/链接/发布时间 |

**数据源：**
- 热榜：通过 newsnow 开源项目的 API 聚合（今日头条、百度、B站、知乎等）
- RSS：直接抓取订阅源（Hacker News、36氪等）

### 2. AI 模块 (`trendradar/ai/`)

| 文件 | 功能 |
|------|------|
| `client.py` | LLM 客户端，基于 LiteLLM，支持 DeepSeek/OpenAI/Gemini 等 |
| `analyzer.py` | 生成 AI 分析报告（趋势洞察、热点解读） |
| `filter.py` | AI 智能筛选，替代关键词匹配（更灵活但消耗 token） |
| `translator.py` | 标题翻译（英文 → 中文等） |
| `prompt_loader.py` | 加载 `config/` 下的提示词模板文件 |

### 3. 推送模块 (`trendradar/notification/`)

| 文件 | 功能 |
|------|------|
| `dispatcher.py` | 根据调度配置决定是否推送 |
| `senders.py` | 各渠道发送实现（飞书/钉钉/企微/Telegram/邮件/Bark/Slack/通用Webhook） |
| `formatters.py` | 将数据格式化为各渠道要求的消息格式 |
| `renderer.py` | Markdown 渲染（适配不同平台语法差异） |
| `splitter.py` | 长消息自动拆分（飞书/钉钉有长度限制） |

### 4. 报告模块 (`trendradar/report/`)

| 文件 | 功能 |
|------|------|
| `generator.py` | 报告生成主逻辑（聚合热榜+RSS数据） |
| `html.py` | 生成 HTML 可视化报告（含 ECharts 图表） |
| `formatter.py` | 纯文本报告格式化 |

### 5. 存储模块 (`trendradar/storage/`)

| 文件 | 功能 |
|------|------|
| `local.py` | 本地 SQLite + HTML/TXT 文件存储 |
| `remote.py` | 远程 S3 兼容存储（R2/OSS/COS） |
| `manager.py` | 存储后端选择与管理 |
| `sqlite_mixin.py` | SQLite 数据库操作封装 |

### 6. 核心模块 (`trendradar/core/`)

| 文件 | 功能 |
|------|------|
| `config.py` | 加载 `config.yaml`，校验配置合法性 |
| `scheduler.py` | 调度系统，根据时间段决定执行什么操作 |
| `analyzer.py` | 关键词匹配统计，计算热度得分 |
| `frequency.py` | 热词出现频率追踪（跨次抓取对比） |

### 7. Obsidian 转换 (`scripts/`)

| 文件 | 功能 |
|------|------|
| `generate_obsidian_md.py` | 读取 SQLite 数据库，生成 Obsidian Markdown 笔记 |

---

## 配置文件说明

### `config/config.yaml` — 主配置

分 11 个配置段：

| 段 | 作用 | 关键配置 |
|----|------|----------|
| 1. app | 基础设置 | 时区 `Asia/Shanghai` |
| 2. platforms | 热榜数据源 | 平台 ID、域名校验 |
| 3. rss | RSS 订阅 | 订阅 URL、新鲜度过滤 |
| 4. report | 报告模式 | `daily`/`current`/`incremental` |
| 4.5 filter | 筛选策略 | `keyword`（关键词）或 `ai`（AI 智能） |
| 5. display | 推送内容控制 | 区域顺序、独立展示区 |
| 6. notification | 推送渠道 | 各渠道 webhook 配置 |
| 7. storage | 存储配置 | 本地/远程 S3 |
| 8. ai | AI 模型 | 模型名、API Key |
| 9. ai_analysis | AI 分析 | 语言、提示词、分析模式 |
| 10. ai_translation | AI 翻译 | 目标语言、翻译范围 |
| 11. advanced | 高级设置 | 调试模式、爬虫参数 |

### `config/frequency_words.txt` — 关键词列表

每行一个关键词，用于热榜标题匹配。当前配置为 AI 聚焦版：

```
大模型
AI Agent
AI编程
GPT
Claude
DeepSeek
```

匹配逻辑：标题包含任一关键词即命中，支持多行词组（用空格连接）。

### `config/ai_interests.txt` — AI 筛选兴趣描述

自然语言描述你的兴趣方向，供 AI 筛选时参考（仅 `filter.method=ai` 时生效）。

---

## 部署方式

### 方式一：GitHub Actions（推荐）

**优点：** 免费、无需服务器、自动运行

**步骤：**

1. Fork 仓库到你的 GitHub 账号
2. 配置 GitHub Secrets（Settings → Secrets → Actions）：

   | Secret 名 | 值 | 说明 |
   |-----------|---|------|
   | `GENERIC_WEBHOOK_URL` | `https://www.pushplus.plus/send` | PushPlus API 地址 |
   | `GENERIC_WEBHOOK_TEMPLATE` | `{"token":"你的token","title":"{title}","content":"{content}","template":"markdown"}` | 推送模板 |
   | `AI_API_KEY` | 你的 DeepSeek API key | 可选，AI 分析用 |

3. 启用 GitHub Actions（Settings → Actions → Enable）
4. 手动触发一次验证：Actions → Get Hot News → Run workflow

**自动运行时间：** 每天北京时间 8:00 和 20:00

**注意：** 每 7 天需要在 Actions 页面运行 `Check In` workflow 续期，否则自动停止。

### 方式二：Docker

```bash
docker build -t trendradar .
docker run -v $(pwd)/config:/app/config -v $(pwd)/output:/app/output trendradar
```

### 方式三：本地运行

```bash
pip install -r requirements.txt
python -m trendradar
```

---

## Obsidian 集成

### 目录结构

```
obsidian_vault/
├── .obsidian/           # Obsidian 配置（外观、插件）
├── Daily/               # 每日汇总笔记
│   └── 2026-06-11.md    # 日期命名
├── AI/                  # 按来源分类
│   ├── bilibili_热搜_2026-06-11.md
│   ├── 百度热搜_2026-06-11.md
│   └── ...
└── Templates/           # 笔记模板
```

### 工作流程

```
GitHub Actions 跑爬虫
    ↓
生成 SQLite 数据库（output/news/、output/rss/）
    ↓
generate_obsidian_md.py 读取 SQLite
    ↓
生成 Markdown 到 obsidian_vault/
    ↓
git commit + push
    ↓
本地 git pull（每 30 分钟自动同步）
    ↓
Obsidian 打开 vault 目录查看
```

### 手动同步

```bash
cd D:\Projects\TrendRadarVault
git pull
```

### 自动同步

已配置 Windows 定时任务 `TrendRadarSync`，每 30 分钟自动执行 `git pull`。

查看任务状态：
```powershell
Get-ScheduledTask -TaskName "TrendRadarSync"
```

手动触发：
```powershell
schtasks /Run /TN "TrendRadarSync"
```

---

## 我做了哪些改动

### 1. `config/config.yaml` — 精简数据源

**改动：** 去掉非 AI 相关平台，保留 AI/科技/财经聚焦源

| 保留 | 去掉 |
|------|------|
| 今日头条、百度、华尔街见闻、澎湃新闻、B站、财联社、知乎 | 凤凰网、贴吧、微博、抖音 |

新增 36氪 RSS 订阅。

### 2. `config/frequency_words.txt` — AI 聚焦关键词

**改动：** 原版是通用热点词，改为 AI/科技聚焦

```
大模型 / LLM / GPT / Claude / DeepSeek / Gemini / Qwen
AI Agent / MCP / AI 编程 / Cursor
AGI / 具身智能 / 量子计算 / 芯片
```

### 3. `.github/workflows/crawler.yml` — 运行频率 + 自动提交

**改动：**

| 项目 | 原版 | 改后 |
|------|------|------|
| 运行频率 | 每小时 1 次 | 每天 2 次（8:00/20:00） |
| permissions | `contents: read` | `contents: write` |
| 新增步骤 | 无 | Generate Obsidian Markdown |
| 新增步骤 | 无 | Commit and push results |

### 4. `scripts/generate_obsidian_md.py` — 新增

读取 SQLite 数据库，生成 Obsidian 兼容的 Markdown 文件：
- 每日汇总笔记 → `obsidian_vault/Daily/{date}.md`
- 按来源分类笔记 → `obsidian_vault/AI/{source}_{date}.md`

### 5. `obsidian_vault/` — 新增

Obsidian Vault 目录结构，包含 `.obsidian` 配置、Daily/AI/Templates 目录。

### 6. `.gitignore` — 新增

排除 SQLite `.db` 文件（太大，每次运行生成），保留 HTML 和 Markdown。

### 7. `C:\Users\唐永屹\scripts\sync_trendradar.ps1` — 新增

Windows 自动同步脚本，配合定时任务每 30 分钟 `git pull`。

---

## 常见问题

### Q: 推送没收到？
- 检查 GitHub Secrets 是否配置正确
- 确认 PushPlus token 有效（去 pushplus.plus 查看）
- 查看 Actions 日志是否有报错

### Q: AI 分析没生成？
- 需要配置 `AI_API_KEY` Secret
- 确认 DeepSeek API key 有效且有余额

### Q: Obsidian 没看到新笔记？
- 确认 vault 目录已 `git pull`
- 检查定时任务是否在运行：`Get-ScheduledTask -TaskName "TrendRadarSync"`

### Q: 想加新的 RSS 源？
编辑 `config/config.yaml`，在 `rss.feeds` 下添加：
```yaml
- id: "my-feed"
  name: "我的订阅"
  url: "https://example.com/feed"
```

### Q: 想改关键词？
编辑 `config/frequency_words.txt`，每行一个关键词。

### Q: 7 天后停止了？
去 GitHub Actions 页面运行 `Check In` workflow 续期。
