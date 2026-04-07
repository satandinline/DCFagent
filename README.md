# DCF 估值分析智能代理

基于大语言模型（MiniMax-M2.7-highspeed）与自动化工作流的 DCF（贴现现金流）估值分析智能代理，实现从企业财报自动提取关键财务指标、生成完整 DCF 估值模型的功能。

## 🌟 核心特性

- **📄 智能数据提取** — 上传 PDF 财务报告，AI 自动提取结构化财务数据
- **💰 DCF 估值模型** — 自由现金流折现计算企业价值与每股估值
- **📊 敏感性分析** — WACC 与永续增长率多维度敏感性矩阵热力图
- **🤖 AI 估值叙述** — 大语言模型自动生成专业估值分析报告
- **💾 数据持久化** — MySQL 数据库存储历史估值数据与趋势分析
- **🎯 提示词优化** — 15次迭代优化的Few-shot + Chain-of-Thought提示词系统
- **🔍 RAG检索增强** — 三层搜索策略（Yahoo Finance → DuckDuckGo → Google）自动获取实时金融数据
- **🌍 双语支持** — 中文/英文界面切换
- **🌓 暗色模式** — 深色/浅色主题自由切换

## 🛠️ 技术栈


| 层级     | 技术                                             |
| -------- | ------------------------------------------------ |
| 后端     | Python 3.11+, FastAPI, Uvicorn, Pydantic         |
| LLM      | MiniMax-M2.7-highspeed (OpenAI 兼容接口)         |
| PDF 解析 | PyMuPDF / pdfplumber (智能页码选择)                     |
| 数据库   | MySQL 8.0+, PyMySQL, SQLAlchemy                  |
| 搜索服务 | yfinance, ddgs (DuckDuckGo), googlesearch-python |
| 前端     | React 18, TypeScript, Vite                       |
| UI 组件  | Ant Design 5, TailwindCSS                        |
| 图表     | ECharts (echarts-for-react)                      |
| 状态管理 | Zustand                                          |
| 国际化   | react-i18next                                    |

## 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:satandinline/DCFagent.git
cd dcfestimate
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入你的 MiniMax API Key 和数据库配置：

```
MINIMAX_API_KEY=your_api_key_here
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_PORT=3306
MYSQL_DATABASE=dcf_estimation
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

**重要**: 确保当前工作目录是项目根目录 `dcfestimate`。

**后端**：

```bash
# 从项目根目录运行，使用5050端口
uvicorn backend.main:app --reload --port 5050
```

**前端**：

```bash
# 进入frontend目录
cd frontend

# 运行开发服务器
npm run dev
```

访问 http://localhost:3000

**注意**: 如果前端端口3000被占用,Vite会自动使用下一个可用端口(如3001)。

## 🏗️ 项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DCF Valuation System                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
┌───────▼────────┐                              ┌──────────▼──────────┐
│   Frontend     │                              │      Backend         │
│  (React + TS)  │◄──── HTTP/REST API ────────►│    (FastAPI)         │
└────────────────┘                              └─────────────────────┘
        │                                                   │
        │                                                   │
┌───────▼────────────────────────┐             ┌──────────▼──────────────────┐
│       UI Components            │             │      API Layer              │
│                                │             │                             │
│ • FileUpload.tsx              │             │ • /api/upload.py           │
│ • ParamPanel.tsx              │             │ • /api/analysis.py         │
│ • CashFlowChart.tsx           │             │ • /api/report.py           │
│ • SensitivityTable.tsx        │             └──────────┬──────────────────┘
│ • WaterfallChart.tsx          │                        │
│ • DCFResult.tsx               │             ┌──────────▼──────────────────┐
│ • LanguageSwitch.tsx          │             │    Service Layer            │
└────────────────────────────────┘             │                             │
        │                                      │ • llm_service.py           │
        │                                      │ • pdf_service.py           │
┌───────▼────────────────────────┐             │ • extractor_service.py     │
│      State Management          │             │ • dcf_service.py           │
│       (Zustand)                │             │ • db_service.py            │
│                                │             │ • optimized_prompts.py     │
│ • useStore.ts                  │             └──────────┬──────────────────┘
└────────────────────────────────┘                        │
        │                                      ┌──────────▼──────────────────┐
        │                                      │    Data Layer               │
┌───────▼────────────────────────┐             │                             │
│     i18n (react-i18next)       │             │ ┌───────────────────────┐  │
│                                │             │ │   MySQL Database      │  │
│ • zh.json                      │             │ │                       │  │
│ • en.json                      │             │ │ • stocks              │  │
└────────────────────────────────┘             │ │ • asset_profiles      │  │
                                               │ │ • income_statements   │  │
┌────────────────────────────────┐             │ │ • balance_sheets      │  │
│    External Services           │             │ │ • cash_flows          │  │
│                                │             │ │ • historical_prices   │  │
│ ┌──────────────────────────┐  │             │ │ • valuation_results   │  │
│ │  MiniMax LLM API         │  │             │ └───────────────────────┘  │
│ │                          │  │             └─────────────────────────────┘
│ │ • Financial Extraction   │  │
│ │ • Narrative Generation   │  │
│ │ • Optimized Prompts      │  │
│ └──────────────────────────┘  │
│                               │
│ ┌──────────────────────────┐  │
│ │  PDF Parser              │  │
│ │  (pdfplumber)            │  │
│ └──────────────────────────┘  │
└────────────────────────────────┘
```

