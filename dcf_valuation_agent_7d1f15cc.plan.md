---
name: DCF Valuation Agent
overview: Build a full-stack DCF (Discounted Cash Flow) valuation analysis intelligent agent with Python FastAPI backend and React frontend, powered by MiniMax-M2.7-highspeed LLM for automated financial data extraction and valuation modeling, with bilingual (CN/EN) support.
todos:
  - id: backend-setup
    content: "Initialize backend: FastAPI project structure, requirements.txt (fastapi, uvicorn, openai, pdfplumber, python-multipart, pydantic, python-dotenv), config, CORS, health endpoint"
    status: pending
  - id: backend-schemas
    content: "Define Pydantic schemas: FinancialData, DCFParameters, DCFResult, SensitivityMatrix, ExtractionResponse"
    status: pending
  - id: backend-pdf
    content: Implement PDF parsing service using pdfplumber to extract text from uploaded financial reports
    status: pending
  - id: backend-llm
    content: "Implement MiniMax LLM service: OpenAI SDK wrapper with base_url=https://api.minimaxi.com/v1, model=MiniMax-M2.7-highspeed, with structured extraction prompt and JSON response parsing"
    status: pending
  - id: backend-extractor
    content: "Build financial data extractor service: send PDF text to LLM with carefully crafted prompt to extract revenue, EBITDA, CapEx, D&A, working capital, tax rate, debt, cash, shares, beta"
    status: pending
  - id: backend-dcf
    content: "Implement DCF calculation engine: FCFF projection, WACC calculation (CAPM), terminal value (Gordon Growth), enterprise value, equity value per share, sensitivity analysis matrix"
    status: pending
  - id: backend-api
    content: "Wire up all API routes: /upload, /extract, /calculate, /sensitivity, /narrative with proper error handling and streaming support for LLM calls"
    status: pending
  - id: frontend-setup
    content: "Initialize React project: Vite + TypeScript + TailwindCSS + Ant Design 5 + ECharts + react-i18next + Zustand + React Router + Axios"
    status: pending
  - id: frontend-i18n
    content: Set up i18n with zh.json and en.json translation files, LanguageSwitch component in header
    status: pending
  - id: frontend-pages
    content: "Build 3 pages: HomePage (hero + CTA), AnalysisPage (input tabs + parameter panel), ResultPage (dashboard with all charts and results)"
    status: pending
  - id: frontend-components
    content: "Build core components: FileUpload (drag-and-drop PDF), ManualInput (Ant Design form), ParamPanel (sliders/inputs for WACC, growth rates, forecast years)"
    status: pending
  - id: frontend-charts
    content: "Build visualization components: CashFlowChart (bar chart), SensitivityTable (heatmap), WaterfallChart (valuation bridge), all using ECharts"
    status: pending
  - id: frontend-integration
    content: "Connect frontend to backend API: upload flow, extraction display with editable fields, calculation trigger, result rendering"
    status: pending
  - id: polish
    content: "Final polish: dark/light mode toggle, responsive design, loading states, error handling, README documentation"
    status: pending
isProject: false
---

# DCF Valuation Analysis Intelligent Agent

## Architecture Overview

```mermaid
graph TB
    subgraph frontend [Frontend - React + Vite + TailwindCSS + Ant Design]
        Upload[PDF Upload / Manual Input]
        Dashboard[Analysis Dashboard]
        Charts[Interactive Charts - ECharts]
        Params[Parameter Adjustment Panel]
        Report[Report Export]
        I18n[i18n - CN/EN Switch]
    end

    subgraph backend [Backend - Python FastAPI]
        API[REST API Layer]
        LLM[MiniMax LLM Service]
        DCFEngine[DCF Calculation Engine]
        PDFParser[PDF Parser - pdfplumber]
        Extractor[Financial Data Extractor]
    end

    subgraph external [External Services]
        MiniMax["MiniMax API (M2.7-highspeed)"]
    end

    Upload --> API
    Dashboard --> API
    Params --> API
    API --> PDFParser
    API --> Extractor
    Extractor --> LLM
    LLM --> MiniMax
    API --> DCFEngine
    DCFEngine --> Dashboard
    DCFEngine --> Charts
    Dashboard --> Report
```



## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic, pdfplumber, OpenAI SDK (MiniMax compatible)
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Ant Design 5, ECharts (echarts-for-react), react-i18next, Zustand
- **LLM**: MiniMax-M2.7-highspeed via OpenAI-compatible endpoint (`https://api.minimaxi.com/v1`)

## Project Structure

