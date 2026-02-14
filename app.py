# =====================================================
# CANADIAN RESIDENCY PROGRAM STRATEGY DASHBOARD
# Production-Ready | Render Deployment Compatible
# =====================================================
import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from scipy.stats import kruskal
import scikit_posthocs as sp

import dash
from dash import dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go

app = dash.Dash(__name__)
server = app.server
# =====================================================
# DATABASE CONFIG (Render Compatible)
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")
FINAL = "analytics_programs_clean"
METRICS = "cleaning_metrics"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# =====================================================
# LOAD DATA
# =====================================================


df = pd.read_sql(f"SELECT * FROM {FINAL}", engine)
metrics_df = pd.read_sql(f"SELECT * FROM {METRICS}", engine)

df["quota"] = pd.to_numeric(df["quota"], errors="coerce").fillna(0)
df["program_length"] = pd.to_numeric(df["program_length"], errors="coerce")
df["approved_date"] = pd.to_datetime(df["approved_date"], errors="coerce")


# =====================================================
# CITY FILTER — ONLY CITIES WITH >20 RESIDENCIES
# =====================================================

city_counts = df.groupby("city").size()
valid_cities = city_counts[city_counts > 20].index
df_city_filtered = df[df["city"].isin(valid_cities)]


# =====================================================
# PROGRAM-TO-QUOTA RATIO
# =====================================================

df["program_quota_ratio"] = df["quota"] / df["program_length"].replace(0, np.nan)


# =====================================================
# KRUSKAL–WALLIS TEST
# =====================================================

groups = [
    group["program_quota_ratio"].dropna().values
    for _, group in df.groupby("province")
]

H_stat, p_value = kruskal(*groups)

kruskal_result = {
    "H_statistic": round(H_stat, 4),
    "p_value": round(p_value, 6),
    "significant": "Yes" if p_value < 0.05 else "No",
}

kruskal_table = pd.DataFrame([kruskal_result])

kruskal_summary = (
    "A Kruskal–Wallis non-parametric test was conducted to evaluate whether "
    "provincial program-to-quota ratios differ significantly. "
    f"The test returned H = {kruskal_result['H_statistic']} with p = {kruskal_result['p_value']}. "
    "This provides statistical evidence that provincial program-to-quota distributions "
    f"{'do' if kruskal_result['significant'] == 'Yes' else 'do not'} differ meaningfully, "
    "supporting evidence-based policy discussion."
)


# =====================================================
# PAIRWISE DUNN POST-HOC TEST (USING scikit_posthocs)
# =====================================================

dunn = sp.posthoc_dunn(
    df,
    val_col="program_quota_ratio",
    group_col="province",
    p_adjust="holm"
)

# Identify provinces involved in significant differences
sig_provinces = set()

for g1 in dunn.index:
    for g2 in dunn.columns:
        if g1 != g2 and dunn.loc[g1, g2] < 0.05:
            sig_provinces.add(g1)
            sig_provinces.add(g2)


# =====================================================
# SIGNIFICANCE CLUSTER COLORING
# =====================================================

cluster_colors = [
    "#d62728", "#1f77b4", "#2ca02c",
    "#9467bd", "#ff7f0e", "#8c564b"
]

cluster_map = {}
color_index = 0

for prov in df["province"].unique():
    if prov in sig_provinces:
        cluster_map[prov] = cluster_colors[color_index]
        color_index = (color_index + 1) % len(cluster_colors)
    else:
        cluster_map[prov] = "#7f7f7f"  # neutral gray

df["cluster_color"] = df["province"].map(cluster_map)


# =====================================================
# NON-LINEAR Y-AXIS COMPRESSION (BACKGROUND ONLY)
# =====================================================

def compress_ratio(y):
    if pd.isna(y):
        return np.nan
    if y <= 10:
        return y
    return 10 + (y - 10) / 4

df["ratio_compressed"] = df["program_quota_ratio"].apply(compress_ratio)


# =====================================================
# REAL-VALUE Y-AXIS TICKS (VISIBLE TO USER)
# =====================================================

original_ticks = [0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50]

def compress_tick(y):
    if y <= 10:
        return y
    return 10 + (y - 10) / 4

compressed_ticks = [compress_tick(v) for v in original_ticks]


# =====================================================
# BOX PLOT WITH TRUE VALUES ON AXIS
# =====================================================

sig_marker = " *" if p_value < 0.05 else ""

fig_box = px.box(
    df,
    x="province",
    y="ratio_compressed",
    color="province",
    color_discrete_map=cluster_map,
    title=f"Program-to-Quota Ratio by Province{sig_marker}",
    points=False
)

fig_box.update_traces(
    boxpoints=False,
    jitter=0,
    pointpos=0,
    marker_opacity=0
)

fig_box.update_yaxes(
    tickmode="array",
    tickvals=compressed_ticks,
    ticktext=[str(v) for v in original_ticks],
    title="Program-to-Quota Ratio (true values)"
)

