# # 🇨🇦 CaRMS Residency Strategy Dashboard  

## Overview  

This project delivers an end-to-end data pipeline and interactive analytics dashboard for analyzing Canadian residency programs.  

It transforms semi-structured CaRMS program descriptions into structured PostgreSQL tables and generates strategic insights through a cloud-deployed Dash application.

The project demonstrates applied data engineering, statistical analysis, and business intelligence in a production-ready environment.

**Live App:**  
https://carms-dashboard.onrender.com/

---

## Architecture  

Raw CSV  
→ ETL Parsing Layer  
→ PostgreSQL (Staging--Render hosted)  
→ Cleaning & Feature Engineering  
→ Analytics Tables  (PostgreSQL--Render hosted)
→ Dash Dashboard (Render Deployment)


---
## ⚙️ Running the Project Locally

### Step 1 – Install Dependencies

pip install -r requirements.txt

### Step 2 – Set Environment Variable

**Windows**

set DATABASE_URL=postgresql://user:password@host:port/database

**Mac / Linux**

export DATABASE_URL=postgresql://user:password@host:port/database

### Step 3 – Run ETL Pipeline

python pipeline/etl_pipeline.py

### Step 4 – Run Cleaning & Enrichment Layer

python pipeline/cleaning_layer.py

### Step 5 – Launch Dashboard

python app.py

Access locally at:

http://127.0.0.1:8050

---

## ☁ Production Deployment (Render)

- PostgreSQL hosted on Render  
- Dash application deployed as a Web Service  
- Gunicorn used as production WSGI server  
- SSL-enforced database connection  

### Start Command (Render)

gunicorn app:app

### Required Environment Variable

DATABASE_URL

---

## Key Features  

### Data Engineering  

- Semi-structured text parsing into structured fields  
- Schema normalization and type enforcement  
- Feature engineering (quota per residency, time buckets, flags)  
- Column-level data quality metrics table  
- PostgreSQL cloud integration  

### Statistical Analysis  

- Kruskal–Wallis test to compare quota-per-residency distributions across provinces  
- Dunn post-hoc test for pairwise provincial comparisons  
- Boxplot visualization of statistical findings  

### Business Intelligence  

- National KPI summary  
- Residency and quota distribution by province and city  
- Specialty portfolio analysis  
- Program duration funnel  
- Accreditation trend over time  
- Data quality transparency section  

---

## Technology Stack  

- Python (Pandas, NumPy)  
- PostgreSQL  
- SQLAlchemy  
- Dash & Plotly  
- SciPy / scikit-posthocs  
- Gunicorn  
- Render (Cloud Deployment)  

---

## Why This Project Matters  

This project demonstrates:

- Structured data engineering workflow  
- Cloud database deployment  
- Statistical reasoning beyond descriptive analytics  
- End-to-end pipeline ownership  
- Production deployment of an interactive analytics application  

It was developed as part of a Junior Data Scientist application requirement and serves as a portfolio-ready example for:

- Data Scientist  
- Data Analyst  
- BI Developer  
- Data Engineer  





