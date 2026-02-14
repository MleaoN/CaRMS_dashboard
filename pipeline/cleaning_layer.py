# ==========================================================
# ANALYTICS CLEANING & ENRICHMENT LAYER
# Production-Ready | Render Deployment Compatible
# Reads from staging table
# Writes analytics_programs_clean
# ==========================================================

import os
import pandas as pd
import uuid
import re
import sys
import unicodedata
from sqlalchemy import create_engine


# ==========================================================
# CONFIGURATION (CLOUD READY)
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

STAGING_TABLE = "stg_program_descriptions"
FINAL = "analytics_programs_clean"

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")
    return create_engine(DATABASE_URL, pool_pre_ping=True)



# ===================================
# POSTAL → PROVINCE MAP
# ===================================

POSTAL_PROVINCE = {
    "A": "NL","B": "NS","C": "PE","E": "NB","G": "QC","H": "QC","J": "QC",
    "K": "ON","L": "ON","M": "ON","N": "ON","P": "ON","R": "MB","S": "SK",
    "T": "AB","V": "BC","X": "NT","Y": "YT"
}

# ===================================
# NORMALIZE
# ===================================
def norm(txt):
    if not isinstance(txt, str):
        return ""

    # Lowercase
    txt = txt.lower()

    # Remove common noise characters
    txt = txt.replace("#", "")
    txt = txt.replace(".", "")
    txt = txt.replace(",", "")
    txt = txt.replace("’", "'")
    txt = txt.replace("–", "-")

    # Collapse all whitespace (including unicode)
    txt = re.sub(r"\s+", " ", txt)

    return txt.strip()

# ===================================
# SPECIALTY MAP (CANONICAL)
# ===================================

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

    text = re.sub(r"[\n\r]+", " ", str(raw))
    text = re.sub(r"\s*-\s*.*$", "", text)

    n = norm(text)

    for key, value in SPECIALTY_MAP.items():
        if key in n:
            return value

    if "integrated" in n:
        if "emergency" in n:
            return "Family Medicine + Emergency Medicine"
        if "clinician" in n or "scholar" in n:
            return "Family Medicine + Research Track"
        return "Family Medicine (Integrated)"

    return text.strip().title()

# ===================================
# ACCREDITATION NORMALIZATION
# ===================================

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

# ===================================
# UNIVERSITY MAP (CANONICAL)
# ===================================

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
    "mcmaster university": "McMaster University",
    "toronto metropolitan university": "Toronto Metropolitan University"
}

def clean_university(raw):
    if pd.isna(raw):
        return None

    raw_clean = str(raw).lstrip("# ").strip()
    n = norm(raw_clean)

    for key, value in UNIVERSITY_MAP.items():
        if key in n:
            return value

    return raw_clean.title()

# ===================================
# CITY CLEANING LAYER (FINAL VERSION)
# ===================================

# -----------------------------------
# 1. GENERIC LABELS (need enrichment)
# -----------------------------------

GENERIC_CITY_LABELS = {
    "Community", "Urban", "Regional", "West", "East",
    "North", "South", "Rural", "Unit Based", "Bilingual"
}

# -----------------------------------
# 2. PREFIXES TO STRIP
# -----------------------------------

CITY_PREFIXES = {
    "rural", "regional", "remote", "urban", "community",
    "indigenous", "integrated", "unit", "unit based"
}

def clean_city(raw):
    """Normalize raw city text and strip prefixes."""
    if pd.isna(raw):
        return None

    text = str(raw).replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\)$", "", text)
    text = unicodedata.normalize("NFKC", text)

    n = text.lower()
    first = n.split()[0]

    if first in CITY_PREFIXES:
        rest = text[len(first):].strip(" -").strip()
        return rest.title() if rest else text.title()

    return text.title()


# -----------------------------------
# 3. CANONICAL MAPPING
# -----------------------------------

