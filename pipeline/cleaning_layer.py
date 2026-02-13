# ==========================================================
# ANALYTICS CLEANING & ENRICHMENT LAYER
# Production-Ready | Render Deployment Compatible
# Reads from staging table
# Writes analytics_programs_clean
# ==========================================================

import os
import re
import sys
import pandas as pd
from sqlalchemy import create_engine


# ==========================================================
# CONFIGURATION (CLOUD READY)
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

STAGING_TABLE = "stg_program_descriptions"
ANALYTICS_TABLE = "analytics_programs_clean"


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")
    return create_engine(DATABASE_URL, pool_pre_ping=True)


# ==========================================================
# NORMALIZATION
# ==========================================================

def norm(txt):
    if not isinstance(txt, str):
        return ""
    txt = txt.lower()
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


# ==========================================================
# POSTAL → PROVINCE MAP
# ==========================================================

POSTAL_PROVINCE = {
    "A": "NL","B": "NS","C": "PE","E": "NB","G": "QC","H": "QC","J": "QC",
    "K": "ON","L": "ON","M": "ON","N": "ON","P": "ON",
    "R": "MB","S": "SK","T": "AB","V": "BC","X": "NT","Y": "YT"
}


# ==========================================================
# SPECIALTY CLEANING
# ==========================================================

SPECIALTY_MAP = {
 
    # ===== Primary Care =====
    "medecine familiale": "Family Medicine",
    "médecine familiale": "Family Medicine",
    "family medicine": "Family Medicine",

    # ===== Pediatrics =====
    "pediatrie": "Pediatrics",
    "pédiatrie": "Pediatrics",
    "pediatrics": "Pediatrics",

    # ===== Internal =====
    "medecine interne": "Internal Medicine",
    "médecine interne": "Internal Medicine",
    "internal medicine": "Internal Medicine",

    # ===== Emergency =====
    "medecine d'urgence": "Emergency Medicine",
    "médecine d'urgence": "Emergency Medicine",
    "emergency medicine": "Emergency Medicine",

    # ===== Psychiatry / Neuro =====
    "psychiatrie": "Psychiatry",
    "psychiatry": "Psychiatry",

    "neurologie": "Neurology",
    "neurology": "Neurology",

    "neuropathology": "Neuropathology",

    "neurochirurgie": "Neurosurgery",
    "neurosurgery": "Neurosurgery",

    # ===== Surgery =====
    "chirurgie générale": "General Surgery",
    "chirurgie generale": "General Surgery",
    "general surgery": "General Surgery",

    "chirurgie orthopédique": "Orthopedic Surgery",
    "chirurgie orthopedique": "Orthopedic Surgery",
    "orthopedic surgery": "Orthopedic Surgery",

    "chirurgie plastique": "Plastic Surgery",
    "plastic surgery": "Plastic Surgery",

    "chirurgie cardiaque": "Cardiac Surgery",
    "cardiac surgery": "Cardiac Surgery",

    "chirurgie vasculaire": "Vascular Surgery",
    "vascular surgery": "Vascular Surgery",

    # ===== ENT / Ophthalmology =====
    "oto-rhino-laryngologie": "Otolaryngology",
    "oto": "Otolaryngology",
    "otolaryngology": "Otolaryngology",

    "ophtalmologie": "Ophthalmology",
    "ophthalmology": "Ophthalmology",

    # ===== Anesthesia =====
    "anesthesiologie": "Anesthesiology",
    "anesthésiologie": "Anesthesiology",
    "anesthesiology": "Anesthesiology",

    # ===== Radiology / Oncology =====
    "radiologie diagnostique": "Diagnostic Radiology",
    "diagnostic radiology": "Diagnostic Radiology",
    "diagnostic radiology": "Diagnostic Radiology",
    "radio": "Diagnostic Radiology",

    "radio-oncologie": "Radiation Oncology",
    "radiation oncology": "Radiation Oncology",

    # ===== Pathology =====
    "pathologie diagnostique et moleculaire": "Diagnostic and Molecular Pathology",
    "pathologie diagnostique et moléculaire": "Diagnostic and Molecular Pathology",
    "diagnostic and molecular pathology": "Diagnostic and Molecular Pathology",
    "diagnostic and clinical pathology": "Diagnostic and Clinical Pathology",
    "hematological pathology": "Hematological Pathology",

    # ===== Genetics =====
    "genetique et genomique": "Medical Genetics and Genomics",
    "génétique et génomique médicales": "Medical Genetics and Genomics",
    "medical genetics": "Medical Genetics and Genomics",
    "medical genetics and genomics": "Medical Genetics and Genomics",

    # ===== Public Health =====
    "sante publique": "Public Health and Preventive Medicine",
    "santé publique et médecine préventive": "Public Health and Preventive Medicine",
    "public health": "Public Health and Preventive Medicine",
    "public health and preventive medicine": "Public Health and Preventive Medicine",

    # ===== Nuclear =====
    "medecine nucleaire": "Nuclear Medicine",
    "médecine nucléaire": "Nuclear Medicine",
    "nuclear medicine": "Nuclear Medicine",

    # ===== Urology =====
    "urologie": "Urology",
    "urology": "Urology",

    # ===== Physical Medicine / Rehab =====
    "médecine physique et réadaptation": "Physical Medicine & Rehabilitation",
    "physical medicine & rehabilitation": "Physical Medicine & Rehabilitation",

    # ===== Obstetrics / Gynecology =====
    "obstétrique et gynécologie": "Obstetrics and Gynecology",
    "obstetrics and gynecology": "Obstetrics and Gynecology"
}