### 数据流向

```
用户上传PDF
    │
    ▼
┌─────────────┐
│ PDF Upload  │ ──► pdfplumber 提取文本
└─────────────┘
    │
    ▼
┌──────────────────┐
│ LLM Extraction   │ ──► 优化后的Prompt (Iteration 2)
│ (Few-shot + CoT) │     提取结构化财务数据
└──────────────────┘
    │
    ▼
┌──────────────┐
│ Save to DB   │ ──► MySQL存储历史数据
└──────────────┘
    │
    ▼
┌──────────────┐
│ DCF Engine   │ ──► 计算FCF、WACC、终值
└──────────────┘
    │
    ├─────────────┬──────────────┐
    ▼             ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────┐
│Charts  │ │Sensitivity│ │Narrative │
│可视化  │ │敏感性分析  │ │AI报告    │
└────────┘ └──────────┘ └──────────┘
    │             │              │
    └─────────────┴──────────────┘
                  │
                  ▼
          ┌──────────────┐
          │ Save Results │ ──► 估值结果存入数据库
          └──────────────┘
```

## 📁 项目结构

```
dcfestimate/
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 环境配置（含MySQL）
│   ├── init_db.py               # 数据库初始化脚本
│   ├── requirements.txt         # Python依赖
│   ├── .env                     # 环境变量（API Key, DB配置）
│   ├── api/
│   │   ├── upload.py            # PDF 上传与数据提取
│   │   ├── analysis.py          # DCF 计算、敏感性分析、趋势查询
│   │   └── report.py            # 报告导出（预留）
│   ├── services/
│   │   ├── llm_service.py       # MiniMax LLM 封装（含优化Prompt）
│   │   ├── pdf_service.py       # PDF 文本提取
│   │   ├── extractor_service.py # LLM 财务数据提取（集成DB保存+RAG）
│   │   ├── dcf_service.py       # DCF 计算引擎（集成DB存取）
│   │   ├── db_service.py        # MySQL 数据库服务
│   │   ├── rag_service.py       # RAG检索增强生成服务
│   │   └── web_search_service.py # 三层搜索服务（Yahoo/DuckDuckGo/Google）
│   ├── models/
│   │   └── schemas.py           # Pydantic 数据模型
│   ├── examples/                # 使用示例
│   │   ├── db_usage_example.py  # 数据库基础用法
│   │   ├── integration_example.py # 完整集成示例
│   │   ├── prompt_usage_example.py # Prompt使用示例
│   │   ├── rag_usage_example.py # RAG功能示例
│   │   └── yahoo_finance_demo.py # Yahoo Finance演示
│   └── temp_uploads/            # 临时文件目录
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   │   ├── HomePage.tsx     # 首页
│   │   │   ├── AnalysisPage.tsx # 分析页
│   │   │   └── ResultPage.tsx   # 结果页
│   │   ├── components/          # UI 组件
│   │   │   ├── FileUpload.tsx   # 文件上传
│   │   │   ├── ParamPanel.tsx   # 参数面板
│   │   │   ├── CashFlowChart.tsx # 现金流图表
│   │   │   ├── SensitivityTable.tsx # 敏感性表格
│   │   │   ├── WaterfallChart.tsx # 瀑布图
│   │   │   ├── DCFResult.tsx    # DCF结果展示
│   │   │   └── LanguageSwitch.tsx # 语言切换
│   │   ├── services/            # API 服务
│   │   │   └── api.ts           # Axios封装
│   │   ├── store/               # Zustand 状态管理
│   │   │   └── useStore.ts      # 全局状态
│   │   ├── types/               # TypeScript 类型
│   │   │   └── index.ts         # 类型定义
│   │   └── i18n/                # 国际化翻译
│   │       ├── zh.json          # 中文
│   │       ├── en.json          # 英文
│   │       └── index.ts         # i18n配置
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── prompt_file/                 # Excel Prompt模板
│   ├── 6_dcf_model_1_0.xlsx
│   ├── 15_multiples_analysis_0_0.xlsx
│   └── VC Valuation _ Multi-Year _ Advance Template.xlsx
├── start.py                     # 一键启动脚本
└── README.md                    # 项目文档
```

