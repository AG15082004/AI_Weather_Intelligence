# 🌦️ Tamil Nadu Weather Intelligence Platform

A full-stack weather analytics and AI intelligence platform for all **38 districts** of Tamil Nadu, India. Built with React, FastAPI, Microsoft Fabric Lakehouse, and Ollama-powered AI — delivering real-time weather insights, historical analytics, air quality monitoring, and an AI-driven dashboard builder.

---

## 🛠️ Tech Stack

| Layer        | Technology                                       |
| ------------ | ------------------------------------------------ |
| **Frontend** | React 18 · Vite · TypeScript · Tailwind CSS · shadcn/ui · Recharts |
| **Backend**  | FastAPI · Python 3.10+ · Pydantic · structlog    |
| **Data**     | Microsoft Fabric Lakehouse (`lh_tn_weather_intelligence`) · ODBC 18 |
| **AI**       | Ollama · Qwen3:4b                                |

---

## 🏗️ Architecture Overview

```
┌───────────────────┐      HTTP / REST       ┌───────────────────┐
│                   │  ◄──────────────────►   │                   │
│   React Frontend  │       :5173             │  FastAPI Backend  │
│   (Vite + TS)     │                         │     :8000         │
│                   │                         │                   │
└───────────────────┘                         └──────┬───────┬────┘
                                                     │       │
                                              ODBC   │       │  HTTP
                                                     ▼       ▼
                                        ┌─────────────┐  ┌──────────┐
                                        │   Microsoft  │  │  Ollama  │
                                        │    Fabric    │  │ Qwen3:4b │
                                        │  Lakehouse   │  │  :11434  │
                                        └─────────────┘  └──────────┘
```

- **Frontend (port 5173)** — Single-page React application providing interactive dashboards, charts, and an AI chat interface. Proxies `/api` requests to the backend.
- **Backend (port 8000)** — FastAPI REST API handling data retrieval, analytics aggregation, and AI orchestration.
- **Data Platform** — Microsoft Fabric Lakehouse (`lh_tn_weather_intelligence`) accessed via ODBC Driver 18 with interactive authentication.
- **AI Engine** — Local Ollama instance running Qwen3:4b for natural-language weather queries and AI-driven dashboard generation.

---

## ✨ Features

| #   | Module                     | Description                                                               |
| --- | -------------------------- | ------------------------------------------------------------------------- |
| 1   | **Weather Overview**       | At-a-glance dashboard with key weather KPIs across Tamil Nadu             |
| 2   | **Temperature Analytics**  | Historical temperature trends, daily/monthly averages, district comparisons |
| 3   | **Rainfall Analytics**     | Rainfall totals, monthly trends, heavy-rain indicators                    |
| 4   | **District Intelligence**  | Deep-dive analytics for each of the 38 districts                         |
| 5   | **Current Weather**        | Live weather conditions — temperature, humidity, wind, pressure           |
| 6   | **Air Quality Monitoring** | AQI, PM2.5, PM10 and pollutant-level dashboards                          |
| 7   | **AI Weather Assistant**   | Chat-based natural-language weather queries powered by Qwen3:4b           |
| 8   | **AI Dashboard Builder**   | Describe a dashboard in plain English — the AI builds it for you          |

---

## 📋 Prerequisites

| Requirement                       | Version / Notes                              |
| --------------------------------- | -------------------------------------------- |
| **Node.js**                       | 18 or later                                  |
| **Python**                        | 3.10 or later                                |
| **ODBC Driver 18 for SQL Server** | [Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) |
| **Ollama**                        | With the `qwen3:4b` model pulled             |
| **Microsoft Fabric**              | Workspace access with a SQL analytics endpoint |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd TN_Weather_Api
```

### 2. Backend setup

```bash
cd backend

# Create your environment file
cp .env.example .env
# Edit .env and fill in your Fabric SQL endpoint and other settings

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload
```

The API will be available at **http://localhost:8000**. Interactive docs at `/docs`.

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**.

### 4. Ollama setup

```bash
# Pull the model
ollama pull qwen3:4b

# Start the Ollama server (if not already running)
ollama serve
```

Ollama will serve on **http://localhost:11434** by default.

### 5. Microsoft Fabric configuration

Set these variables in `backend/.env`:

| Variable                  | Description                                       | Example                             |
| ------------------------- | ------------------------------------------------- | ----------------------------------- |
| `FABRIC_SQL_ENDPOINT`     | SQL analytics endpoint from your Fabric workspace | `xyz.datawarehouse.fabric.microsoft.com` |
| `FABRIC_DATABASE`         | Lakehouse database name                           | `lh_tn_weather_intelligence`        |
| `FABRIC_AUTHENTICATION`   | Authentication method                             | `interactive`                       |
| `OLLAMA_BASE_URL`         | Ollama server URL                                 | `http://localhost:11434`            |
| `OLLAMA_MODEL`            | LLM model name                                    | `qwen3:4b`                         |
| `CORS_ORIGINS`            | Allowed CORS origins                              | `http://localhost:5173`             |
| `LOG_LEVEL`               | Logging level                                     | `INFO`                              |
| `CACHE_TTL_SECONDS`       | Cache time-to-live in seconds                     | `300`                               |

