# DCFagent

AI agent for DCF evaluate.
==========================

# DCF 估值分析智能代理

基于大语言模型（MiniMax-M2.7-highspeed）与自动化工作流的 DCF（贴现现金流）估值分析智能代理，实现从企业财报自动提取关键财务指标、生成完整 DCF 估值模型的功能。

## 功能特性

- **智能数据提取** — 上传 PDF 财务报告，AI 自动提取结构化财务数据
- **DCF 估值模型** — 自由现金流折现计算企业价值与每股估值
- **敏感性分析** — WACC 与永续增长率多维度敏感性矩阵热力图
- **AI 估值叙述** — 大语言模型自动生成专业估值分析报告
- **双语支持** — 中文/英文界面切换
- **暗色模式** — 深色/浅色主题自由切换

## 技术栈


| 层级     | 技术                                     |
| -------- | ---------------------------------------- |
| 后端     | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| LLM      | MiniMax-M2.7-highspeed (OpenAI 兼容接口) |
| PDF 解析 | pdfplumber                               |
| 前端     | React 18, TypeScript, Vite               |
| UI 组件  | Ant Design 5, TailwindCSS                |
| 图表     | ECharts (echarts-for-react)              |
| 状态管理 | Zustand                                  |
| 国际化   | react-i18next                            |

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd dcfestimate
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入你的 MiniMax API Key 和 Ngrok Token（可选）：

```
MINIMAX_API_KEY=your_api_key_here
NGROK_AUTH_TOKEN=your_ngrok_token_here
```

### 3. 安装后端依赖

```bash
pip install -r backend/requirements.txt
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动开发服务器

#### 方式一：本地开发模式（推荐）

在项目根目录运行一键启动脚本：

```bash
python start.py
```

这将自动：

- ✅ 检查并安装前端依赖
- ✅ 启动前端开发服务器 (http://localhost:3000)
- ✅ 启动后端 API 服务器 (http://localhost:8001)
- ✅ 自动打开浏览器

#### 方式二：手动分步启动

**启动后端：**

```bash
# 在项目根目录执行
uvicorn backend.main:app --reload --port 8001
```

**启动前端（新终端窗口）：**

```bash
cd frontend
npm run dev
```

#### 方式三：公网部署模式

使用 ngrok 将后端 API 暴露到公网：

```bash
python deploy_ngrok_lib.py
```

这将：

- ✅ 自动检查并安装 ngrok 库
- ✅ 启动后端服务
- ✅ 创建 ngrok 隧道
- ✅ 显示公网访问地址
- ✅ 自动打开浏览器查看 API 文档

**访问地址：**

- 本地访问：http://localhost:3000
- 公网访问：https://xxx.ngrok.io（由 ngrok 生成）

## 项目结构

```
dcfestimate/
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 环境配置
│   ├── requirements.txt
│   ├── api/
│   │   ├── upload.py            # PDF 上传与数据提取
│   │   ├── analysis.py          # DCF 计算与敏感性分析
│   │   └── report.py            # 报告导出（预留）
│   ├── services/
│   │   ├── llm_service.py       # MiniMax LLM 封装
│   │   ├── pdf_service.py       # PDF 文本提取
│   │   ├── extractor_service.py # LLM 财务数据提取
│   │   └── dcf_service.py       # DCF 计算引擎
│   └── models/
│       └── schemas.py           # Pydantic 数据模型
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # UI 组件
│   │   ├── services/            # API 服务
│   │   ├── store/               # Zustand 状态管理
│   │   ├── types/               # TypeScript 类型
│   │   └── i18n/                # 国际化翻译
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## API 接口


| 方法 | 路径                  | 说明                    |
| ---- | --------------------- | ----------------------- |
| GET  | `/api/health`         | 健康检查                |
| POST | `/api/extract/upload` | 上传 PDF 并提取财务数据 |
| POST | `/api/extract/text`   | 从文本提取财务数据      |
| POST | `/api/calculate`      | 运行 DCF 估值计算       |
| POST | `/api/sensitivity`    | 生成敏感性分析矩阵      |
| POST | `/api/narrative`      | 生成 AI 估值叙述        |

## DCF 计算公式

- **FCFF** = NOPAT + D&A − CapEx − ΔNWC
- **WACC** = E/(E+D) × Re + D/(E+D) × Rd × (1−T)，其中 Re = Rf + β × (Rm − Rf)
- **终端价值** = FCF × (1+g) / (WACC − g)
- **企业价值** = Σ PV(FCF) + PV(终端价值)
- **每股价值** = (企业价值 − 总债务 + 现金) / 流通股数
