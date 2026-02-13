# =====================================================
# CANADIAN RESIDENCY PROGRAM STRATEGY DASHBOARD
# Production-Ready | Render Deployment Compatible
# =====================================================

import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import dash
from dash import dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go

#print("DEBUG: DATABASE_URL =", os.getenv("DATABASE_URL"))

# =====================================================
# DATABASE CONFIG (Render Compatible)
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
# CITY MAPPING
# =====================================================

FSA_TO_CITY = {
    "H3A": "Montreal","A1C": "St. John's","M5S": "Toronto","K1N": "Ottawa",
    "L8S": "Hamilton","L6Y": "Brampton","N3R": "Brantford","N2L": "Waterloo",
    "N2G": "Kitchener","N9B": "Windsor","L2G": "Niagara",
    "T6G": "Edmonton","R3T": "Winnipeg","V6T": "Vancouver"
}

df["FSA"] = df["postal_code"].astype(str).str[:3]
df["city"] = df["FSA"].map(FSA_TO_CITY)

# =====================================================
# KPI CALCULATIONS
# =====================================================

specialty_quota_avg = (
    df.groupby("specialty")["quota"]
      .mean()
      .reset_index(name="avg_quota")
)

avg_quota_overall = round(specialty_quota_avg["avg_quota"].mean(), 1)

highest_specialty = specialty_quota_avg.sort_values(
    "avg_quota", ascending=False
).iloc[0]

lowest_specialty = specialty_quota_avg.sort_values(
    "avg_quota", ascending=True
).iloc[0]

approved_pct = round(
    (df["accreditation_status"] == "Approved").mean() * 100, 1
)

avg_program_length = round(df["program_length"].mean(), 1)

# =====================================================
# AGGREGATIONS
# =====================================================

prov_programs = (
    df.groupby("province")
      .size()
      .reset_index(name="Programs")
      .sort_values("Programs", ascending=False)
)

prov_quota = (
    df.groupby("province")["quota"]
      .sum()
      .reset_index(name="Quota")
      .sort_values("Quota", ascending=False)
)

city_programs = (
    df.groupby(["city", "province"])
      .size()
      .reset_index(name="Programs")
      .sort_values("Programs", ascending=False)
)

city_quota = (
    df.groupby(["city", "province"])["quota"]
      .sum()
      .reset_index(name="Quota")
      .sort_values("Quota", ascending=False)
)

# =====================================================
# NEW TABLE: UNIVERSITY + SPECIALTY
# =====================================================

university_specialty_table = (
    df.groupby(["university", "specialty"])
      .agg(
          Residencies=("specialty", "count"),
          Total_Quota=("quota", "sum")
      )
      .reset_index()
      .sort_values(["university", "Residencies"], ascending=[True, False])
)

# =====================================================
# FIGURES
# =====================================================

fig_residency_prov = px.bar(
    prov_programs,
    x="province",
    y="Programs",
    color="Programs",
    color_continuous_scale="Rainbow",
    title="Residency Count per Province"
)

fig_quota_prov = px.bar(
    prov_quota,
    x="province",
    y="Quota",
    color="Quota",
    color_continuous_scale="Rainbow",
    title="Total Quota per Province"
)

fig_residency_city = px.bar(
    city_programs,
    x="city",
    y="Programs",
    color="province",
    title="Residency Count per City (Grouped by Province)"
)

fig_quota_city = px.bar(
    city_quota,
    x="city",
    y="Quota",
    color="province",
    title="Total Quota per City (Grouped by Province)"
)

specialty_dist = (
    df.groupby("specialty")
      .size()
      .reset_index(name="Programs")
      .sort_values("Programs", ascending=False)
)

fig_specialty_volume = px.bar(
    specialty_dist.head(15),
    x="Programs",
    y="specialty",
    orientation="h",
    title="Top Specialties by Program Volume"
)

df["length_bucket"] = pd.cut(
    df["program_length"],
    bins=[0, 2, 4, 6, 10],
    labels=["≤2 Years", "3–4 Years", "5–6 Years", "7+ Years"]
)

length_dist = (
    df.groupby("length_bucket")
      .size()
      .reset_index(name="Programs")
      .sort_values("Programs", ascending=False)
)

fig_funnel = go.Figure(
    go.Funnel(
        y=length_dist["length_bucket"],
        x=length_dist["Programs"]
    )
)
fig_funnel.update_layout(title="Program Length Structure Funnel")

df["year_month"] = df["approved_date"].dt.to_period("M").astype(str)

time_series = (
    df[df["approved_date"].notna()]
      .groupby("year_month")
      .size()
      .reset_index(name="Approved")
)

fig_time = px.line(
    time_series,
    x="year_month",
    y="Approved",
    title="Accreditation Activity Over Time"
)

# =====================================================
# DASH APP
# =====================================================

app = dash.Dash(__name__)
server = app.server

CARD_STYLE = {
    "padding": "18px",
    "borderRadius": "10px",
    "boxShadow": "0 3px 8px rgba(0,0,0,0.08)",
    "textAlign": "center",
    "backgroundColor": "#f9f9f9",
    "width": "18%"
}

app.layout = html.Div([

    html.H1(
        "Canadian Residency Program Strategy Dashboard",
        style={"textAlign": "center", "marginBottom": "40px"}
    ),

    html.H2("National Overview"),
    html.Div([
        html.Div([html.H4("Avg Quota / Specialty"), html.H2(f"{avg_quota_overall}")], style=CARD_STYLE),
        html.Div([html.H4("Highest Avg Quota"), html.H2(highest_specialty["specialty"])], style=CARD_STYLE),
        html.Div([html.H4("Lowest Avg Quota"), html.H2(lowest_specialty["specialty"])], style=CARD_STYLE),
        html.Div([html.H4("% Approved"), html.H2(f"{approved_pct}%")], style=CARD_STYLE),
        html.Div([html.H4("Avg Program Length"), html.H2(f"{avg_program_length} yrs")], style=CARD_STYLE),
    ], style={"display": "flex", "justifyContent": "space-between"}),

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

    html.H2("University + Specialty Structure"),
    dash_table.DataTable(
        data=university_specialty_table.round(2).to_dict("records"),
        columns=[{"name": i, "id": i} for i in university_specialty_table.columns],
        sort_action="native",
        page_size=12,
        style_table={"overflowX": "auto"},
    ),

    html.Hr(),
])

# =====================================================
# RUN (Development Only)
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
