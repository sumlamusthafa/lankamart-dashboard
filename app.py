"""
CIT308 Mid Semester Assignment - LankaMart Retail Dashboard
Run locally with:  streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="LankaMart Performance Dashboard", layout="wide")

DATA_FILE = "CIT308_LankaMart_Retail_Transactions.csv"

def load_and_clean_data(path: str) -> pd.DataFrame:
    """
    Loads the raw transaction file and applies documented, reproducible
    cleaning steps. Raw columns are preserved; new columns are appended.
    """
    raw = pd.read_csv(path)

    df = raw.copy()

    n_dupes = df.duplicated().sum()
    df = df.drop_duplicates()

    category_fix = {"electronic": "Electronics"}
    df["product_category"] = df["product_category"].replace(category_fix)

    df["rating_missing"] = df["customer_rating"].isna()

    df["promotion"] = df["promotion"].fillna("None")

    df["order_date"] = pd.to_datetime(df["order_date"])

    df["profit_margin"] = df["profit_lkr"] / df["revenue_lkr"]
    df["order_month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    df["is_returned"] = df["returned"].eq("Yes")

    def delivery_band(days):
        if days == 0:
            return "Same day"
        elif days <= 3:
            return "1-3 days"
        else:
            return "4+ days"

    df["delivery_band"] = df["delivery_days"].apply(delivery_band)

    df.attrs["n_duplicates_removed"] = int(n_dupes)
    return df


df = load_and_clean_data(DATA_FILE)

st.sidebar.header("Filters")

min_date, max_date = df["order_date"].min(), df["order_date"].max()
date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

provinces = sorted(df["province"].unique())
selected_provinces = st.sidebar.multiselect("Province", provinces, default=provinces)

channels = sorted(df["sales_channel"].unique())
selected_channels = st.sidebar.multiselect("Sales channel", channels, default=channels)

segments = sorted(df["customer_segment"].unique())
selected_segments = st.sidebar.multiselect("Customer segment", segments, default=segments)

if st.sidebar.button("Reset all filters"):
    st.rerun()

if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date, end_date = min_date, max_date

mask = (
    (df["order_date"] >= start_date)
    & (df["order_date"] <= end_date)
    & (df["province"].isin(selected_provinces))
    & (df["sales_channel"].isin(selected_channels))
    & (df["customer_segment"].isin(selected_segments))
)
fdf = df.loc[mask].copy()

st.title("LankaMart Performance Dashboard")
st.caption(
    f"Showing {len(fdf):,} of {len(df):,} order lines "
    f"({start_date.date()} to {end_date.date()})"
)

if fdf.empty:
    st.warning("No records match the current filters. Adjust filters or reset.")
    st.stop()

total_revenue = fdf["revenue_lkr"].sum()
total_profit = fdf["profit_lkr"].sum()
profit_margin = total_profit / total_revenue if total_revenue else 0
return_rate = fdf["is_returned"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"LKR {total_revenue:,.0f}")
k2.metric("Total Profit", f"LKR {total_profit:,.0f}")
k3.metric("Profit Margin", f"{profit_margin:.1%}")
k4.metric("Return Rate", f"{return_rate:.1%}", help="Share of order lines marked Returned = Yes")

st.divider()

c1, c2 = st.columns(2)

with c1:
    monthly = (
        fdf.groupby("order_month")[["revenue_lkr", "profit_lkr"]]
        .sum()
        .reset_index()
    )
    fig_trend = px.line(
        monthly,
        x="order_month",
        y=["revenue_lkr", "profit_lkr"],
        markers=True,
        title="Monthly Revenue and Profit (LKR)",
        labels={"order_month": "Month", "value": "LKR", "variable": "Metric"},
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with c2:
    cat = (
        fdf.groupby("product_category")["revenue_lkr"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    fig_cat = px.bar(
        cat,
        x="revenue_lkr",
        y="product_category",
        orientation="h",
        title="Revenue by Product Category (LKR)",
        labels={"revenue_lkr": "Revenue (LKR)", "product_category": "Category"},
    )
    st.plotly_chart(fig_cat, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    prov = (
        fdf.groupby("province")[["revenue_lkr", "profit_lkr"]]
        .sum()
        .reset_index()
        .sort_values("revenue_lkr", ascending=True)
    )
    fig_prov = px.bar(
        prov,
        x="revenue_lkr",
        y="province",
        orientation="h",
        title="Revenue by Province (LKR)",
        labels={"revenue_lkr": "Revenue (LKR)", "province": "Province"},
    )
    st.plotly_chart(fig_prov, use_container_width=True)

with c4:
    jitter_df = fdf.copy()
    rng = np.random.default_rng(42)  #
    jitter_df["discount_jittered"] = jitter_df["discount_pct"] + rng.uniform(
        -0.012, 0.012, size=len(jitter_df)
    )
    fig_scatter = px.scatter(
        jitter_df,
        x="discount_jittered",
        y="profit_margin",
        color="product_category",
        opacity=0.55,
        hover_data={"discount_pct": ":.0%", "discount_jittered": False,
                     "order_id": True, "product_name": True},
        title="Discount % vs Profit Margin (points jittered to reduce overlap)",
        labels={"discount_jittered": "Discount (%)", "profit_margin": "Profit Margin",
                "discount_pct": "Actual discount"},
    )
    fig_scatter.update_traces(marker=dict(size=7, line=dict(width=0)))
    fig_scatter.update_xaxes(tickformat=".0%", tickvals=[0, 0.05, 0.10, 0.15, 0.20, 0.25])
    fig_scatter.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_scatter, use_container_width=True)

fig_rating = px.histogram(
    fdf.dropna(subset=["customer_rating"]),
    x="customer_rating",
    nbins=5,
    title="Customer Rating Distribution (missing ratings excluded)",
    labels={"customer_rating": "Rating (1-5)"},
)
st.plotly_chart(fig_rating, use_container_width=True)

st.divider()

st.subheader("Detail: filtered order lines")
display_cols = [
    "order_id", "order_date", "province", "city", "sales_channel",
    "customer_segment", "product_category", "product_name", "units",
    "revenue_lkr", "profit_lkr", "profit_margin", "returned",
    "delivery_band", "customer_rating", "promotion",
]
st.dataframe(fdf[display_cols], use_container_width=True, hide_index=True)

st.divider()

st.subheader("Key insights")

top_province = prov.sort_values("revenue_lkr", ascending=False).iloc[0]
top_category = cat.sort_values("revenue_lkr", ascending=False).iloc[0]
return_by_cat = fdf.groupby("product_category")["is_returned"].mean().sort_values(ascending=False)
worst_return_cat = return_by_cat.index[0]
worst_return_rate = return_by_cat.iloc[0]

st.markdown(
    f"""
- **{top_province['province']}** is the top-performing province by revenue in the current selection
  (LKR {top_province['revenue_lkr']:,.0f}).
- **{top_category['product_category']}** is the leading product category by revenue
  (LKR {top_category['revenue_lkr']:,.0f}).
- **{worst_return_cat}** has the highest return rate among filtered categories at
  **{worst_return_rate:.1%}**, worth investigating for quality or fulfilment issues.
- Overall profit margin for the current selection is **{profit_margin:.1%}**;
  compare across filter states to identify low-margin segments.
"""
)

with st.expander("Data quality notes (for report)"):
    st.write(
        f"""
        - {df.attrs.get('n_duplicates_removed', 0)} duplicate row(s) removed on load.
        - "electronic" category label standardised to "Electronics".
        - {df['rating_missing'].sum()} rows have a missing customer_rating; these are
          excluded from rating averages/plots rather than imputed.
        - {(df['promotion'] == 'None').sum()} rows had no promotion recorded; these are
          treated as "None" (no promotion applied), not as missing data.
        """
    )
