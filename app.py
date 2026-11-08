from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="NYC Housing & Transportation Analytics", page_icon="🏙️", layout="wide")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

@st.cache_data
def load_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

D = {
    "integrated": load_csv("integrated_data.csv"),
    "rq1": load_csv("rq1_data.csv"),
    "rq3": load_csv("rq3_data.csv"),
    "rq4": load_csv("rq4_data.csv"),
    "rq5": load_csv("rq5_data.csv"),
    "rq6": load_csv("rq6_data.csv"),
    "rq7": load_csv("rq7_data.csv"),
    "rq8": load_csv("rq8_data.csv"),
}

BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]

# Normalize common fields without changing the source CSVs.
for key in ["rq1", "rq4", "rq5", "rq6", "rq8"]:
    df = D[key]
    if "borough_clean" in df.columns:
        df["borough_clean"] = df["borough_clean"].astype(str).str.strip().str.title()
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

if not D["rq3"].empty:
    D["rq3"]["date"] = pd.to_datetime(D["rq3"]["date"], errors="coerce")
    D["rq3"]["year"] = pd.to_numeric(D["rq3"].get("year"), errors="coerce")
if not D["rq7"].empty:
    D["rq7"]["date"] = pd.to_datetime(D["rq7"]["date"], errors="coerce")


def corr_pair(df, x, y, method="pearson"):
    clean = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(clean) < 2 or clean[x].nunique() < 2 or clean[y].nunique() < 2:
        return float("nan")
    return clean[x].corr(clean[y], method=method)