def clean_specialty(raw):
    if pd.isna(raw):
        return None

    # Remove line breaks + location suffix
    text = re.sub(r"[\n\r]+", " ", str(raw))
    text = re.sub(r"\s*-\s*.*$", "", text)

    n = norm(text)

    # Match dictionary
    for key, value in SPECIALTY_MAP.items():
        if key in n:
            return value

    # Integrated programs
    if "integrated" in n:
        if "emergency" in n:
            return "Family Medicine + Emergency Medicine"
        if "clinician" in n or "scholar" in n:
            return "Family Medicine + Research Track"
        return "Family Medicine (Integrated)"

    # Fallback
    return text.strip().title()


# ==========================================================
# UNIVERSITY CLEANING
# ==========================================================

UNIVERSITY_MAP = {
    "université de sherbrooke": "University of Sherbrooke",
    "university of manitoba": "University of Manitoba",
    "mcgill university": "McGill University",
    "université mcgill": "McGill University",
    "queen’s university": "Queen's University",
    "université laval": "Laval University",
    "université de montréal": "University of Montreal",
    "university of british columbia": "University of British Columbia",
    "university of calgary": "University of Calgary",
    "nosm university": "NOSM University",
    "university of alberta": "University of Alberta",
    "western university": "Western University",
    "university of ottawa": "University of Ottawa",
    "université d’ottawa": "University of Ottawa",
    "memorial university of newfoundland": "Memorial University of Newfoundland",
    "university of saskatchewan": "University of Saskatchewan",
    "university of toronto": "University of Toronto",
    "dalhousie university": "Dalhousie University",
    "mcmasteR university": "McMaster University",
    "toronto metropolitan university": "Toronto Metropolitan University"
}

def clean_university(raw):
    if pd.isna(raw):
        return None

    # ----------------------------
    # Remove leading '#' and whitespace
    # ----------------------------
    raw_clean = str(raw).lstrip("# ").strip()

    # ----------------------------
    # Normalize for matching
    # ----------------------------
    n = norm(raw_clean)

    for key, value in UNIVERSITY_MAP.items():
        if key in n:
            return value

    # ----------------------------
    # Fallback: title-case original
    # ----------------------------
    return raw_clean.title()


# ==========================================================
# ACCREDITATION CLEANING
# ==========================================================

ACCREDITATION_MAP = {
    "accredited": "Approved",
    "agree": "Approved",
    "notice": "Provisional"
}

def clean_accreditation(raw):
    if pd.isna(raw):
        return None

    n = norm(raw)
    for k, v in ACCREDITATION_MAP.items():
        if k in n:
            return v

    return str(raw).strip().title()


