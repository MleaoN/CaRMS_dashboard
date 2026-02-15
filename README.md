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
→ PostgreSQL (Staging)  
→ Cleaning & Feature Engineering  
→ Analytics Tables  
→ Dash Dashboard (Render Deployment)

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

- Junior Data Scientist  
- Data Analyst  
- BI Developer  
- Entry-Level Data Engineer  
