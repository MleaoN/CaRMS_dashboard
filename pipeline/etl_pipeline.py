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

POSTAL_PROVINCE = {
    "A": "NL","B": "NS","C": "PE","E": "NB","G": "QC","H": "QC","J": "QC",
    "K": "ON","L": "ON","M": "ON","N": "ON","P": "ON","R": "MB","S": "SK",
    "T": "AB","V": "BC","X": "NT","Y": "YT"
}

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,
    "juillet":7,"aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12
}


# ============================
# NORMALIZE TEXT
# ============================

def normalize(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

# ============================
# PARSE FUNCTIONS
# ============================
def parse_program_name(text):
    if pd.isna(text):
        return None, None, None
    parts = str(text).split("-")
    
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) >= 3:
        return parts[0], parts[1], parts[-1]   # last element is city
    elif len(parts) == 2:
        return parts[0], parts[1], None
    else:
        return None, None, None


def parse_approved_date(text):
    if pd.isna(text):
        return None
    clean = normalize(str(text))
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
        return datetime(int(year), int(month_num), int(day)).date()
    except:
        return None

def parse_program_director(text):
    if pd.isna(text):
        return None
    clean = normalize(str(text))
    patterns = [
        r"program director\s+(dr\.?\s+[a-z\-]+\s+[a-z\-]+)",  # English
        r"directeur de programme\s+dr\(e\)\s+([a-z\-]+\s+[a-z\-]+)",  # French Dr(e)
        r"directeur de programme\s+dre\s+([a-z\-]+\s+[a-z\-]+)",       # French Dre
        r"directeur de programme\s+dr\s+([a-z\-]+\s+[a-z\-]+)",        # French Dr
        r"(dr\.?\s+[a-z\-]+\s+[a-z\-]+)"                               # fallback
    ]
    for p in patterns:
        m = re.search(p, clean, re.I)
        if m:
            name = m.group(1)
            name = name.replace(".", "").replace("dr", "").replace("dre", "").strip()
            return name.title()
    return None

def extract_address_and_province(text):
    if pd.isna(text):
        return None, None
    lines = [l.strip() for l in str(text).splitlines() if l.strip()]
    province = None
    province_idx = None

    # Find province
    for i, line in enumerate(lines):
        m = re.search(r"\b(ON|QC|NL|BC|AB|MB|SK|NS|NB|PE)\b", line)
        if m:
            province = m.group(1)
            province_idx = i
            break
        norm = normalize(line)
        for k, v in PROVINCE_MAP.items():
            if k in norm:
                province = v
                province_idx = i
                break
        if province_idx is not None:
            break

    if province_idx is None:
        province_idx = len(lines) - 1

    # Walk upwards to find street
    address = None
    for j in range(province_idx - 1, -1, -1):
        line = lines[j]
        if not re.search(r"\d", line):
            continue
        if not re.search(r"[A-Za-z]", line):
            continue
        if re.search(r"[A-Z]\d[A-Z]\s?\d[A-Z]\d", line):
            continue
        if re.search(r",[ ]*(ON|QC|NL|BC|AB|MB|SK|NS|NB|PE)", line):
            continue
        address = line.strip()
        break
    return address, province

def parse_quota(text):
    if pd.isna(text):
        return None
    clean = normalize(str(text))
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

import re

def parse_phone(program_contacts):

    if not isinstance(program_contacts, str):
        return None

    # Normalize text (lowercase + remove accents)
    text = normalize(program_contacts.lower())

    # Split by line
    lines = re.split(r"[\n\r]+", text)

    # Keywords (after normalization)
    keywords = [
        "phone",
        "telephone",
        "tel",
        "teleph",
        "work",
        "mobile",
        "cell"
    ]

    for line in lines:

        # Must contain a digit
        if not re.search(r"\d", line):
            continue

        # Must contain any phone keyword (partial match allowed)
        if not any(k in line for k in keywords):
            continue

        # Extract all digits
        digits = re.sub(r"\D", "", line)

        # Remove country code if present
        if len(digits) > 10 and digits.startswith("1"):
            digits = digits[1:]

        # Return first valid phone
        if len(digits) >= 10:
            return digits[:10]

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
    clean = normalize(str(text))
    m = re.search(r"(accreditation status\s*[:]\s*([a-z]+)|statut d[’']agr[eé]ment\s*[:]\s*([a-z]+))", clean)
    if m:
        return (m.group(2) or m.group(3)).title()
    return None


def extract_postal_code(text):
    if pd.isna(text):
        return None
    text = str(text)
    m = re.search(r"[ABCEGHJ-NPRSTVXY]\d[A-Z][ ]?\d[A-Z]\d", text, re.I)
    if m:
        return m.group(0).upper().replace(" ", "")
    return None

# ============================
# ETL PIPELINE FUNCTIONS
# ============================

def extract_csv():
    print("📥 Extracting CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows")
    return df

def transform(df):
    print("🧹 Transforming...")
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

    # Program name
    parsed = df["program_name"].apply(parse_program_name)
    df["university"] = parsed.apply(lambda x: x[0])
    df["specialty"] = parsed.apply(lambda x: x[1])
    df["city"] = parsed.apply(lambda x: x[2])

    # Address / Province
    addr = df["match_iteration_name"].apply(extract_address_and_province)
    df["address"] = addr.apply(lambda x: x[0])
    df["province"] = addr.apply(lambda x: x[1])
    
    df["postal_code"] = df.apply(lambda r: extract_postal_code(r["match_iteration_name"]) or
                                             extract_postal_code(r["address"]), axis=1)

    # Quota
    df["quota"] = df["match_iteration_name"].apply(parse_quota)

    # Program director
    df["program_director"] = df["match_iteration_name"].apply(parse_program_director)

    # Phone: handle missing program_contacts column
    if "program_contracts" not in df.columns:
        df["program_contracts"] = ""
    df["phone"] = df["program_contracts"].apply(parse_phone)



    # Program length
    df["program_length"] = df["program_curriculum"].apply(parse_program_length)

    # Approved date
    df["approved_date"] = df["match_iteration_name"].apply(parse_approved_date)

    # Accreditation
    df["accreditation_status"] = df["match_iteration_name"].apply(parse_accreditation_status)

 
    df = df[[
        "document_id","n_program_description_sections","match_iteration_id", "program_description_id","source","university","specialty","city",
        "address","postal_code","approved_date","quota","program_director",
        "province","phone","program_length","accreditation_status"
    ]]
    return df

def load_staging(df, engine):
    print("📤 Loading staging...")
    df.to_sql(
        STAGING_TABLE, engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500
    )

def run_pipeline():
    print("========== ETL START ==========")
    try:
        engine = get_engine()
        df = extract_csv()
        df = transform(df)
        load_staging(df, engine)
        print("✅ Pipeline completed")
    except Exception as e:
        print("💥 Pipeline failed")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
