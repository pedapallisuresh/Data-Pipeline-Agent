# Data Pipeline Agent 🛢️➡️✨➡️🏆

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellowgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-GCS%20%7C%20BigQuery-orange?logo=googlecloud)](https://cloud.google.com/)

**AI-Orchestrated Medallion Architecture Data Pipeline using Google Agent Development Kit (ADK)**

A production-ready implementation of the [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) (Bronze → Silver → Gold) for ETL pipelines on Google Cloud Platform (GCP). Leverages [Google ADK](https://google.github.io/adk-docs/) for intelligent agent-based orchestration.

## 🚀 Features
- **Medallion Layers**:
  - **Bronze**: Raw data ingestion (GCS CSV).
  - **Silver**: Cleansed & standardized (GCS Parquet).
  - **Gold**: Aggregated analytics-ready (GCS CSV + BigQuery).
- **Dual Agent Modes**:
  - **LLM-Driven** (`LlmAgent`): AI decides tool calls dynamically.
  - **Sequential** (`SequentialAgent`): Fixed workflow orchestration.
- **Robust & Portable**:
  - Lazy GCP client initialization (works offline with stubs).
  - Environment-configurable (buckets, datasets).
  - Standalone runner (`run_pipeline.py`) – no ADK required.
- **Tools**:
  - GCS-based ETL (`tools.py`).
  - BigQuery wrapper (`bigquery_tools.py`).

## 🏗️ Architecture

```
User Prompt → Root Agent (BSG_Pipeline_Orchestrator)
              ↓ SequentialAgent
├── BronzeToSilverAgent (LlmAgent)
│   └── process_bronze_to_silver(file_name) [GCS CSV → Parquet]
└── SilverToGoldAgent (LlmAgent)
    └── process_silver_to_gold(silver_file) [Parquet → CSV/BigQuery Agg]
```

**Data Flow**:
```
Raw CSV (Bronze GCS) 
  ↓ Clean/Drop NaNs + Timestamp
Parquet (Silver GCS)
  ↓ GroupBy/Aggregate
CSV + BigQuery Table (Gold)
```

## ⚡ Quickstart (Windows)

### 1. Setup Virtual Environment
```cmd
cd c:\Users\pedapalli.s.lv\data_pipeline_agent
python -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Install Dependencies
```cmd
pip install google-adk google-cloud-storage google-cloud-bigquery pandas pyarrow
```

### 3. GCP Authentication (Optional for Local Testing)
```cmd
gcloud auth application-default login
```

### 4. Configure Environment Variables
```cmd
set BRONZE_BUCKET=your-gcs-data-pipeline-bronze
set SILVER_BUCKET=your-gcs-data-pipeline-silver
set GOLD_BUCKET=your-gcs-data-pipeline-gold
set BQ_DATASET=your_project.gold_analytics
set BQ_TABLE=pipeline_results
```
(Defaults provided if unset.)

### 5. Run Pipeline

**Option A: ADK CLI (Agent Mode)**
```cmd
adk run data_pipeline_agent
# Example prompt: "Process new raw file: sales/batch_2024-01.csv"
```

**Option B: Standalone Runner**
```cmd
python run_pipeline.py --file sales/batch_2024-01.csv
```

**Expected Output**:
```
✅ Bronze → Silver: sales/batch_2024-01_cleaned.parquet
🏆 Silver → Gold: sales/batch_2024-01_report.csv + BigQuery loaded
```

## ⚙️ Configuration

| Variable          | Default                      | Description |
|-------------------|------------------------------|-------------|
| `BRONZE_BUCKET`   | `gcs-data-pipeline-bronze`  | GCS raw data bucket |
| `SILVER_BUCKET`   | `gcs-data-pipeline-silver`  | GCS cleaned data |
| `GOLD_BUCKET`     | `gcs-data-pipeline-gold`    | GCS reports |
| `BQ_DATASET`      | `gold_analytics`            | BigQuery dataset |
| `BQ_TABLE`        | `pipeline_results`          | BigQuery table |

## 💻 Key Files

| File | Purpose |
|------|---------|
| `agent.py` | ADK agents + orchestration logic |
| `tools.py` | GCS ETL functions |
| `bigquery_tools.py` | BigQuery tools + FunctionTools |
| `run_pipeline.py` | Non-ADK runner |
| `types.py` | Type hints |

## 🧪 Local Testing (No GCP)
- Stubs handle missing `google-cloud-*` packages.
- Modify `tools.py` for local FS (future enhancement).

## 🔧 Troubleshooting
- **GCS Errors**: Verify `gcloud auth application-default login`.
- **BigQuery Fails**: Check `BQ_*` env vars & dataset exists.
- **ADK Not Found**: Use `run_pipeline.py` or `pip install google-adk`.
- **Module Import**: Ensure `.venv` activated.

## 📈 Example Data Flow
```
Input: "Process sales/november.csv"
1. Download november.csv from Bronze GCS
2. Clean → november_cleaned.parquet (Silver)
3. Aggregate sales by category → november_report.csv (Gold GCS)
4. Load summary to BigQuery gold_analytics.pipeline_results
```

## 🤝 Contributing
See [ADK Contributing Guide](adk-python/contributing/README.md). PRs welcome!

## 📄 License
[Apache 2.0](LICENSE) © Google LLC

---

⭐ **Built with [Google ADK](https://google.github.io/adk-docs/)**
