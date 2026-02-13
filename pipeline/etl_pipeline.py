# ==========================================================
# ETL PIPELINE – UNIVERSITY PROGRAMS
# Production-Ready for Render Deployment
# Loads data into staging table only
# ==========================================================

import os
import sys
import re
import unicodedata
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text


# ==========================================================
# CONFIGURATION (CLOUD READY)
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
CSV_PATH = os.getenv("CSV_PATH", "data/program_descriptions.csv")

STAGING_TABLE = "stg_program_descriptions"


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")
    return create_engine(DATABASE_URL, pool_pre_ping=True)


# ==========================================================
# REFERENCE DICTIONARIES
# ==========================================================

PROVINCE_MAP = {
    "newfoundland": "NL",
    "labrador": "NL",
    "quebec": "QC",
    "ontario": "ON",
    "alberta": "AB",
    "british columbia": "BC",
    "manitoba": "MB",
    "saskatchewan": "SK",
    "nova scotia": "NS",
    "new brunswick": "NB",
    "prince edward island": "PE"
}

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,
    "juillet":7,"aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12
}


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def normalize(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def parse_program_name(text):
    if pd.isna(text):
        return None, None, None

    parts = [p.strip() for p in str(text).split(" - ")]

    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None

    return None, None, None


def parse_approved_date(text):
    if pd.isna(text):
        return None

    clean = normalize(text)
    m = re.search(r"(?:last approved on|approuve le)\s+([a-z]+\s+\d{1,2},?\s+\d{4})", clean)

    if not m:
        return None

    date_str = m.group(1).replace(",", "")
    parts = date_str.split()

    if len(parts) != 3:
        return None

    month, day, year = parts
    month_num = MONTHS.get(month)

    if not month_num:
        return None

    try:
        return datetime(int(year), month_num, int(day)).date()
    except:
        return None


def parse_quota(text):
    if pd.isna(text):
        return None

    clean = normalize(text)

    patterns = [
        r"quota\s*[:]\s*(\d+)",
        r"approximate\s+quota\s*[:]\s*(\d+)",
        r"quota\s+approximatif\s*[:]\s*(\d+)"
    ]

    for p in patterns:
        m = re.search(p, clean)
        if m:
            return int(m.group(1))

    return None


def parse_program_length(text):
    if pd.isna(text):
        return None

    patterns = [
        r"(\d+)\s+years?",
        r"(\d+)\s+ans?",
        r"dur[eé]e\s*[:]\s*(\d+)",
        r"programme\s+de\s+(\d+)\s+ans"
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return int(m.group(1))

    return None


def parse_accreditation_status(text):
    if pd.isna(text):
        return None

    clean = normalize(text)

    m = re.search(
        r"(accreditation status\s*[:]\s*([a-z]+)|statut d[’']agr[eé]ment\s*[:]\s*([a-z]+))",
        clean
    )

    if m:
        return (m.group(2) or m.group(3)).title()

    return None


def extract_postal_code(text):
    if pd.isna(text):
        return None

    m = re.search(r"[ABCEGHJ-NPRSTVXY]\d[A-Z][ ]?\d[A-Z]\d", str(text), re.I)

    if m:
        return m.group(0).upper().replace(" ", "")

    return None


# ==========================================================
# EXTRACT
# ==========================================================

def extract_csv():
    print("📥 Extracting CSV...")

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows")

    return df


# ==========================================================
# TRANSFORM
# ==========================================================

def transform(df):

    print("🧹 Transforming...")

    df = df.copy()
    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    # Parse program name
    parsed = df["program_name"].apply(parse_program_name)
    df["university"] = parsed.apply(lambda x: x[0])
    df["specialty"] = parsed.apply(lambda x: x[1])
    df["city"] = parsed.apply(lambda x: x[2])

    # Postal Code
    df["postal_code"] = df["match_iteration_name"].apply(extract_postal_code)

    # Quota
    df["quota"] = df["match_iteration_name"].apply(parse_quota)

    # Program Length
    df["program_length"] = df["program_curriculum"].apply(parse_program_length)

    # Approved Date
    df["approved_date"] = df["match_iteration_name"].apply(parse_approved_date)

    # Accreditation
    df["accreditation_status"] = df["match_iteration_name"].apply(parse_accreditation_status)

    return df


# ==========================================================
# LOAD (STAGING ONLY)
# ==========================================================

def load_staging(df, engine):

    print("📤 Loading staging table...")

    df.to_sql(
        STAGING_TABLE,
        engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500
    )

    print("✅ Staging table loaded")


# ==========================================================
# PIPELINE RUNNER
# ==========================================================

def run_pipeline():

    print("========== ETL START ==========")

    try:
        engine = get_engine()
        df = extract_csv()
        df = transform(df)
        load_staging(df, engine)

        print("✅ ETL completed successfully")

    except Exception as e:
        print("💥 ETL failed")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
