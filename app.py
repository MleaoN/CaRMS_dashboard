# =====================================================
# CANADIAN RESIDENCY PROGRAM STRATEGY DASHBOARD
# Production-Ready | Render Deployment Compatible
# =====================================================

import os
import pandas as pd
from sqlalchemy import create_engine
import dash
from dash import dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# DATABASE CONFIG
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")
TABLE = "analytics_programs_clean"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# =====================================================
# LOAD DATA
# =====================================================

df = pd.read_sql(f"SELECT * FROM {TABLE}", engine)

df["quota"] = pd.to_numeric(df["quota"], errors="coerce").fillna(0)
df["program_length"] = pd.to_numeric(df["program_length"], errors="coerce")
df["approved_date"] = pd.to_datetime(df["approved_date"], errors="coerce")

# =====================================================
# CITY MAPPING (FSA → City, fallback to province largest city)
# =====================================================

FSA_TO_CITY = {
    "H3A": "Montreal", "A1C": "St. John's", "M5S": "Toronto", "K1N": "Ottawa",
    "L8S": "Hamilton", "L6Y": "Brampton", "N3R": "Brantford", "N2L": "Waterloo",
    "N2G": "Kitchener", "N9B": "Windsor", "L2G": "Niagara", "N3Y": "Simcoe",
    "N4K": "Owen Sound", "T6G": "Edmonton", "R3T": "Winnipeg",
    "V2T": "Fraser", "V6T": "Vancouver"
}

# Normalize province names
PROVINCE_NORMALIZE = {
    "Ontario": "ON",
    "Quebec": "QC",
    "British Columbia": "BC",
    "Alberta": "AB",
    "Manitoba": "MB",
    "Saskatchewan": "SK",
    "Nova Scotia": "NS",
    "New Brunswick": "NB",
    "Newfoundland and Labrador": "NL",
    "Prince Edward Island": "PE"
}

df["province"] = df["province"].replace(PROVINCE_NORMALIZE)

# Largest city fallback per province
PROVINCE_LARGEST_CITY = {
    "ON": "On_unkow_city",
    "QC": "QC_unkow_city",
    "BC": "BC_unkow_city",
    "AB": "AB_unkow_city",
    "MB": "MB_unkow_city",
    "SK": "SK_unkow_city",
    "NS": "NS_unkow_city",
    "NB": "NB_unkow_city",
    "NL": "NL_unkow_city",
    "PE": "PE_unkow_city",
    "YT": "YT_unkow_city",
    "NT": "NT_unkow_city",
    "NU": "NU_unkow_city"
}

df["FSA"] = df["postal_code"].astype(str).str[:3]

# Step 1: Try FSA mapping
df["city"] = df["FSA"].map(FSA_TO_CITY)

# Step 2: Fallback to largest city in province
df["city"] = df.apply(
    lambda row: row["city"] if pd.notna(row["city"]) 
                else PROVINCE_LARGEST_CITY.get(row["province"], "Unknown"),
    axis=1
)

# =====================================================
# KPI CALCULATIONS
# =====================================================

specialty_quota_avg = (
    df.groupby("specialty")["quota"]
      .mean()
      .reset_index(name="avg_quota")
)

avg_quota_overall = round(specialty_quota_avg["avg_quota"].mean(), 1)
highest_specialty = specialty_quota_avg.sort_values("avg_quota", ascending=False).iloc[0]
lowest_specialty = specialty_quota_avg.sort_values("avg_quota", ascending=True).iloc[0]
approved_pct = round((df["accreditation_status"] == "Approved").mean() * 100, 1)
avg_program_length = round(df["program_length"].mean(), 1)

# =====================================================
# AGGREGATIONS
# =====================================================

prov_programs = df.groupby("province").size().reset_index(name="Programs")
prov_quota = df.groupby("province")["quota"].sum().reset_index(name="Quota")

city_programs = df.groupby(["city", "province"]).size().reset_index(name="Programs")
city_quota = df.groupby(["city", "province"])["quota"].sum().reset_index(name="Quota")

# =====================================================
# SPECIALTY TABLE (NO UNIVERSITY)
# =====================================================

