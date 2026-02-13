# CaRMS Residency Program Strategy Dashboard

## Executive Summary

This project delivers an end‑to‑end data pipeline and interactive analytics dashboard for analyzing Canadian residency programs.  
The goal is to transform raw CaRMS program descriptions into structured, analytics‑ready datasets that support:

- Strategic capacity planning  
- Accreditation monitoring  
- Provincial and specialty‑level insights  
- Program length and structure evaluation  

The system follows a layered architecture:

**Raw Data → ETL Layer → Cleaning & Enrichment → PostgreSQL → Dash Analytics App**

---

## Architecture

### 1. Data Layer
- Source file: `program_descriptions.csv`  
- Stored under `/data`  
- Contains residency program metadata (specialty, province, city, accreditation status, quota, etc.)

---

### 2. ETL Pipeline  
**File:** `pipeline/etl_pipeline.py`

**Responsibilities**
- Parse values from a **non‑structured, inconsistently formatted source table**
- Extract structured fields from free‑text and semi‑structured descriptions
- Perform initial validation (presence checks, basic type inference)
- Load the parsed raw fields into a PostgreSQL staging table

This layer focuses on **interpreting and extracting meaning** from the messy input data, without enforcing final naming conventions or schema normalization.

---

### 3. Cleaning & Enrichment Layer  
**File:** `pipeline/cleaning_layer.py`

**Responsibilities**
- Normalize column names and enforce schema consistency  
- Apply type casting and handle missing values  
- Standardize categorical values (province, city, specialty)  
- Engineer analytical features (time buckets, accreditation flags)  
- Produce a clean, analytics‑ready dataset for the dashboard  

---

### 4. Analytics & Dashboard Layer  
**File:** `app.py`

**Responsibilities**
- KPI computation  
- Provincial and city‑level aggregations  
- Specialty portfolio analysis  
- Program length funnel  
- Accreditation trend visualization  
- Interactive Dash dashboard deployed on Render  

---

## Running the Project

### Running Locally

1. Install dependencies:
```bash
   pip install -r requirements.txt
```
2. Set your local environment variable:
export DATABASE_URL="postgresql://<user>:<password>@<host>/<database>"

- Use your local or cloud PostgreSQL connection string.

3.  Run the Dash app:
```bash
python app.py
```
The dashboard will be available at: http://127.0.0.1:8050

### Running as a Web Service (Render Deployment)

https://carms-dashboard.onrender.com/

###Key Metrics & Insights- Average quota per specialty

- Highest and lowest quota specialties
- Accreditation approval rate
- Residency distribution by province and city
- Program length structure (1–7 years)
- Accreditation trends over time

###Technology Stack

- Python (Pandas, SQLAlchemy)
- PostgreSQL
- Dash & Plotly
- Gunicorn (production server)
- Render (cloud deployment)