CITY_CANONICAL_MAP = {

    # --- Multi-city / composite ---
    "barrie or newmarket": "Barrie",
    "midland or orillia": "Midland",
    "valemount & mcbride": "Valemount",
    "uxbridge markham": "Markham",
    "oshawa lakeridge": "Oshawa",
    "west (thunder bay & sault ste. marie": "Thunder Bay",
    "east (sudbury & north bay": "Sudbury",
    "peel & surrounding communities": "Brampton",
    "first nations northern ontario": "Thunder Bay",
    "northern ontario": "Sudbury",
    "northern thompson": "Thompson",

    # --- Region / RHA / composite labels ---
    "ottawa community": "Ottawa",
    "interlake eastern": "Selkirk",
    "greater toronto area": "Toronto",
    "south west nova": "Yarmouth",
    "quinte": "Belleville",
    "northern remote": "Thompson",
    "northwest": "Thunder Bay",
    "interior": "Kelowna",
    "kootenay boundary": "Trail",
    "okanagan south": "Penticton",
    "north okanagan": "Vernon",
    "vancouver island": "Victoria",
    "cape breton": "Sydney",
    "annapolis valley": "Kentville",
    "parkland": "Dauphin",
    "boundary trails": "Winkler",

    # --- Fraser / Vancouver composites ---
    "fraser greater vancouver": "Vancouver",
    "vancouver fraser": "Vancouver",
    "south fraser": "Surrey",
    "mainland vancouver": "Vancouver",
    "coastal": "Vancouver",

    # --- Rural-ish anchored ---
    "kelowna regional": "Kelowna",
    "kelowna rural": "Kelowna",

    # --- Quebec health-centre style ---
    "montérégie": "Longueuil",
    "rivières": "Trois-Rivières",
    "estrie": "Sherbrooke",
    "québec": "Québec",
    "des faubourgs": "Montréal",
    "de verdun": "Montréal",
    "maizerets": "Québec",
    "rosemont": "Montréal",
    "maisonneuve": "Montréal",
    "de la cité de la santé": "Laval",
    "d'assise": "Montréal",
    "des aurores boréales": "Val-d'Or",
    "les montégériennes": "Longueuil",
    "les eskers d'amos": "Amos",
    "yamaska": "Saint-Hyacinthe",
    "richelieu": "Sorel-Tracy",
    "manicouagan": "Baie-Comeau",
    "pistoles": "Trois-Pistoles",
    "du marigot": "Sherbrooke",
    "val d'or": "Val-d'Or",
    "nord de lanaudière": "Joliette",
    "lanaudière": "Joliette",
    "coeur": "Montréal",
    "la pommeraie": "Cowansville",
    "dame": "Montréal",
    "hubert": "Longueuil",
    "eustache": "Saint-Eustache",
    "neufchâtel": "Québec",
    "de maria": "Gaspé",

    # --- Stream regions ---
    "western stream": "Corner Brook",
    "central stream": "Gander",
    "eastern stream": "St. John's",
    "north nova": "New Glasgow",
    "south shore": "Bridgewater",
    "thousand islands": "Kingston",

    # --- Province-level ---
    "nova scotia": "Halifax",
    "new brunswick": "Saint John",
    "prince edward island": "Charlottetown",
    "nunavut": "Iqaluit",

    # --- Health hubs / misc ---
    "health hub (bihh": "Brandon",
    "impact": "Community Impact",
    "communities": "Community",
    "and rural": "Rural",
    "based": "Unit Based",

    # --- University names appearing in city column ---
    "nosm university": "Sudbury",
    "u of manitoba": "Winnipeg",
    "montfort": "Ottawa",

    # --- Other regional anchors ---
    "halton": "Oakville",
    "kawartha": "Peterborough",
    "ville": "Montréal",
    "quw'utsun": "Duncan",
}

def canonicalize_city(city):
    if pd.isna(city):
        return None
    n = city.lower()
    for key, value in CITY_CANONICAL_MAP.items():
        if key in n:
            return value
    return city


# -----------------------------------
# 4. CONTEXT-BASED INFERENCE
# -----------------------------------