specialty_table = (
    df.groupby("specialty")
      .agg(
          Residencies=("specialty","count"),
          Avg_Quota=("quota","mean"),
          Avg_Length=("program_length","mean")
      )
      .reset_index()
      .sort_values("Residencies", ascending=False)
)

# =====================================================
# FIGURES
# =====================================================

fig_residency_prov = px.bar(
    prov_programs, x="province", y="Programs", color="Programs",
    color_continuous_scale="Rainbow", title="Residency Count per Province"
)

fig_quota_prov = px.bar(
    prov_quota, x="province", y="Quota", color="Quota",
    color_continuous_scale="Rainbow", title="Total Quota per Province"
)

fig_residency_city = px.bar(
    city_programs, x="city", y="Programs", color="province",
    title="Residency Count per City"
)

fig_quota_city = px.bar(
    city_quota, x="city", y="Quota", color="province",
    title="Total Quota per City"
)

specialty_dist = df.groupby("specialty").size().reset_index(name="Programs")

fig_specialty_volume = px.bar(
    specialty_dist.sort_values("Programs", ascending=False).head(15),
    x="Programs", y="specialty", orientation="h",
    title="Top Specialties by Program Volume"
)

df["length_bucket"] = pd.cut(
    df["program_length"], bins=[0,2,4,6,10],
    labels=["≤2 Years","3–4 Years","5–6 Years","7+ Years"]
)

length_dist = df.groupby("length_bucket").size().reset_index(name="Programs")

fig_funnel = go.Figure(go.Funnel(
    y=length_dist["length_bucket"],
    x=length_dist["Programs"]
))
fig_funnel.update_layout(title="Program Length Structure Funnel")

df["year_month"] = df["approved_date"].dt.to_period("M").astype(str)
time_series = df[df["approved_date"].notna()].groupby("year_month").size().reset_index(name="Approved")

fig_time = px.line(time_series, x="year_month", y="Approved",
                   title="Accreditation Activity Over Time")

# =====================================================
# DASH APP
# =====================================================

app = dash.Dash(__name__)
server = app.server

CARD_STYLE = {
    "padding":"18px",
    "borderRadius":"10px",
    "boxShadow":"0 3px 8px rgba(0,0,0,0.08)",
    "textAlign":"center",
    "backgroundColor":"#f9f9f9",
    "width":"18%"
}

app.layout = html.Div([

    html.H1("Canadian Residency Program Strategy Dashboard",
            style={"textAlign":"center","marginBottom":"40px"}),

    html.H2("National Overview"),
    html.Div([
        html.Div([html.H4("Avg Quota / Specialty"), html.H2(f"{avg_quota_overall}")], style=CARD_STYLE),
        html.Div([html.H4("Highest Avg Quota"), html.H2(highest_specialty["specialty"])], style=CARD_STYLE),
        html.Div([html.H4("Lowest Avg Quota"), html.H2(lowest_specialty["specialty"])], style=CARD_STYLE),
        html.Div([html.H4("% Approved"), html.H2(f"{approved_pct}%")], style=CARD_STYLE),
        html.Div([html.H4("Avg Program Length"), html.H2(f"{avg_program_length} yrs")], style=CARD_STYLE),
    ], style={"display":"flex","justifyContent":"space-between"}),

    html.Hr(),

    html.H2("Provincial Capacity & Distribution"),
    dcc.Graph(figure=fig_residency_prov),
    dcc.Graph(figure=fig_quota_prov),

    html.Hr(),

    html.H2("City-Level Distribution"),
    dcc.Graph(figure=fig_residency_city),
    dcc.Graph(figure=fig_quota_city),

    html.Hr(),

    html.H2("Specialty Portfolio"),
    dcc.Graph(figure=fig_specialty_volume),
    dcc.Graph(figure=fig_funnel),

    html.Hr(),

    html.H2("Accreditation Trend"),
    dcc.Graph(figure=fig_time),

    html.Hr(),

    html.H2("Specialty Portfolio Structure"),
    dash_table.DataTable(
        data=specialty_table.round(2).to_dict("records"),
        columns=[{"name": i, "id": i} for i in specialty_table.columns],
        sort_action="native",
        page_size=10
    ),

    html.Hr(),
])

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)

