# CaRMS Residency Program Strategy Dashboard

## Executive Summary

This project builds an end-to-end data pipeline and interactive analytics dashboard analyzing Canadian residency programs.

The objective is to transform raw CaRMS program data into structured insights that support strategic capacity planning, accreditation monitoring, and specialty portfolio analysis.

The solution follows a layered data architecture:

Raw Data → ETL Layer → Cleaning & Enrichment Layer → PostgreSQL → Interactive BI Dashboard

---

## Architecture

### 1. Data Layer
- Source: `program_descriptions.csv`
- Stored in `/data`

### 2. ETL Pipeline
File: `pipeline/etl_pipeline.py`

Responsibilities:
- Load raw CSV
- Normalize column formats
- Basic data validation
- Load into PostgreSQL staging table

### 3. Cleaning & Enrichment Layer
File: `pipeline/cleaning_layer.py`

Responsibilities:
- Type casting
- Missing value handling
- Feature engineering (city mapping, time buckets)
- Aggregation-ready dataset creation

### 4. Analytics & Dashboard Layer
File: `app.py`

Responsibilities:
- KPI calculations
- Provincial and city-level aggregation
- Specialty portfolio analysis
- Program length funnel structure
- Accreditation trend analysis
- Interactive Dash dashboard

---

## Key Business Metrics

- Average quota per specialty
- Highest & lowest quota specialties
- Accreditation approval rate
- Residency distribution by province
- Residency distribution by city
- Program length structure
- Temporal accreditation trend

---

## Technology Stack

- Python
- Pandas
- PostgreSQL
- SQLAlchemy
- Dash
- Plotly
- Gunicorn
- Render (Deployment)

---