fig_box.update_layout(
    title_font_size=22,
    legend_title="Province (Significance Clusters)"
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

city_programs = (
    df_city_filtered.groupby(["city", "province"])
    .size()
    .reset_index(name="Programs")
)

city_quota = (
    df_city_filtered.groupby(["city", "province"])["quota"]
    .sum()
    .reset_index(name="Quota")
)


# =====================================================
# SPECIALTY TABLE
# =====================================================

specialty_table = (
    df.groupby("specialty")
      .agg(
          Residencies=("specialty", "count"),
          Avg_Quota=("quota", "mean"),
          Avg_Length=("program_length", "mean"),
      )
      .reset_index()
      .sort_values("Residencies", ascending=False)
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
    title="Residency Count per Province",
)

fig_quota_prov = px.bar(
    prov_quota,
    x="province",
    y="Quota",
    color="Quota",
    color_continuous_scale="Rainbow",
    title="Total Quota per Province",
)

fig_residency_city = px.bar(
    city_programs,
    x="city",
    y="Programs",
    color="province",
    title="Residency Count per City (Cities with >20 Programs)",
)

fig_quota_city = px.bar(
    city_quota,
    x="city",
    y="Quota",
    color="province",
    title="Total Quota per City (Cities with >20 Programs)",
)

specialty_dist = df.groupby("specialty").size().reset_index(name="Programs")

fig_specialty_volume = px.bar(
    specialty_dist.sort_values("Programs", ascending=False).head(15),
    x="Programs",
    y="specialty",
    orientation="h",
    title="Top Specialties by Program Volume",
)

df["length_bucket"] = pd.cut(
    df["program_length"],
    bins=[0, 2, 4, 6, 10],
    labels=["≤2 Years", "3–4 Years", "5–6 Years", "7+ Years"],
)

length_dist = df.groupby("length_bucket").size().reset_index(name="Programs")

fig_funnel = go.Figure(
    go.Funnel(
        y=length_dist["length_bucket"],
        x=length_dist["Programs"],
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
    title="Accreditation Activity Over Time",
)


# =====================================================
# CLEANED METRICS TABLE
# =====================================================

metrics_display = metrics_df.copy()
metrics_display = metrics_display.drop(columns=["run_id", "run_timestamp"], errors="ignore")
metrics_display["improvement_pct"] = (
    metrics_display["improvement_pct"].round(2).astype(str) + "%"
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
    "width": "18%",
}

SECTION_TITLE_STYLE = {
    "marginTop": "30px",
    "marginBottom": "10px",
    "fontWeight": "600",
}

app.layout = html.Div(
    [
        html.H1(
            "Canadian Residency Program Strategy Dashboard",
            style={"textAlign": "center", "marginBottom": "40px"},
        ),

        # =====================================================
        # SECTION 1 — DATA ENGINEERING METRICS
        # =====================================================
        html.H2("Data Engineering — Cleaning Metrics", style=SECTION_TITLE_STYLE),
        dash_table.DataTable(
            data=metrics_display.to_dict("records"),
            columns=[{"name": i, "id": i} for i in metrics_display.columns],
            sort_action="native",
            page_size=10,
            style_table={"marginBottom": "40px"},
        ),

        html.Hr(),

        
        # =====================================================
        # SECTION 3 — ANALYTICS DASHBOARD
        # =====================================================
        html.H2("National Overview", style=SECTION_TITLE_STYLE),
        html.Div(
            [
                html.Div(
                    [
                        html.H4("Avg Quota / Specialty"),
                        html.H2(f"{avg_quota_overall}"),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(
                    [
                        html.H4("Highest Avg Quota"),
                        html.H2(highest_specialty["specialty"]),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(
                    [
                        html.H4("Lowest Avg Quota"),
                        html.H2(lowest_specialty["specialty"]),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(
                    [
                        html.H4("% Approved"),
                        html.H2(f"{approved_pct}%"),
                    ],
                    style=CARD_STYLE,
                ),
                html.Div(
                    [
                        html.H4("Avg Program Length"),
                        html.H2(f"{avg_program_length} yrs"),
                    ],
                    style=CARD_STYLE,
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between"},
        ),

        html.Hr(),

        # =====================================================
        # SECTION 2 — STATISTICAL TESTING
        # =====================================================
        html.H2(
            "Statistical Testing — Provincial Program-to-Quota Differences",
            style=SECTION_TITLE_STYLE,
        ),
        html.P(
            kruskal_summary,
            style={"fontSize": "16px", "maxWidth": "900px"},
        ),
        dash_table.DataTable(
            data=kruskal_table.to_dict("records"),
            columns=[{"name": i, "id": i} for i in kruskal_table.columns],
            page_size=5,
            style_table={"marginBottom": "30px", "maxWidth": "500px"},
        ),
        dcc.Graph(figure=fig_box),

        html.Hr(),


        html.H2("Provincial Capacity & Distribution", style=SECTION_TITLE_STYLE),
        dcc.Graph(figure=fig_residency_prov),
        dcc.Graph(figure=fig_quota_prov),

        html.Hr(),

        html.H2(
            "City-Level Distribution (Cities with >20 Programs)",
            style=SECTION_TITLE_STYLE,
        ),
        dcc.Graph(figure=fig_residency_city),
        dcc.Graph(figure=fig_quota_city),

        html.Hr(),

        html.H2("Specialty Portfolio", style=SECTION_TITLE_STYLE),
        dcc.Graph(figure=fig_specialty_volume),
        dcc.Graph(figure=fig_funnel),

        html.Hr(),

        html.H2("Accreditation Trend", style=SECTION_TITLE_STYLE),
        dcc.Graph(figure=fig_time),

        html.Hr(),

        html.H2("Specialty Portfolio Structure", style=SECTION_TITLE_STYLE),
        dash_table.DataTable(
            data=specialty_table.round(2).to_dict("records"),
            columns=[{"name": i, "id": i} for i in specialty_table.columns],
            sort_action="native",
            page_size=10,
        ),

        html.Hr(),
    ],
    style={"padding": "20px 40px"},
)

# =====================================================
# LOCAL RUN (Development Only)
# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)

