import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mass Mobilization Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a polished look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* KPI cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #234b78 100%);
        border-radius: 12px;
        padding: 18px 20px;
        color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,.15);
    }
    div[data-testid="stMetric"] label {
        color: #a8c8e8 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0e1c2f;
    }
    section[data-testid="stSidebar"] * {
        color: #d0dde8 !important;
    }
    /* Header area */
    .dashboard-header {
        padding: 0.5rem 0 1.2rem 0;
    }
    .dashboard-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .dashboard-header p {
        margin: 0.2rem 0 0 0;
        color: #8899aa;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path(__file__).parent / "mass mob minimal.xlsx"
    df = pd.read_excel(path)

    # Build a proper start date column (used for time-series)
    df["startmonth"] = df["startmonth"].fillna(1).astype(int)
    df["startday"] = df["startday"].fillna(1).astype(int)
    df["startyear"] = df["startyear"].fillna(df["year"]).astype(int)

    df["start_date"] = pd.to_datetime(
        df[["startyear", "startmonth", "startday"]].rename(
            columns={"startyear": "year", "startmonth": "month", "startday": "day"}
        ),
        errors="coerce",
    )

    # Clean participants for numeric analysis
    df["participants_numeric"] = pd.to_numeric(df["participants"], errors="coerce")

    # Ensure protesterviolence is clean
    df["protesterviolence"] = df["protesterviolence"].fillna(0).astype(int)
    df["violence_label"] = df["protesterviolence"].map({0: "Peaceful", 1: "Violent"})

    return df


df = load_data()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Filters")

    # Year range
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    year_range = st.slider(
        "Year range",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
    )

    # Region
    all_regions = sorted(df["region"].dropna().unique())
    selected_regions = st.multiselect("Region", all_regions, default=all_regions)

    # Country (dynamic based on region)
    available_countries = sorted(
        df.loc[df["region"].isin(selected_regions), "country"].dropna().unique()
    )
    selected_countries = st.multiselect(
        "Country", available_countries, default=available_countries
    )

    # Protester demand
    all_demands = sorted(df["protesterdemand1"].dropna().unique())
    selected_demands = st.multiselect("Protester demand", all_demands, default=all_demands)

    # State response
    all_responses = sorted(df["stateresponse1"].dropna().unique())
    selected_responses = st.multiselect(
        "State response", all_responses, default=all_responses
    )

    # Protester violence
    violence_opts = st.radio(
        "Protester violence",
        ["All", "Peaceful only", "Violent only"],
        index=0,
    )

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
mask = (
    (df["year"].between(*year_range))
    & (df["region"].isin(selected_regions))
    & (df["country"].isin(selected_countries))
    & (df["protesterdemand1"].isin(selected_demands) | df["protesterdemand1"].isna())
    & (df["stateresponse1"].isin(selected_responses) | df["stateresponse1"].isna())
)

if violence_opts == "Peaceful only":
    mask &= df["protesterviolence"] == 0
elif violence_opts == "Violent only":
    mask &= df["protesterviolence"] == 1

filtered = df[mask].copy()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dashboard-header">
        <h1>Mass Mobilization Protest Dashboard</h1>
        <p>Explore protest events across 30 countries from 1990 to 2020 &mdash; filter by region, country, demands, and more.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Protests", f"{len(filtered):,}")
k2.metric("Countries", filtered["country"].nunique())
k3.metric("Regions", filtered["region"].nunique())
violent_pct = (
    (filtered["protesterviolence"].sum() / len(filtered) * 100) if len(filtered) else 0
)
k4.metric("Violent %", f"{violent_pct:.1f}%")
k5.metric(
    "Year Span",
    f"{int(filtered['year'].min())}–{int(filtered['year'].max())}" if len(filtered) else "N/A",
)

st.divider()

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLOR_SEQ = px.colors.qualitative.Bold
TEMPLATE = "plotly_white"

# ---------------------------------------------------------------------------
# Row 1: Protests over time  |  By region
# ---------------------------------------------------------------------------
col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("Protests Over Time")
    time_df = (
        filtered.groupby(["year", "region"])
        .size()
        .reset_index(name="count")
        .sort_values("year")
    )
    fig_time = px.area(
        time_df,
        x="year",
        y="count",
        color="region",
        template=TEMPLATE,
        color_discrete_sequence=COLOR_SEQ,
        labels={"year": "Year", "count": "Protests", "region": "Region"},
    )
    fig_time.update_layout(
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=20, r=20, t=10, b=60),
        height=380,
    )
    st.plotly_chart(fig_time, use_container_width=True)