def parse_natural_language(query):
    q = query.lower()
    found_borough = None
    aliases = {
        "bronx": "Bronx", "brooklyn": "Brooklyn", "manhattan": "Manhattan",
        "queens": "Queens", "staten island": "Staten Island", "si": "Staten Island"
    }
    for phrase, borough in aliases.items():
        if re.search(r"\b" + re.escape(phrase) + r"\b", q):
            found_borough = borough
            break
    years = re.findall(r"\b(202[2-6])\b", q)
    return found_borough, (int(years[0]) if years else None)

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
.hero {padding: 1.35rem 1.5rem; border-radius: 16px; background: linear-gradient(115deg,#102a43,#1d4e89); color: white; margin-bottom: 1rem;}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:.4rem 0 0 0; opacity:.88;}
.small-note {font-size:.85rem; color: #64748b;}
</style>
<div class="hero"><h1>NYC Housing & Transportation Analytics</h1><p>Exploring the relationship between housing maintenance complaints and serious-injury traffic crashes across New York City.</p></div>
""", unsafe_allow_html=True)

if not any(not x.empty for x in D.values()):
    st.error("No project CSV files were found. Keep the data folder beside app.py.")
    st.stop()

# Sidebar filters
st.sidebar.header("Report filters")
all_years = sorted(set(
    [int(x) for x in D["rq4"].get("year", pd.Series(dtype=float)).dropna().unique()]
    + [int(x) for x in D["rq5"].get("year", pd.Series(dtype=float)).dropna().unique()]
    + [int(x) for x in D["rq3"].get("year", pd.Series(dtype=float)).dropna().unique()]
))
selected_borough = st.sidebar.selectbox("Borough", ["All boroughs"] + BOROUGHS)
selected_year = st.sidebar.selectbox("Year", ["All years"] + all_years)
st.sidebar.selectbox("Housing category", ["Not available in exported data"], disabled=True,
                     help="The supplied CSV exports contain aggregated complaint counts, not complaint-category fields.")
st.sidebar.selectbox("Transportation category", ["Not available in exported data"], disabled=True,
                     help="The supplied CSV exports contain aggregated serious-crash counts, not crash-category fields.")
st.sidebar.caption("Category filters can be enabled after exporting category-level fields from the source datasets.")

st.subheader("Ask the dashboard")
query = st.text_input("Natural-language search", placeholder="Example: Show Queens in 2024")
parsed_borough, parsed_year = parse_natural_language(query) if query else (None, None)
if query and (parsed_borough or parsed_year):
    pieces = []
    if parsed_borough: pieces.append(parsed_borough)
    if parsed_year: pieces.append(str(parsed_year))
    st.info("Detected filter: " + " · ".join(pieces) + ". These filters will be applied when you generate the report.")
elif query:
    st.caption("Try including a borough name and/or a year (2022–2026).")

if "report_generated" not in st.session_state:
    st.session_state.report_generated = True
if st.button("Generate Report", type="primary", use_container_width=True):
    st.session_state.report_generated = True
    st.session_state.applied_borough = parsed_borough or (None if selected_borough == "All boroughs" else selected_borough)
    st.session_state.applied_year = parsed_year or (None if selected_year == "All years" else int(selected_year))

if "applied_borough" not in st.session_state:
    st.session_state.applied_borough = None if selected_borough == "All boroughs" else selected_borough
if "applied_year" not in st.session_state:
    st.session_state.applied_year = None if selected_year == "All years" else int(selected_year)

borough = st.session_state.applied_borough
year = st.session_state.applied_year
st.caption("Applied filters: " + (borough or "All boroughs") + " · " + (str(year) if year else "All years"))


def filter_borough(df):
    if df.empty or not borough or "borough_clean" not in df.columns:
        return df.copy()
    return df[df["borough_clean"].astype(str).str.title() == borough].copy()


def filter_year(df):
    if df.empty or not year or "year" not in df.columns:
        return df.copy()
    return df[pd.to_numeric(df["year"], errors="coerce") == year].copy()

# Overall overview metrics, based on matched area-level RQ1 data.
rq1 = filter_borough(D["rq1"])
if not rq1.empty:
    k_housing = pd.to_numeric(rq1["total_problem_records"], errors="coerce").sum()
    k_crashes = pd.to_numeric(rq1["total_serious_crashes"], errors="coerce").sum()
    k_areas = len(rq1)
else:
    k_housing = k_crashes = k_areas = 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Matched ZIP–borough areas", f"{k_areas:,}")
m2.metric("Housing problem records", f"{k_housing:,.0f}")
m3.metric("Serious-injury crashes", f"{k_crashes:,.0f}")
m4.metric("RQ1 Pearson correlation", f"{corr_pair(rq1, 'total_problem_records', 'total_serious_crashes'):.3f}" if len(rq1) else "—")
st.caption("Overview totals use matched ZIP–borough areas in the exported RQ1 dataset; they are not citywide population-adjusted rates.")

st.divider()
st.header("Explore the data")
left, right = st.columns(2)
with left:
    st.subheader("Monthly activity")
    monthly = D["rq3"].copy()
    if not monthly.empty:
        if year:
            monthly = monthly[monthly["year"] == year]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["housing_problems"], name="Housing problem records", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["serious_crashes"], name="Serious-injury crashes", mode="lines+markers", yaxis="y2"))
        fig.update_layout(height=390, hovermode="x unified", yaxis=dict(title="Housing records"), yaxis2=dict(title="Serious crashes", overlaying="y", side="right"), legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Monthly dataset is unavailable.")
with right:
    st.subheader("Housing complaints vs. serious crashes")
    scatter = filter_borough(D["rq1"])
    if not scatter.empty:
        fig = px.scatter(scatter, x="total_problem_records", y="total_serious_crashes", color="borough_clean" if not borough else None,
                         hover_data=["zip_clean", "borough_clean", "total_unique_complaints"], trendline="ols",
                         labels={"total_problem_records":"Housing problem records", "total_serious_crashes":"Serious-injury crashes", "borough_clean":"Borough"})
        fig.update_layout(height=390)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Pearson r = {corr_pair(scatter, 'total_problem_records', 'total_serious_crashes'):.3f} · Spearman ρ = {corr_pair(scatter, 'total_problem_records', 'total_serious_crashes', 'spearman'):.3f}")
    else:
        st.info("No matched areas for this filter.")

st.divider()
st.header("Research questions")
tabs = st.tabs(["RQ1–RQ2", "RQ3–RQ4", "RQ5–RQ6", "RQ7–RQ8"])

with tabs[0]:
    st.subheader("RQ1 · Housing complaints and serious-injury crashes")
    st.write("Do ZIP-code areas with more housing maintenance complaint records also experience more serious-injury traffic crashes?")
    d = filter_borough(D["rq1"])
    if not d.empty:
        c1, c2 = st.columns(2)
        c1.metric("Pearson correlation", f"{corr_pair(d, 'total_problem_records', 'total_serious_crashes'):.3f}")
        c2.metric("Spearman correlation", f"{corr_pair(d, 'total_problem_records', 'total_serious_crashes', 'spearman'):.3f}")
        st.plotly_chart(px.scatter(d, x="total_problem_records", y="total_serious_crashes", color="borough_clean" if not borough else None,
                                   hover_data=["zip_clean", "borough_clean"], trendline="ols",
                                   labels={"total_problem_records":"Housing problem records", "total_serious_crashes":"Serious-injury crashes"}), use_container_width=True)
    st.subheader("RQ2 · Does the relationship differ by borough?")
    d = D["rq1"].copy()
    rows = []
    for b, group in d.groupby("borough_clean"):
        rows.append({"Borough":b, "Matched areas":len(group), "Pearson r":corr_pair(group,"total_problem_records","total_serious_crashes"), "Spearman ρ":corr_pair(group,"total_problem_records","total_serious_crashes","spearman")})
    corr_df = pd.DataFrame(rows)
    if borough: corr_df = corr_df[corr_df["Borough"] == borough]
    st.dataframe(corr_df.round(3), use_container_width=True, hide_index=True)
    if not corr_df.empty:
        st.plotly_chart(px.bar(corr_df, x="Borough", y=["Pearson r", "Spearman ρ"], barmode="group", title="Correlation by borough"), use_container_width=True)

with tabs[1]:
    st.subheader("RQ3 · Monthly changes")
    st.write("Do monthly changes in housing complaint activity correspond to changes in serious-injury crashes?")
    d = D["rq3"].copy()
    if year: d = d[d["year"] == year]
    if not d.empty:
        c1,c2 = st.columns(2)
        c1.metric("Pearson · monthly totals", f"{corr_pair(d,'housing_problems','serious_crashes'):.3f}")
        c2.metric("Pearson · monthly changes", f"{corr_pair(d,'housing_change','crash_change'):.3f}")
        st.plotly_chart(px.scatter(d, x="housing_change", y="crash_change", hover_data=["date"], trendline="ols", labels={"housing_change":"Change in housing problem records", "crash_change":"Change in serious crashes"}), use_container_width=True)
    st.divider()
    st.subheader("RQ4 · Consistently high-activity areas")
    st.write("Are areas with consistently high housing complaint activity also associated with high serious-crash activity across years?")
    d = filter_borough(D["rq4"])
    if year: d = d[d["year"] == year]
    if not d.empty:
        st.metric("Area-year Pearson correlation", f"{corr_pair(d,'annual_housing_problems','annual_serious_crashes'):.3f}")
        top = d.sort_values("housing_rank", ascending=False).head(20)
        top["Area"] = top["zip_clean"].astype(str) + " · " + top["borough_clean"].astype(str)
        st.plotly_chart(px.scatter(top, x="annual_housing_problems", y="annual_serious_crashes", color="borough_clean", size="housing_rank", hover_name="Area", hover_data=["year","housing_rank","crash_rank","high_in_both"]), use_container_width=True)
        st.dataframe(d.sort_values("housing_rank", ascending=False).head(15), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("RQ5 · Seasonal patterns")
    st.write("Do seasonal patterns in housing complaint activity align with seasonal patterns in serious-injury crashes across boroughs?")
    d = filter_borough(D["rq5"])
    if year: d = d[d["year"] == year]
    if not d.empty:
        seasonal = d.groupby(["borough_clean","season"], as_index=False)[["housing_problems","serious_crashes"]].mean()
        order=["Winter","Spring","Summer","Autumn"]
        fig=px.line(seasonal, x="season", y="housing_problems", color="borough_clean", markers=True, category_orders={"season":order}, labels={"season":"Season","housing_problems":"Average housing problem records"})
        st.plotly_chart(fig,use_container_width=True)
        fig=px.line(seasonal, x="season", y="serious_crashes", color="borough_clean", markers=True, category_orders={"season":order}, labels={"season":"Season","serious_crashes":"Average serious-injury crashes"})
        st.plotly_chart(fig,use_container_width=True)
    st.divider()
    st.subheader("RQ6 · Crash severity outcomes")
    st.write("Are areas with more housing problem records also associated with greater severe-injury and fatality outcomes per serious crash?")
    d=filter_borough(D["rq6"])
    if not d.empty:
        st.metric("Pearson correlation", f"{corr_pair(d,'total_housing_problems','severity_outcomes_per_crash'):.3f}")
        st.metric("Spearman correlation", f"{corr_pair(d,'total_housing_problems','severity_outcomes_per_crash','spearman'):.3f}")
        st.plotly_chart(px.scatter(d,x="total_housing_problems",y="severity_outcomes_per_crash",color="borough_clean" if not borough else None,hover_data=["zip_clean","borough_clean"],trendline="ols",labels={"total_housing_problems":"Housing problem records","severity_outcomes_per_crash":"Severe injuries + fatalities per crash"}),use_container_width=True)

with tabs[3]:
    st.subheader("RQ7 · One-month lag")
    st.write("Are higher housing complaint levels in one month associated with more serious-injury crashes in the following month?")
    d=D["rq7"].copy()
    if year: d=d[d["date"].dt.year==year]
    if not d.empty:
        c1,c2=st.columns(2)
        c1.metric("Pearson correlation",f"{corr_pair(d,'previous_month_housing','serious_crashes'):.3f}")
        c2.metric("Spearman correlation",f"{corr_pair(d,'previous_month_housing','serious_crashes','spearman'):.3f}")
        st.plotly_chart(px.scatter(d,x="previous_month_housing",y="serious_crashes",hover_data=["date"],trendline="ols",labels={"previous_month_housing":"Previous-month housing problem records","serious_crashes":"Current-month serious crashes"}),use_container_width=True)
    st.divider()
    st.subheader("RQ8 · Problems per unique complaint")
    st.write("Are areas with more problem records per unique complaint also associated with higher serious-injury crash counts?")
    d=filter_borough(D["rq8"])
    if not d.empty:
        c1,c2=st.columns(2)
        c1.metric("Pearson correlation",f"{corr_pair(d,'problems_per_complaint','total_serious_crashes'):.3f}")
        c2.metric("Spearman correlation",f"{corr_pair(d,'problems_per_complaint','total_serious_crashes','spearman'):.3f}")
        st.plotly_chart(px.scatter(d,x="problems_per_complaint",y="total_serious_crashes",color="borough_clean" if not borough else None,hover_data=["zip_clean","borough_clean"],trendline="ols",labels={"problems_per_complaint":"Problem records per unique complaint","total_serious_crashes":"Serious-injury crashes"}),use_container_width=True)

st.divider()
st.header("What the results mean")
st.markdown("""
- **Association is not causation.** These analyses identify statistical patterns, not proof that housing complaints cause traffic crashes or vice versa.
- **SIRTA scope:** the transportation dataset covers serious-injury crash investigations; it does not represent every traffic crash in NYC.
- **Counts are not exposure-adjusted rates.** Population, road usage, traffic volume, and reporting behavior can affect comparisons.
- **Geographic matching matters.** ZIP–borough results use matched areas; unmatched records and missing geography should not be interpreted as zero events.
- **Category filters are not available in this export.** The supplied CSVs contain aggregated counts rather than the underlying housing complaint and crash categories.
""")

st.caption("Data sources: NYC Open Data — Housing Maintenance Code Complaints (ygpa-z7cr) and SIRTA Serious Injury & Fatality Crashes (xeqp-qz8h). Analysis period represented in the exports: 2022–2026, with some research questions restricted to complete years 2022–2025.")