UNIVERSITY_CITY_MAP = {
    "McGill University": "Montreal",
    "University of Montreal": "Montreal",
    "Laval University": "Quebec City",
    "University of Ottawa": "Ottawa",
    "University of Toronto": "Toronto",
    "Toronto Metropolitan University": "Toronto",
    "McMaster University": "Hamilton",
    "Western University": "London",
    "University of Manitoba": "Winnipeg",
    "University of British Columbia": "Vancouver",
    "University of Alberta": "Edmonton",
    "University of Saskatchewan": "Saskatoon",
    "University of Calgary": "Calgary",
    "Dalhousie University": "Halifax",
    "Memorial University of Newfoundland": "St. John's",
    "NOSM University": "Sudbury",
}

FSA_TO_CITY = {
    "H3A": "Montreal",
    "A1C": "St. John's",
    "M5S": "Toronto",
    "K1N": "Ottawa",
    "L8S": "Hamilton",
    "N2L": "Waterloo",
    "N2G": "Kitchener",
    "N9B": "Windsor",
    "R3T": "Winnipeg",
    "T6G": "Edmonton",
    "V6T": "Vancouver",
}

def infer_city_from_context(city, postal, university):
    if city not in GENERIC_CITY_LABELS:
        return city

    if isinstance(postal, str) and len(postal) >= 3:
        fsa = postal[:3]
        if fsa in FSA_TO_CITY:
            return FSA_TO_CITY[fsa]

    if university in UNIVERSITY_CITY_MAP:
        return UNIVERSITY_CITY_MAP[university]

    return city

# ===================================
# POSTAL CLEANING
# ===================================

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
    if isinstance(raw, str):
        m = re.search(r"[ABCEGHJ-NPRSTVXY]\d[A-Z]\s?\d[A-Z]\d", raw, re.I)
        if m:
            return m.group(0).upper().replace(" ", "")

    city_n = norm(city) if city else ""
    uni_n = norm(university) if university else ""

    for k, fsa in CITY_TO_FSA.items():
        if k in city_n:
            return fsa + "1A1"

    for k, fsa in UNIVERSITY_TO_FSA.items():
        if k in uni_n:
            return fsa + "1A1"

    return None

# ===================================
# PROVINCE INFERENCE
# ===================================

def infer_province(row):
    if pd.notna(row.get("province")):
        return row["province"]

    postal = row.get("postal_code_clean")
    if isinstance(postal, str) and len(postal) >= 1:
        return POSTAL_PROVINCE.get(postal[0])

    return None

# ===================================
# VALIDATION
# ===================================

def validate(df):
    checks = {
        "province": df["province_clean"].isna().sum(),
        "postal": df["postal_code_clean"].isna().sum(),
        "specialty": df["specialty_clean"].isna().sum(),
        "accreditation": df["accreditation_clean"].isna().sum(),
        "university": df["university_clean"].isna().sum(),
        "city": df["city_final"].isna().sum()
    }

    print("\n=== DATA QUALITY REPORT ===")
    for k, v in checks.items():
        print(f"{k}: {v} nulls")

    if any(v > 0 for v in checks.values()):
        print("⚠️  Warning: Missing values detected")
    else:
        print("✅ All checks passed")

# ===================================
# DATA ENGINEERING METRICS
# ===================================

def cleaning_metrics(df, raw_col, clean_col):
    if raw_col == "accreditation_status":
        total = len(df)
        changed = (df[raw_col].str.lower() == "agree").sum()
        unchanged = total - changed

        return {
            "raw_column": raw_col,
            "clean_column": clean_col,
            "total_rows": total,
            "changed_rows": changed,
            "unchanged_rows": unchanged,
            "improvement_pct": round((changed / total) * 100, 2)
        }
   
 
    raw_norm = df[raw_col].apply(norm)
    clean_norm = df[clean_col].apply(norm)

    total = len(df)
    changed = (raw_norm != clean_norm).sum()
    unchanged = total - changed

    return {
        "raw_column": raw_col,
        "clean_column": clean_col,
        "total_rows": total,
        "changed_rows": changed,
        "unchanged_rows": unchanged,
        "improvement_pct": round((changed / total) * 100, 2)
    }