with col_b:
    st.subheader("Protests by Region")
    region_df = filtered["region"].value_counts().reset_index()
    region_df.columns = ["region", "count"]
    fig_region = px.pie(
        region_df,
        names="region",
        values="count",
        template=TEMPLATE,
        color_discrete_sequence=COLOR_SEQ,
        hole=0.45,
    )
    fig_region.update_traces(textinfo="percent+label", textposition="outside")
    fig_region.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=10),
        height=380,
    )
    st.plotly_chart(fig_region, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Top countries  |  Protester demands
# ---------------------------------------------------------------------------
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Top 15 Countries by Protest Count")
    top_countries = (
        filtered["country"]
        .value_counts()
        .head(15)
        .reset_index()
    )
    top_countries.columns = ["country", "count"]
    fig_countries = px.bar(
        top_countries,
        y="country",
        x="count",
        orientation="h",
        template=TEMPLATE,
        color="count",
        color_continuous_scale="Blues",
        labels={"country": "", "count": "Protests"},
    )
    fig_countries.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=10, b=20),
        height=440,
    )
    st.plotly_chart(fig_countries, use_container_width=True)

with col_d:
    st.subheader("Protester Demands")
    demand_df = (
        filtered["protesterdemand1"]
        .dropna()
        .value_counts()
        .reset_index()
    )
    demand_df.columns = ["demand", "count"]
    fig_demand = px.bar(
        demand_df,
        y="demand",
        x="count",
        orientation="h",
        template=TEMPLATE,
        color="count",
        color_continuous_scale="Purples",
        labels={"demand": "", "count": "Protests"},
    )
    fig_demand.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=10, b=20),
        height=440,
    )
    st.plotly_chart(fig_demand, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3: State response  |  Violence breakdown
# ---------------------------------------------------------------------------
col_e, col_f = st.columns(2)

with col_e:
    st.subheader("State Responses")
    resp_df = (
        filtered["stateresponse1"]
        .dropna()
        .value_counts()
        .reset_index()
    )
    resp_df.columns = ["response", "count"]
    fig_resp = px.bar(
        resp_df,
        x="response",
        y="count",
        template=TEMPLATE,
        color="response",
        color_discrete_sequence=COLOR_SEQ,
        labels={"response": "", "count": "Protests"},
    )
    fig_resp.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=20),
        height=380,
    )
    st.plotly_chart(fig_resp, use_container_width=True)

with col_f:
    st.subheader("Protester Violence")
    viol_df = filtered["violence_label"].value_counts().reset_index()
    viol_df.columns = ["type", "count"]
    fig_viol = px.pie(
        viol_df,
        names="type",
        values="count",
        template=TEMPLATE,
        color="type",
        color_discrete_map={"Peaceful": "#3b82f6", "Violent": "#ef4444"},
        hole=0.5,
    )
    fig_viol.update_traces(textinfo="percent+label+value", textposition="outside")
    fig_viol.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=10),
        height=380,
    )
    st.plotly_chart(fig_viol, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 4: Violence trend  |  Participants distribution
# ---------------------------------------------------------------------------
col_g, col_h = st.columns(2)

with col_g:
    st.subheader("Violence Rate Over Time")
    viol_trend = (
        filtered.groupby("year")
        .agg(total=("protesterviolence", "size"), violent=("protesterviolence", "sum"))
        .reset_index()
    )
    viol_trend["violence_rate"] = (viol_trend["violent"] / viol_trend["total"] * 100).round(1)
    fig_vtrend = px.line(
        viol_trend,
        x="year",
        y="violence_rate",
        template=TEMPLATE,
        labels={"year": "Year", "violence_rate": "Violence Rate (%)"},
        markers=True,
    )
    fig_vtrend.update_traces(line_color="#ef4444", line_width=2.5)
    fig_vtrend.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        height=380,
    )
    st.plotly_chart(fig_vtrend, use_container_width=True)