# ==========================================================
# POSTAL CLEANING
# ==========================================================

CITY_TO_FSA = {
    "montreal": "H3A", "st johns": "A1C",
    "toronto": "M5S", "ottawa": "K1N", "hamilton": "L8S",
    "brampton": "L6Y", "brantford": "N3R", "waterloo": "N2L",
    "kitchener": "N2G", "windsor": "N9B", "niagara": "L2G",
    "simcoe": "N3Y", "owen sound": "N4K",
    "edmonton": "T6G", "winnipeg": "R3T", "fraser": "V2T",
    "vancouver": "V6T", "st john": "A1C", "st. john": "A1C"
}

UNIVERSITY_TO_FSA = {
    "mcgill": "H3A", "universite de montreal": "H3T",
    "mcmaster": "L8S", "western university": "N6A",
    "university of ottawa": "K1N",
    "university of alberta": "T6G", "university of manitoba": "R3T",
    "university of british columbia": "V6T", "memorial university": "A1C"
}

def clean_postal(raw, city, university):
    # 1️⃣ Try extracting real postal
    if isinstance(raw, str):
        m = re.search(r"[ABCEGHJ-NPRSTVXY]\d[A-Z]\s?\d[A-Z]\d", raw, re.I)
        if m:
            return m.group(0).upper().replace(" ", "")

    # 2️⃣ No valid postal → infer
    city_n = norm(city) if city else ""
    uni_n = norm(university) if university else ""

    for k, fsa in CITY_TO_FSA.items():
        if k in city_n:
            return fsa + "1A1"

    for k, fsa in UNIVERSITY_TO_FSA.items():
        if k in uni_n:
            return fsa + "1A1"

    # 3️⃣ Still nothing → unknown
    return None


# ==========================================================
# PROVINCE INFERENCE
# ==========================================================

def infer_province(row):
    if pd.notna(row.get("province")):
        return row["province"]

    postal = row.get("postal_code_clean")
    if isinstance(postal, str) and len(postal) >= 1:
        return POSTAL_PROVINCE.get(postal[0])

    return None

# ==========================================================
# VALIDATION
# ==========================================================

def validate(df):

    print("\n=== DATA QUALITY REPORT ===")

    checks = {
        "province_nulls": df["province"].isna().sum(),
        "postal_nulls": df["postal_code"].isna().sum(),
        "specialty_nulls": df["specialty"].isna().sum(),
        "accreditation_nulls": df["accreditation_status"].isna().sum(),
        "university_nulls": df["university"].isna().sum()
    }

    for k, v in checks.items():
        print(f"{k}: {v}")

    if any(v > 0 for v in checks.values()):
        print("⚠️  Warning: Missing values detected")
    else:
        print("✅ Data quality checks passed")


# ==========================================================
# PIPELINE
# ==========================================================

def run():

    print("========== CLEANING START ==========")

    try:

        engine = get_engine()

        # Load staging
        df = pd.read_sql(f"SELECT * FROM {STAGING_TABLE}", engine)
        print(f"Loaded {len(df)} rows from staging")

        # Clean fields
        df["postal_code"] = df["postal_code"].apply(clean_postal)
        df["province"] = df["postal_code"].apply(infer_province)
        df["university"] = df["university"].apply(clean_university)
        df["specialty"] = df["specialty"].apply(clean_specialty)
        df["accreditation_status"] = df["accreditation_status"].apply(clean_accreditation)

        # Select final schema
        final = df[[
            "document_id",
            "n_program_description_sections",
            "program_description_id",
            "university",
            "specialty",
            "accreditation_status",
            "province",
            "postal_code",
            "quota",
            "approved_date",
            "program_director",
            "program_length"
        ]].copy()

        # Write analytics table
        final.to_sql(
            ANALYTICS_TABLE,
            engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=500
        )

        validate(final)

        print("✅ Analytics table created successfully")
        print(f"Rows written: {len(final)}")

    except Exception as e:
        print("💥 Cleaning layer failed")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    run()