# ===================================
# PIPELINE
# ===================================

def run():
    
    print("========== CLEANING START ==========")
    engine = get_engine()
    
    try:
    
        # Load staging table
        df = pd.read_sql(f"SELECT * FROM {STAGING_TABLE}", engine)
        print(f"Loaded {len(df)} rows")

        # -----------------------------------
        # CITY CLEANING LAYER
        # -----------------------------------

        df["city_clean"] = df["city"].apply(clean_city)
        df["city_canonical"] = df["city_clean"].apply(canonicalize_city)

        # University
        df["university_clean"] = df["university"].apply(clean_university)

        # Postal
        df["postal_code_clean"] = df.apply(
            lambda r: clean_postal(
                r["postal_code"],
                r["city_canonical"],
                r["university_clean"]
            ),
            axis=1
        )

        # City enrichment (postal + university)
        df["city_final"] = df.apply(
            lambda r: infer_city_from_context(
                r["city_canonical"],
                r["postal_code_clean"],
                r["university_clean"]
            ),
            axis=1
        )

        # -----------------------------------
        # OTHER COLUMN CLEANING
        # -----------------------------------

        # Province
        df["province_clean"] = df.apply(infer_province, axis=1)

        # Specialty
        df["specialty_clean"] = df["specialty"].apply(clean_specialty)

        # Accreditation
        df["accreditation_clean"] = df["accreditation_status"].apply(clean_accreditation)

        # Program director (basic normalization)
        df["program_director_clean"] = df["program_director"].fillna("").str.strip()

        # Approved date (no transformation yet)
        df["approved_date_clean"] = df["approved_date"]

        # Quota (no transformation yet)
        df["quota_clean"] = df["quota"]

        # Program length (no transformation yet)
        df["program_length_clean"] = df["program_length"]

        # -----------------------------------
        # VALIDATION
        # -----------------------------------

        validate(df)

        # -----------------------------------
        # FINAL ANALYTICS TABLE
        # -----------------------------------

        final = df[[
            "document_id",
            "n_program_description_sections",
            "program_description_id",
            "university_clean",
            "specialty_clean",
            "accreditation_clean",
            "province_clean",
            "postal_code_clean",
            "city_final",
            "quota_clean",
            "approved_date_clean",
            "program_director_clean",
            "program_length_clean"
        ]].copy()

        final.columns = [
            "document_id",
            "n_program_description_sections",
            "program_description_id",
            "university",
            "specialty",
            "accreditation_status",
            "province",
            "postal_code",
            "city",
            "quota",
            "approved_date",
            "program_director",
            "program_length"
        ]

        final.to_sql(FINAL, engine, if_exists="replace", index=False)
        print("✅ Analytics table created")
        print(f"Rows: {len(final)}")

        # -----------------------------------
        # CLEANING METRICS TABLE
        # -----------------------------------

        all_metrics = []

        column_pairs = [
            ("city", "city_final"),
            ("postal_code", "postal_code_clean"),
            ("university", "university_clean"),
            ("province", "province_clean"),
            ("specialty", "specialty_clean"),
            ("accreditation_status", "accreditation_clean"),
            ("program_director", "program_director_clean"),
            ("approved_date", "approved_date_clean"),
            ("quota", "quota_clean"),
            ("program_length", "program_length_clean"),
        ]

        # Compute metrics
        for raw_col, clean_col in column_pairs:
            all_metrics.append(cleaning_metrics(df, raw_col, clean_col))

        metrics_df = pd.DataFrame(all_metrics)
        metrics_df["run_id"] = str(uuid.uuid4())
        metrics_df["run_timestamp"] = pd.Timestamp.utcnow()

        metrics_df.to_sql(
            "cleaning_metrics",
            engine,
            if_exists="replace",
            index=False
        )

        print("📊 Cleaning metrics written to DB")


            
    finally:
        engine.dispose()
        print("🔌 Database connection closed")

# ===================================
# RUN
# ===================================

if __name__ == "__main__":
    run()
    
