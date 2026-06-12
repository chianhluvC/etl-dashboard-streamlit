"""
Retail Analytics Dashboard
pip install streamlit requests pandas plotly
ATHENA_API_URL=getonAWS streamlit run streamlit_app.py
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# Config & page setup
# ══════════════════════════════════════════════════════════════════════════════
API_URL = st.secrets["API_URL"].rstrip("/")

st.set_page_config(
    page_title="Retail Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] label { color: #f1f5f9 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 6px;
}

/* KPI metric cards */
div[data-testid="metric-container"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
div[data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: .05em !important;
    text-transform: uppercase;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-size: 28px !important;
    font-weight: 600 !important;
}

/* Section tabs */
div[data-baseweb="tab-list"] { border-bottom: 2px solid #e2e8f0; gap: 4px; }
div[data-baseweb="tab"] {
    font-weight: 500;
    color: #64748b;
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
}
div[aria-selected="true"] { color: #0f172a !important; border-bottom: 2px solid #0f172a; }

/* Query box */
.query-box {
    background: #0f172a;
    border-radius: 10px;
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    color: #7dd3fc;
    font-size: 13px;
    line-height: 1.6;
}
</style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("📊 Retail Intelligence")

    st.caption("Sales analytics dashboard powered by Athena")

    st.divider()

    # ──────────────────────────────────────────────────────────────────────
    # Configuration
    # ──────────────────────────────────────────────────────────────────────
    st.subheader("⚙️ Configuration")

    # Hidden API config
    with st.expander("🔐 Advanced API Settings"):
        api_input = st.text_input(
            "API Gateway Endpoint",
            value=API_URL,
            placeholder="https://xxx.execute-api.../prod",
            help="Lambda API endpoint for Athena queries",
            on_change=st.cache_data.clear,
        )

    st.divider()

    # ──────────────────────────────────────────────────────────────────────
    # Dashboard controls
    # ──────────────────────────────────────────────────────────────────────
    st.subheader("📈 Dashboard Controls")

    top_n = st.slider(
        "Top Products",
        min_value=5,
        max_value=25,
        value=10,
    )

    cust_limit = st.slider(
        "Customers to Load",
        min_value=50,
        max_value=500,
        value=100,
    )

    st.divider()

    # ──────────────────────────────────────────────────────────────────────
    # Refresh button
    # ──────────────────────────────────────────────────────────────────────
    if st.button(
        "🔄 Refresh Dashboard",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # ──────────────────────────────────────────────────────────────────────
    # Status section
    # ──────────────────────────────────────────────────────────────────────
    st.subheader("📡 System Status")

    st.success("Athena API Connected")

    # st.metric(
    #     label="Cache TTL",
    #     value="5 min",
    # )

    # st.caption("Data refreshes automatically after cache expiration.")


# ══════════════════════════════════════════════════════════════════════════════
# API helper
# ══════════════════════════════════════════════════════════════════════════════
def call_api(action: str, **kwargs) -> list[dict]:
    url = (api_input or API_URL).rstrip("/")
    if not url:
        st.error("⚠️  Set ATHENA_API_URL or enter the API URL in the sidebar.")
        st.stop()
    r = requests.post(url, json={"action": action, **kwargs}, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])


def to_num(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Data loaders — no @st.cache_data here, cache is on _load_all_cached
# ══════════════════════════════════════════════════════════════════════════════
def load_summary():
    return pd.DataFrame(call_api("summary"))


def load_revenue_by_country():
    df = pd.DataFrame(call_api("revenue_by_country"))
    return to_num(df, ["total_orders", "unique_customers", "total_revenue"])


def load_top_products(n):
    df = pd.DataFrame(call_api("top_products", limit=n))
    return to_num(df, ["times_ordered", "total_qty", "total_revenue", "avg_price"])


def load_monthly_trend():
    df = pd.DataFrame(call_api("monthly_trend"))
    return to_num(
        df, ["total_orders", "unique_customers", "total_revenue", "avg_unit_price"]
    )


def load_customer_behavior(n):
    df = pd.DataFrame(call_api("customer_behavior", limit=n))
    return to_num(
        df, ["order_frequency", "total_units", "total_spend", "avg_order_value"]
    )


def load_spend_distribution():
    df = pd.DataFrame(call_api("spend_distribution"))
    return to_num(df, ["customer_count", "avg_spend"])


# ══════════════════════════════════════════════════════════════════════════════
# Parallel loading with single cache entry
# ──────────────────────────────────────────────────────────────────────────────
# Why single cache (not per-loader):
#   - Per-loader @st.cache_data is NOT thread-safe on first call
#   - All 6 threads see cache miss simultaneously -> 6 concurrent API calls
#   - Athena Lambda reserved_concurrent_executions=6 -> no throttle
#   - Single cache key = 1 parallel batch fires, result cached 5 min
#
# Sequential: ~30s (6 x 5s)  |  Parallel: ~8s (bottleneck = slowest query)
# ──────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=300, show_spinner=False)
def _load_all_cached(top_n: int, cust_limit: int) -> dict:
    """
    Cache miss -> fire 6 threads in parallel -> cache result for 5 min.
    Cache hit  -> return instantly, zero API calls.
    """
    tasks = {
        "summary": lambda: load_summary(),
        "country": lambda: load_revenue_by_country(),
        "products": lambda: load_top_products(top_n),
        "trend": lambda: load_monthly_trend(),
        "customers": lambda: load_customer_behavior(cust_limit),
        "spend_dist": lambda: load_spend_distribution(),
    }
    results = {}
    load_errors = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                load_errors.append(f"{name}: {exc}")
                results[name] = pd.DataFrame()

    if load_errors:
        for err in load_errors:
            st.warning(f"⚠️  Load failed — {err}")

    return results


with st.spinner("Loading data from Athena…"):
    _data = _load_all_cached(top_n, cust_limit)
    df_summary = _data["summary"]
    df_country = _data["country"]
    df_products = _data["products"]
    df_trend = _data["trend"]
    df_customers = _data["customers"]
    df_spend_dist = _data["spend_dist"]

# coerce summary row
s = {}
if not df_summary.empty:
    row = df_summary.iloc[0]
    for col in [
        "total_orders",
        "unique_customers",
        "total_revenue",
        "avg_order_value",
        "total_units_sold",
        "unique_products",
    ]:
        s[col] = pd.to_numeric(row.get(col, 0), errors="coerce") or 0


# ══════════════════════════════════════════════════════════════════════════════
# Page header + KPI row
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# Retail Intelligence")


c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Revenue", f"${s.get('total_revenue', 0):,.0f}")
c2.metric("Total Orders", f"{s.get('total_orders', 0):,.0f}")
c3.metric("Unique Customers", f"{s.get('unique_customers', 0):,.0f}")
c4.metric("Avg Order Value", f"${s.get('avg_order_value', 0):,.2f}")
c5.metric("Units Sold", f"{s.get('total_units_sold', 0):,.0f}")
c6.metric("Unique Products", f"{s.get('unique_products', 0):,.0f}")

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tabs
# ══════════════════════════════════════════════════════════════════════════════
tab_country, tab_products, tab_customers, tab_schema = st.tabs(
    [
        "🌍  Revenue by Country",
        "📦  Trending Products",
        "👥  Customer Behavior",
        "🧬  Schema & Preview",
    ]
)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Revenue by Country
# ══════════════════════════════════════════════════════════════════════════════
with tab_country:
    if df_country.empty:
        st.info("No country data available.")

    else:
        by_country_total = (
            df_country.groupby("country", as_index=False)["total_revenue"]
            .sum()
            .sort_values("total_revenue", ascending=False)
        )

        col_a, col_b = st.columns([3, 2])

        # ──────────────────────────────────────────────────────────────────────
        # Revenue by Country
        # ──────────────────────────────────────────────────────────────────────
        with col_a:
            st.subheader("Revenue by Country")

            fig = px.bar(
                by_country_total.head(15),
                x="total_revenue",
                y="country",
                orientation="h",
                labels={"total_revenue": "Revenue ($)", "country": ""},
                color="total_revenue",
                # darker gradient
                color_continuous_scale=[
                    "#60a5fa",
                    "#2563eb",
                    "#1e3a8a",
                ],
            )

            fig.update_traces(
                marker_line_color="#1e3a8a",
                marker_line_width=1.2,
                opacity=0.95,
            )

            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="DM Sans",
                height=520,
            )

            fig.update_xaxes(
                tickprefix="$",
                gridcolor="#e2e8f0",
            )

            fig.update_yaxes(
                tickfont_size=12,
            )

            st.plotly_chart(fig, use_container_width=True)

        # ──────────────────────────────────────────────────────────────────────
        # Market Share
        # ──────────────────────────────────────────────────────────────────────
        with col_b:
            st.subheader("Market Share")

            top8 = by_country_total.head(8).copy()

            others_rev = by_country_total.iloc[8:]["total_revenue"].sum()

            if others_rev > 0:
                top8 = pd.concat(
                    [
                        top8,
                        pd.DataFrame(
                            [{"country": "Others", "total_revenue": others_rev}]
                        ),
                    ],
                    ignore_index=True,
                )

            fig2 = px.pie(
                top8,
                names="country",
                values="total_revenue",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Bold,
            )

            fig2.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont_size=11,
                insidetextorientation="radial",
            )

            fig2.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
                font_family="DM Sans",
                paper_bgcolor="white",
                height=520,
            )

            st.plotly_chart(fig2, use_container_width=True)

        # ──────────────────────────────────────────────────────────────────────
        # Revenue Heatmap
        # ──────────────────────────────────────────────────────────────────────
        st.subheader("Revenue Heatmap — Country × Month")

        pivot = df_country.pivot_table(
            index="country",
            columns="year_month",
            values="total_revenue",
            aggfunc="sum",
            fill_value=0,
        )

        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index[:12]]

        fig3 = px.imshow(
            pivot,
            labels=dict(x="Month", y="Country", color="Revenue ($)"),
            text_auto=".2s",
            color_continuous_scale=[
                [0.0, "#93c5fd"],
                [0.25, "#60a5fa"],
                [0.5, "#3b82f6"],
                [0.75, "#2563eb"],
                [1.0, "#1e3a8a"],
            ],
            aspect="auto",
        )

        fig3.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            font_family="DM Sans",
            paper_bgcolor="white",
            height=520,
        )

        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Trending Products
# ══════════════════════════════════════════════════════════════════════════════
with tab_products:
    if df_products.empty:
        st.info("No product data available.")
    else:
        col_p1, col_p2 = st.columns([3, 2])

        with col_p1:
            st.subheader(f"Top {top_n} Products by Revenue")
            fig = px.bar(
                df_products.sort_values("total_revenue"),
                x="total_revenue",
                y="product_name",
                orientation="h",
                labels={"total_revenue": "Revenue ($)", "product_name": ""},
                color="total_revenue",
                color_continuous_scale=["#d1fae5", "#065f46"],
                hover_data={
                    "times_ordered": True,
                    "total_qty": True,
                    "avg_price": True,
                },
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="DM Sans",
            )
            fig.update_xaxes(tickprefix="$", gridcolor="#f1f5f9")
            st.plotly_chart(fig, use_container_width=True)

        with col_p2:
            st.subheader("Qty vs Revenue")
            fig2 = px.scatter(
                df_products,
                x="total_qty",
                y="total_revenue",
                size="times_ordered",
                color="avg_price",
                hover_name="product_name",
                labels={
                    "total_qty": "Units Sold",
                    "total_revenue": "Revenue ($)",
                    "avg_price": "Avg Price",
                    "times_ordered": "Orders",
                },
                color_continuous_scale="Greens",
            )
            fig2.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="DM Sans",
            )
            st.plotly_chart(fig2, use_container_width=True)

        # monthly trend selector
        st.subheader("Monthly Trend")
        if not df_trend.empty:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig3 = go.Figure()
                fig3.add_trace(
                    go.Scatter(
                        x=df_trend["year_month"],
                        y=df_trend["total_revenue"],
                        mode="lines+markers",
                        name="Revenue",
                        line=dict(color="#059669", width=2),
                        marker=dict(size=6),
                        fill="tozeroy",
                        fillcolor="rgba(5,150,105,0.08)",
                    )
                )
                fig3.update_layout(
                    title="Monthly Revenue",
                    xaxis_title="Month",
                    yaxis_title="Revenue ($)",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font_family="DM Sans",
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                fig3.update_yaxes(tickprefix="$", gridcolor="#f1f5f9")
                st.plotly_chart(fig3, use_container_width=True)

            with col_t2:
                fig4 = go.Figure()
                fig4.add_trace(
                    go.Bar(
                        x=df_trend["year_month"],
                        y=df_trend["total_orders"],
                        marker_color="#6ee7b7",
                        name="Orders",
                    )
                )
                fig4.update_layout(
                    title="Monthly Orders",
                    xaxis_title="Month",
                    yaxis_title="Orders",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font_family="DM Sans",
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                fig4.update_yaxes(gridcolor="#f1f5f9")
                st.plotly_chart(fig4, use_container_width=True)

        # Product table
        with st.expander("📋 Full product table"):
            st.dataframe(
                df_products.rename(
                    columns={
                        "stock_code": "Code",
                        "product_name": "Product",
                        "times_ordered": "Orders",
                        "total_qty": "Units",
                        "total_revenue": "Revenue ($)",
                        "avg_price": "Avg Price ($)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Customer Behavior
# ══════════════════════════════════════════════════════════════════════════════
with tab_customers:
    if df_customers.empty:
        st.info("No customer data available.")
    else:
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.subheader("Spend vs Order Frequency")
            fig = px.scatter(
                df_customers,
                x="order_frequency",
                y="total_spend",
                color="country",
                hover_name="customer_id",
                size="total_units",
                labels={
                    "order_frequency": "Number of Orders",
                    "total_spend": "Total Spend ($)",
                    "total_units": "Units Bought",
                },
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="DM Sans",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            fig.update_yaxes(tickprefix="$", gridcolor="#f1f5f9")
            fig.update_xaxes(gridcolor="#f1f5f9")
            st.plotly_chart(fig, use_container_width=True)

        with col_c2:
            st.subheader("Spend Distribution by Bucket")
            if not df_spend_dist.empty:
                bucket_order = ["< $100", "$100–499", "$500–999", "$1k–4.9k", "$5k+"]
                df_spend_dist["spend_bucket"] = pd.Categorical(
                    df_spend_dist["spend_bucket"], categories=bucket_order, ordered=True
                )
                df_spend_dist = df_spend_dist.sort_values("spend_bucket")
                fig2 = px.bar(
                    df_spend_dist,
                    x="spend_bucket",
                    y="customer_count",
                    labels={
                        "spend_bucket": "Spend Tier",
                        "customer_count": "# Customers",
                    },
                    color="customer_count",
                    color_continuous_scale=["#fef3c7", "#d97706"],
                )
                fig2.update_layout(
                    coloraxis_showscale=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font_family="DM Sans",
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                fig2.update_yaxes(gridcolor="#f1f5f9")
                st.plotly_chart(fig2, use_container_width=True)

        # Avg order value distribution
        st.subheader("Avg Order Value Distribution")
        fig3 = px.histogram(
            df_customers,
            x="avg_order_value",
            nbins=30,
            labels={"avg_order_value": "Avg Order Value ($)", "count": "Customers"},
            color_discrete_sequence=["#7c3aed"],
        )
        fig3.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_family="DM Sans",
            margin=dict(l=0, r=0, t=10, b=0),
            bargap=0.05,
        )
        fig3.update_xaxes(tickprefix="$", gridcolor="#f1f5f9")
        fig3.update_yaxes(gridcolor="#f1f5f9")
        st.plotly_chart(fig3, use_container_width=True)

        # Top 20 customers table
        with st.expander("🏆 Top customers"):
            st.dataframe(
                df_customers.head(20).rename(
                    columns={
                        "customer_id": "Customer ID",
                        "country": "Country",
                        "order_frequency": "Orders",
                        "total_units": "Units",
                        "total_spend": "Total Spend ($)",
                        "avg_order_value": "Avg Order ($)",
                        "first_purchase_month": "First Purchase",
                        "last_purchase_month": "Last Purchase",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Schema & Preview
# ══════════════════════════════════════════════════════════════════════════════
with tab_schema:
    url = (api_input or API_URL).rstrip("/")

    col_s1, col_s2 = st.columns([1, 2])

    with col_s1:
        st.subheader("Table Schema")
        st.caption(
            "Live view of Glue catalog columns — updates after schema evolution."
        )
        if st.button("🔄 Refresh Schema", key="refresh_schema"):
            st.cache_data.clear()
        try:
            r = requests.post(
                url,
                json={"action": "describe_schema"},
                timeout=30,
            )
            r.raise_for_status()
            df_schema = pd.DataFrame(r.json().get("data", []))
            if not df_schema.empty:
                st.dataframe(df_schema, use_container_width=True, hide_index=True)
                st.caption(f"{len(df_schema)} columns")
            else:
                st.info("No schema data returned.")
        except Exception as exc:
            st.error(f"Schema load failed: {exc}")

    with col_s2:
        st.subheader("Data Preview")
        st.caption("SELECT * — spot-check new columns after schema evolution.")
        preview_limit = st.slider(
            "Rows", min_value=5, max_value=20, value=10, key="preview_limit"
        )
        if st.button("▶  Load Preview", key="run_preview"):
            try:
                r = requests.post(
                    url,
                    json={"action": "preview_data", "limit": preview_limit},
                    timeout=60,
                )
                r.raise_for_status()
                result = r.json()
                df_preview = pd.DataFrame(result.get("data", []))
                if df_preview.empty:
                    st.info("No data found.")
                else:
                    st.success(
                        f"{len(df_preview)} rows — {result.get('queried_at', '')}"
                    )
                    st.dataframe(df_preview, use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error(f"Preview failed: {exc}")