---

## 📡 API Documentation

Once the backend is running, full interactive documentation is available at:

- **Swagger UI** — http://localhost:8000/docs
- **ReDoc** — http://localhost:8000/redoc

### Endpoint summary

| Method | Endpoint                             | Description                              |
| ------ | ------------------------------------ | ---------------------------------------- |
| GET    | `/api/health`                        | Health check                             |
| GET    | `/api/overview/`                     | Weather overview KPIs                    |
| GET    | `/api/temperature/`                  | Temperature data with date/district filters |
| GET    | `/api/temperature/trends`            | Temperature trend analysis               |
| GET    | `/api/rainfall/`                     | Rainfall data with date/district filters |
| GET    | `/api/rainfall/trends`               | Rainfall trend analysis                  |
| GET    | `/api/districts/`                    | List all 38 districts                    |
| GET    | `/api/districts/{district}`          | District-specific weather data           |
| GET    | `/api/current-weather/`             | Current weather for all districts        |
| GET    | `/api/current-weather/{district}`   | Current weather for a specific district  |
| GET    | `/api/air-quality/`                 | Air quality data for all districts       |
| GET    | `/api/air-quality/{district}`       | AQI for a specific district              |
| POST   | `/api/ai/chat`                       | AI weather assistant chat                |
| POST   | `/api/ai/intent`                     | Detect user intent from query            |
| POST   | `/api/dashboard-builder/generate`   | Generate an AI-built dashboard           |
| GET    | `/api/dashboard-builder/`           | List saved dashboards                    |

---

## 📁 Project Structure

```
TN_Weather_Api/
├── README.md
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application entry point
│       ├── config.py               # Pydantic settings
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── overview.py
│       │   ├── temperature.py
│       │   ├── rainfall.py
│       │   ├── districts.py
│       │   ├── current_weather.py
│       │   ├── air_quality.py
│       │   ├── ai.py
│       │   └── dashboard_builder.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── fabric_connection.py
│       │   ├── fabric_schema_service.py
│       │   ├── weather_service.py
│       │   ├── analytics_service.py
│       │   ├── ai_service.py
│       │   └── dashboard_service.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py       # ODBC connection pool
│       │   └── query_executor.py   # Parameterized SQL execution
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── weather.py
│       │   ├── analytics.py
│       │   └── dashboard.py
│       └── utils/
│           ├── __init__.py
│           ├── security.py         # Input sanitization
│           └── cache.py            # TTL cache decorator
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── components/
        │   ├── ui/                 # shadcn/ui components
        │   ├── layout/
        │   │   ├── AppLayout.tsx
        │   │   ├── Sidebar.tsx
        │   │   └── Header.tsx
        │   └── charts/
        │       ├── TemperatureChart.tsx
        │       ├── RainfallChart.tsx
        │       └── AQIChart.tsx
        ├── pages/
        │   ├── WeatherOverview.tsx
        │   ├── TemperatureAnalytics.tsx
        │   ├── RainfallAnalytics.tsx
        │   ├── DistrictIntelligence.tsx
        │   ├── CurrentWeather.tsx
        │   ├── AirQuality.tsx
        │   ├── AIAssistant.tsx
        │   └── DashboardBuilder.tsx
        ├── services/
        │   └── api.ts              # Axios API client
        ├── hooks/
        │   └── useWeatherData.ts
        ├── types/
        │   └── weather.ts
        └── lib/
            └── utils.ts
```

---

## 🔒 Security

- **No secrets in source control** — All credentials and endpoints are loaded from environment variables via `.env` (excluded from git).
- **Parameterized SQL** — All database queries use parameterized statements to prevent SQL injection.
- **Input sanitization** — User-supplied input is validated and sanitized before processing.
- **CORS** — Cross-origin requests are restricted to configured origins only.

---

## 🗄️ Data Architecture

The platform follows a **Bronze → Silver → Gold** medallion architecture in Microsoft Fabric:

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Bronze    │ ───► │   Silver    │ ───► │    Gold     │
│  Raw data   │      │  Cleaned &  │      │ Aggregated  │
│  ingestion  │      │  validated  │      │  analytics  │
└─────────────┘      └─────────────┘      └─────────────┘
```

| Layer      | Purpose                                                   |
| ---------- | --------------------------------------------------------- |
| **Bronze** | Raw weather data ingested from external sources           |
| **Silver** | Cleaned, deduplicated, and schema-validated records       |
| **Gold**   | Pre-aggregated analytics tables optimized for dashboards  |

All data resides in the `lh_tn_weather_intelligence` Lakehouse and is queried through the SQL analytics endpoint.

---

## 📄 License

This project is for educational and internal use. See the repository for license details.