## 🔌 API 接口


| 方法 | 路径                              | 说明                              |
| ---- | --------------------------------- | --------------------------------- |
| GET  | `/api/health`                     | 健康检查                          |
| POST | `/api/extract/upload`             | 上传 PDF 并提取财务数据           |
| POST | `/api/extract/text`               | 从文本提取财务数据                |
| POST | `/api/calculate`                  | 运行 DCF 估值计算（自动保存到DB） |
| POST | `/api/sensitivity`                | 生成敏感性分析矩阵                |
| POST | `/api/narrative`                  | 生成 AI 估值叙述                  |
| GET  | `/api/trends/{ticker}`            | 获取历史趋势分析                  |
| GET  | `/api/load-from-db/{ticker}`      | 从数据库加载财务数据              |
| GET  | `/api/valuation-history`           | 获取所有估值历史记录                |
| GET  | `/api/valuation-history/{ticker}` | 获取指定股票估值历史记录             |

## 📐 DCF 计算公式

- **FCFF** = NOPAT + D&A − CapEx − ΔNWC
- **WACC** = E/(E+D) × Re + D/(E+D) × Rd × (1−T)，其中 Re = Rf + β × (Rm − Rf)
- **终端价值** = FCF × (1+g) / (WACC − g)
- **企业价值** = Σ PV(FCF) + PV(终端价值)
- **每股价值** = (企业价值 − 总债务 + 现金) / 流通股数

## 💡 参数输入

系统支持直观的百分比输入方式：

| 参数 | 输入示例 | 说明 |
|------|----------|------|
| 营业收入增长率 | `5` | 表示 5% |
| 营业利润率 | `15` | 表示 15% |
| 税率 | `25` | 表示 25% |
| WACC | `10` | 表示 10% |
| 无风险利率 | `3` | 表示 3% |

系统会自动在显示时添加 `%` 后缀，并在计算时转换为小数格式。

## 💾 数据库配置

### MySQL 设置

1. 确保 MySQL 8.0+ 已安装并运行
2. 编辑 `backend/.env` 配置数据库连接：

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_PORT=3306
MYSQL_DATABASE=dcf_estimation
```

3. 初始化数据库：

```bash
cd backend
python init_db.py
```

这将创建以下数据表：

- `stocks` - 股票基础信息
- `asset_profiles` - 公司档案
- `income_statements` - 利润表
- `balance_sheets` - 资产负债表
- `cash_flows` - 现金流量表
- `historical_prices` - 历史股价
- `valuation_results` - 估值结果记录

### 数据库功能

✅ **自动保存**：PDF提取的财务数据自动存入数据库
✅ **历史追踪**：记录每次估值结果，支持趋势分析
✅ **快速加载**：从数据库加载历史数据进行重新估值
✅ **趋势分析**：计算CAGR、利润率等关键指标

本项目实现了强大的PDF智能解析系统和RAG（Retrieval-Augmented Generation）系统，结合两层技术显著提升DCF估值的准确性和效率。

### 📄 PDF 智能页码选择

A股年报结构特点：
- **前20页**：包含公司基本情况、主要会计数据、财务指标摘要
- **最后2页**：包含完整的财务报表（资产负债表、利润表、现金流量表）
- **中间页**：主要是文字描述、业务分析，对DCF直接有用的数据较少

```
500页PDF年报
    │
    ├── 前20页 ──► 主要会计数据、财务指标
    │
    ├── 中间页 (20~倒数第3页) ──► 业务分析（跳过）
    │
    └── 最后2页 ──► 完整财务报表
    │
    共扫描22页 → 高效提取关键数据
```

**财务表页识别**：系统自动识别合并资产负债表、利润表、现金流量表等关键页。

### 🔍 RAG 三层搜索架构

```
用户上传PDF + 公司名称/股票代码
            │
            ▼
    ┌───────────────┐
    │ RAG Service   │
    └───────┬───────┘
            │
            ├─ Step 1: 数据库检索 ← 最快、最可靠
            │   ✓ 历史财务数据
            │   ✓ 过往估值记录
            │   ✓ 增长趋势分析
            │
            ├─ Step 2: Yahoo Finance ← 专业金融数据（如有ticker）
            │   ✓ 实时股价、市值
            │   ✓ Beta值、P/E比率
            │   ✓ 财务报表数据
            │   ✓ 利润率等关键指标
            │
            ├─ Step 3: DuckDuckGo ← 通用搜索（稳定可靠）
            │   ✓ 公司新闻、行业动态
            │   ✓ 市场背景信息
            │   ✓ 投资者关系页面
            │
            └─ Step 4: Google Search ← 最后备选
                ✓ 补充搜索结果
              
            │
            ▼
    ┌───────────────┐
    │ Enhanced Text │ ← PDF + 所有检索信息
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ LLM Analysis  │ ← 更准确的DCF估值
    └───────────────┘