```
dcfestimate/
├── backend/
│   ├── main.py                  # FastAPI entry point + CORS
│   ├── requirements.txt
│   ├── config.py                # Environment config (API keys, etc.)
│   ├── api/
│   │   ├── upload.py            # PDF upload endpoints
│   │   ├── analysis.py          # DCF analysis endpoints
│   │   └── report.py            # Report generation endpoints
│   ├── services/
│   │   ├── llm_service.py       # MiniMax LLM wrapper
│   │   ├── pdf_service.py       # PDF text extraction
│   │   ├── extractor_service.py # LLM-based financial data extraction
│   │   └── dcf_service.py       # DCF calculation engine
│   └── models/
│       └── schemas.py           # Pydantic request/response models
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── i18n/
│   │   │   ├── index.ts         # i18n setup
│   │   │   ├── zh.json          # Chinese translations
│   │   │   └── en.json          # English translations
│   │   ├── pages/
│   │   │   ├── HomePage.tsx     # Landing / entry page
│   │   │   ├── AnalysisPage.tsx # Main analysis workspace
│   │   │   └── ResultPage.tsx   # Results & report page
│   │   ├── components/
│   │   │   ├── FileUpload.tsx   # PDF upload component
│   │   │   ├── ManualInput.tsx  # Manual financial data form
│   │   │   ├── ParamPanel.tsx   # WACC/growth rate parameter panel
│   │   │   ├── DCFResult.tsx    # Valuation result display
│   │   │   ├── CashFlowChart.tsx      # FCF projection chart
│   │   │   ├── SensitivityTable.tsx   # Sensitivity analysis heatmap
│   │   │   ├── WaterfallChart.tsx     # Valuation waterfall
│   │   │   └── LanguageSwitch.tsx     # CN/EN toggle
│   │   ├── services/
│   │   │   └── api.ts           # Axios API client
│   │   ├── store/
│   │   │   └── useStore.ts      # Zustand global state
│   │   └── types/
│   │       └── index.ts         # TypeScript type definitions
│   └── public/
└── README.md
```

## Core Feature Design

### 1. Financial Data Input (Two Modes)

**PDF Upload Mode:**

- User uploads PDF financial report
- `pdfplumber` extracts text content
- Text is sent to MiniMax LLM with structured prompt
- LLM returns JSON with extracted financial metrics

**Manual Input Mode:**

- Ant Design form with fields for: Revenue (3-5 years), EBITDA, CapEx, D&A, Working Capital Changes, Tax Rate, Net Debt, Cash, Shares Outstanding, Beta, etc.
- Pre-filled with defaults where appropriate

### 2. MiniMax LLM Integration

Use the OpenAI-compatible SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimaxi.com/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.7-highspeed",
    messages=[
        {"role": "system", "content": FINANCIAL_EXTRACTION_PROMPT},
        {"role": "user", "content": pdf_text}
    ],
    response_format={"type": "json_object"}
)
```

The LLM will be used for:

- Extracting structured financial data from unstructured PDF text
- Suggesting reasonable growth rate assumptions based on industry analysis
- Generating narrative analysis of the valuation results

### 3. DCF Calculation Engine

Core formulas implemented in `dcf_service.py`:

- **FCFF** = EBIT x (1 - Tax Rate) + Depreciation & Amortization - CapEx - Change in Working Capital
- **WACC** = (E/(E+D)) x Re + (D/(E+D)) x Rd x (1-T), where Re = Rf + Beta x (Rm - Rf) via CAPM
- **Terminal Value** = FCF_n x (1+g) / (WACC - g) (Gordon Growth Model)
- **Enterprise Value** = Sum of PV(FCF_t) + PV(Terminal Value)
- **Equity Value per Share** = (Enterprise Value - Net Debt + Cash) / Shares Outstanding
- **Sensitivity Analysis**: Matrix of equity value across different WACC and terminal growth rate combinations

### 4. Frontend UI Design

The UI follows a **step-by-step wizard flow** with three main pages:

- **Home Page**: Hero section with project description, "Start Analysis" CTA button
- **Analysis Page**: Left panel for data input (tabs: Upload / Manual), right panel for real-time parameter adjustment (WACC components, growth rates, forecast period)
- **Result Page**: Full dashboard with:
  - Valuation summary card (Enterprise Value, Equity Value, Price per Share)
  - FCF projection bar chart (historical + forecasted)
  - Sensitivity analysis heatmap (WACC vs Terminal Growth Rate)
  - Valuation waterfall chart (from revenue to equity value per share)
  - LLM narrative analysis section
  - Export to PDF button

Color theme: Professional finance blue/dark with accent colors. Support dark/light mode toggle along with CN/EN language switch.

### 5. API Endpoints

- `POST /api/upload` - Upload PDF, return extracted text
- `POST /api/extract` - Send text to LLM, return structured financial data
- `POST /api/calculate` - Run DCF model with given parameters, return full results
- `POST /api/sensitivity` - Run sensitivity analysis matrix
- `POST /api/narrative` - Generate LLM narrative analysis of results
- `GET /api/health` - Health check

### 6. Key Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant MiniMax

    User->>Frontend: Upload PDF or Enter Data
    Frontend->>Backend: POST /api/upload (PDF)
    Backend->>Backend: pdfplumber extracts text
    Backend->>Frontend: Return extracted text
    Frontend->>Backend: POST /api/extract (text)
    Backend->>MiniMax: LLM structured extraction
    MiniMax->>Backend: JSON financial data
    Backend->>Frontend: Return financial metrics
    Frontend->>Frontend: Display extracted data, allow edits
    User->>Frontend: Adjust parameters (WACC, growth, etc.)
    Frontend->>Backend: POST /api/calculate
    Backend->>Backend: DCF engine computes
    Backend->>Frontend: Valuation results + sensitivity matrix
    Frontend->>Backend: POST /api/narrative
    Backend->>MiniMax: Generate analysis narrative
    MiniMax->>Backend: Narrative text
    Backend->>Frontend: Display full results dashboard
```



## Implementation Order

Tasks are ordered by dependency -- backend core first, then frontend, then integration and polish.