with col_h:
    st.subheader("Participant Size Distribution")
    cat_order = ["50-99", "100-999", "1000-1999", "2000-4999", "5000-10000", ">10000"]
    cat_df = (
        filtered.loc[filtered["participants_category"].notna(), "participants_category"]
        .value_counts()
        .reindex(cat_order)
        .dropna()
        .reset_index()
    )
    cat_df.columns = ["category", "count"]
    fig_cat = px.bar(
        cat_df,
        x="category",
        y="count",
        template=TEMPLATE,
        color="count",
        color_continuous_scale="Teal",
        labels={"category": "Participant Size", "count": "Protests"},
    )
    fig_cat.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=10, b=20),
        height=380,
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 5: Country x Year heatmap
# ---------------------------------------------------------------------------
st.subheader("Protest Intensity Heatmap — Country vs Year")

top_n = st.slider("Number of countries to show", 5, 30, 15, key="heatmap_slider")
top_countries_list = filtered["country"].value_counts().head(top_n).index.tolist()
heat_df = (
    filtered[filtered["country"].isin(top_countries_list)]
    .groupby(["country", "year"])
    .size()
    .reset_index(name="protests")
)
heat_pivot = heat_df.pivot(index="country", columns="year", values="protests").fillna(0)
# Sort by total protests
heat_pivot = heat_pivot.loc[heat_pivot.sum(axis=1).sort_values(ascending=True).index]

fig_heat = px.imshow(
    heat_pivot,
    template=TEMPLATE,
    color_continuous_scale="YlOrRd",
    aspect="auto",
    labels=dict(x="Year", y="Country", color="Protests"),
)
fig_heat.update_layout(
    margin=dict(l=20, r=20, t=10, b=20),
    height=max(350, top_n * 28),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 6: Demand breakdown by region (stacked bar)
# ---------------------------------------------------------------------------
st.subheader("Protester Demands by Region")
demand_region_df = (
    filtered.dropna(subset=["protesterdemand1"])
    .groupby(["region", "protesterdemand1"])
    .size()
    .reset_index(name="count")
)
fig_dr = px.bar(
    demand_region_df,
    x="region",
    y="count",
    color="protesterdemand1",
    template=TEMPLATE,
    color_discrete_sequence=COLOR_SEQ,
    barmode="stack",
    labels={"region": "Region", "count": "Protests", "protesterdemand1": "Demand"},
)
fig_dr.update_layout(
    legend=dict(orientation="h", y=-0.25),
    margin=dict(l=20, r=20, t=10, b=80),
    height=420,
)
st.plotly_chart(fig_dr, use_container_width=True)

# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Filtered Data")
display_cols = [
    "id",
    "country",
    "region",
    "year",
    "start_date",
    "location",
    "protesterdemand1",
    "stateresponse1",
    "violence_label",
    "participants",
    "protesteridentity",
]
st.dataframe(
    filtered[display_cols].sort_values("start_date", ascending=False).reset_index(drop=True),
    use_container_width=True,
    height=460,
)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    ---
    <div style="text-align:center; color:#8899aa; font-size:0.82rem; padding:0.5rem 0;">
        Mass Mobilization Protest Dashboard &bull; Data: Mass Mobilization Project &bull; Built with Streamlit & Plotly
    </div>
    """,
    unsafe_allow_html=True,
)