```

### 搜索服务特点


| 数据源            | 优先级 | 优势         | 适用场景             |
| ----------------- | ------ | ------------ | -------------------- |
| **数据库**        | 1st    | 最快、最可靠 | 历史数据检索         |
| **Yahoo Finance** | 2nd    | 专业金融数据 | 实时股价、Beta、市值 |
| **DuckDuckGo**    | 3rd    | 稳定、免费   | 通用搜索、新闻       |
| **Google Search** | 4th    | 广泛覆盖     | 备选方案             |

### 使用 RAG

```python
# 上传PDF时启用RAG
result = await extract_from_text(
    text=pdf_text,
    company_name="Apple Inc.",
    ticker="AAPL",      # 提供ticker触发Yahoo Finance
    use_rag=True,       # 启用RAG
    use_web_search=True # 允许联网搜索
)

# 系统会自动：
# 1. 从数据库检索历史数据
# 2. 从Yahoo Finance获取实时数据（如有ticker）
# 3. 从DuckDuckGo搜索最新信息
# 4. 合并所有信息进行AI分析
# 5. 生成更准确的DCF估值
```

### 容错机制

✅ **自动重试**：Yahoo Finance限流时自动重试3次（3s→6s→10s）
✅ **智能降级**：某一层失败时自动切换到下一层
✅ **Mock兜底**：全部失败时使用模拟数据保证系统稳定
✅ **完全免费**：所有搜索服务无需API密钥

---

## 🎯 提示词优化系统

本项目实现了基于15次迭代的提示词优化系统，通过Few-shot Learning和Chain-of-Thought技术，显著提升了LLM提取财务数据的准确性和效率。

### 优化成果

- **质量提升**：从 6.67/10 提升至 **10.00/10** (+50%)
- **成本降低**：最优token消耗（2,640 tokens）
- **速度提升**：响应时间减少 30%（38s → 27s）
- **稳定性**：100%结构化JSON输出

### 优化后的Prompt特点

1. **Few-shot Examples**：提供具体示例引导LLM
2. **Chain-of-Thought**：逐步推理提高准确性
3. **Structured Output**：明确JSON格式要求
4. **Business Constraints**：设定合理的业务约束
5. **Concise & Effective**：简洁高效的设计

### 使用优化Prompt

系统默认启用优化后的Prompt（Iteration 2），无需额外配置。如需切换不同版本：

```python
# 在 extractor_service.py 中
result = await extract_from_text(
    pdf_text,
    use_optimized_prompt=True,
    prompt_type='balanced'  # 或 'concise', 'detailed'
)
```

## 🚀 快速启动

### 方式一：一键启动（推荐）

```bash
python start.py              # 本地模式
python start.py --public     # 公网访问模式（ngrok）
```

### 方式二：分别启动

**后端：**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm run dev
```

访问 http://localhost:3000

## 📝 使用流程

1. **上传财报**：拖拽或选择PDF文件上传
2. **输入公司信息**：填写公司名称和股票代码（可选，但推荐）
3. **RAG检索增强**：系统自动从数据库、Yahoo Finance、DuckDuckGo获取实时数据
4. **自动提取**：AI结合PDF内容和检索信息提取财务数据
5. **调整参数**：根据需要修改增长率、WACC等假设
6. **查看结果**：
   - DCF估值结果（企业价值、每股价值）
   - 现金流预测图表
   - 敏感性分析热力图
   - AI生成的投资叙述报告
7. **历史对比**：查看该股票的历史估值记录
8. **趋势分析**：分析收入、利润增长趋势

## 🛡️ 注意事项

- `.env` 文件包含敏感信息，请勿提交到版本控制
- 首次使用前需运行 `python init_db.py` 初始化数据库
- 确保 MiniMax API Key 有效且有足够配额
- PDF文件应为清晰的财务报告，包含完整财务数据
- **推荐提供股票代码**：能触发Yahoo Finance获取高质量实时数据
- **网络要求**：Yahoo Finance、DuckDuckGo需要网络连接（建议使用VPN）
- **限流处理**：Yahoo Finance有速率限制，系统会自动重试和降级

## 📄 License

MIT License
