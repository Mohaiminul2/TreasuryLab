"""
pages/1_overview.py

Page 1: Company Overview
Ticker selector + summary view of Revenue, COGS, Net Income and key
balance sheet items over the available historical years.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, html

from pages._data_loader import safe_available_tickers, safe_load_metrics
from pages._ui import (
    apply_chart_defaults,
    bs_colors,
    chart_card_with_header,
    empty_state,
    fmt_days,
    fmt_money,
    fmt_pct,
    kpi_card,
    kpi_row,
    loading_wrap,
    modern_table,
    page_header,
    section_card,
    series_colors,
    style_figure,
    ticker_dropdown_row,
    year_labels,
)

dash.register_page(__name__, path="/", name="Overview")


def layout():
    tickers = safe_available_tickers()
    df = safe_load_metrics()
    
    if df.empty:
        # No data available — show friendly empty state
        return dbc.Container(
            [
                page_header(
                    "Company Overview",
                    "Select a company to view its historical revenue, cost, "
                    "profitability, and balance sheet trend, sourced from "
                    "yfinance annual filings.",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )
    
    years = df["fiscal_year"].astype(int)
    meta = [
        f"FY {years.min()}–{years.max()}",
        "Annual filings",
        "USD",
    ]
    return dbc.Container(
        [
            page_header(
                "Company Overview",
                "Select a company to view its historical revenue, cost, "
                "profitability, and balance sheet trend, sourced from "
                "yfinance annual filings.",
                meta=meta,
            ),
            ticker_dropdown_row("overview-ticker-dropdown", tickers),
            loading_wrap(html.Div(id="overview-kpis")),
            dbc.Row(
                [
                    dbc.Col(
                        chart_card_with_header(
                            "overview-revenue-chart",
                            title="Revenue vs COGS",
                            subtitle="Annual grouped columns · FY",
                            icon="ocf",
                            badge="USD",
                        ),
                        xs=12, lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        chart_card_with_header(
                            "overview-margin-chart",
                            title="Net Margin Trend",
                            subtitle="Net income / revenue · %",
                            icon="ccc",
                            badge="%",
                        ),
                        xs=12, lg=6,
                        className="mb-4",
                    ),
                ],
                className="g-3 mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        chart_card_with_header(
                            "overview-balance-sheet-chart",
                            title="Working Capital Items",
                            subtitle="AR / Inventory / AP / Cash · trend",
                            icon="neutral",
                            badge="USD",
                        ),
                        xs=12,
                        className="mb-4",
                    )
                ],
                className="g-3 mb-4",
            ),
            section_card(
                "Raw Historical Data",
                loading_wrap(html.Div(id="overview-data-table")),
                subtitle="Compact USD formatting (auto-scaled B / M / K), no decimals.",
            ),
        ],
        fluid=True,
        className="wc-page",
    )


@callback(
    Output("overview-revenue-chart", "figure"),
    Output("overview-margin-chart", "figure"),
    Output("overview-balance-sheet-chart", "figure"),
    Output("overview-data-table", "children"),
    Output("overview-kpis", "children"),
    Input("overview-ticker-dropdown", "value"),
    Input("store-theme", "data"),
)
def update_overview(ticker, theme):
    if ticker is None:
        empty = style_figure(go.Figure(), theme)
        no_selection = empty_state("No company selected.",
                                  "Choose a ticker to load its historical metrics.",
                                  action_link="/",
                                  action_text="Refresh Page")
        return empty, empty, empty, no_selection, no_selection

    df = safe_load_metrics()
    company_df = df[df["ticker"] == ticker].sort_values("fiscal_year")
    years = year_labels(company_df)
    if company_df.empty:
        empty = style_figure(go.Figure(), theme)
        no_data = empty_state(
            f"No data for {ticker}.",
            "Re-run data_fetcher.py and finance_logic.py to refresh the pipeline.",
            action_link="/",
            action_text="Refresh Data"
        )
        return empty, empty, empty, no_data, no_data

    latest = company_df.iloc[-1]
    net_margin = (
        latest["net_income"] / latest["revenue"]
        if latest.get("revenue") else float("nan")
    )

    kpis = kpi_row(
        [
            kpi_card("Revenue (latest)", fmt_money(latest.get("revenue")),
                     f"FY {int(latest['fiscal_year'])}", "info"),
            kpi_card("Net margin", fmt_pct(net_margin),
                     f"Net income {fmt_money(latest.get('net_income'))}",
                     "good" if net_margin and net_margin > 0 else "bad"),
            kpi_card("Work. cap. req.", fmt_money(latest.get("working_capital_requirement")),
                     "AR + Inventory − AP", "warn"),
            kpi_card("Cash conv. cycle", fmt_days(latest.get("ccc")),
                     f"DSO {latest.get('dso', float('nan')):.0f} + "
                     f"DIO {latest.get('dio', float('nan')):.0f} − "
                     f"DPO {latest.get('dpo', float('nan')):.0f}",
                     "default"),
        ]
    )

    # Revenue & COGS — Bento column (matches Scenario OCF)
    series = series_colors(theme)
    revenue_fig = go.Figure()
    revenue_fig.add_trace(go.Bar(
        x=years, y=company_df["revenue"], name="Revenue",
        marker=dict(color=series["primary"], line=dict(width=0), cornerradius=8),
        text=[fmt_money(v) for v in company_df["revenue"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>Revenue: %{y:$,.0f}<extra></extra>",
    ))
    revenue_fig.add_trace(go.Bar(
        x=years, y=company_df["cogs"], name="COGS",
        marker=dict(color=series["secondary"], line=dict(width=0), cornerradius=8),
        text=[fmt_money(v) for v in company_df["cogs"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>COGS: %{y:$,.0f}<extra></extra>",
    ))
    style_figure(revenue_fig, theme, title=None)
    apply_chart_defaults(revenue_fig, theme, with_legend=True)
    revenue_fig.update_layout(
        barmode="group", bargap=0.32, bargroupgap=0.12,
        yaxis=dict(tickprefix="$"),
        uniformtext_minsize=10, uniformtext_mode="show",
    )

    # Net income margin — line in Bento card (primary hue, like Revenue)
    margin_fig = go.Figure()
    if "net_income" in company_df.columns:
        margin_fig.add_trace(go.Scatter(
            x=years,
            y=company_df["net_income"] / company_df["revenue"],
            mode="lines+markers", name="Net Margin",
            line=dict(width=2.5, color=series["primary"]),
            marker=dict(size=7, color=series["primary"]),
        ))
    style_figure(margin_fig, theme, title=None)
    apply_chart_defaults(margin_fig, theme, with_legend=False)
    margin_fig.update_layout(
        yaxis_tickformat=".1%",
        showlegend=False,
    )

    # Balance sheet composition — Bento (theme-aware, consistent with
    # the day-metric palette: AR blue / inventory amber / AP rose / cash green)
    bs = bs_colors(theme)
    bs_fig = go.Figure()
    for col, label in [
        ("accounts_receivable", "Accounts Receivable"),
        ("inventory", "Inventory"),
        ("accounts_payable", "Accounts Payable"),
        ("cash", "Cash"),
    ]:
        if col in company_df.columns:
            bs_fig.add_trace(go.Scatter(
                x=years, y=company_df[col],
                mode="lines+markers", name=label,
                line=dict(width=2.2, color=bs[col]),
                marker=dict(size=6, color=bs[col]),
            ))
    style_figure(bs_fig, theme, title=None)
    apply_chart_defaults(bs_fig, theme, with_legend=True)
    bs_fig.update_layout(yaxis=dict(tickprefix="$"))

    # Raw data table — Bento modern (dense, horizontal scroll, FY pill)
    display_cols = [
        "fiscal_year", "revenue", "cogs", "net_income",
        "accounts_receivable", "accounts_payable", "inventory", "cash",
    ]
    display_cols = [c for c in display_cols if c in company_df.columns]
    header_labels = {
        "fiscal_year": "FY",
        "revenue": "Revenue",
        "cogs": "COGS",
        "net_income": "Net Income",
        "accounts_receivable": "Accounts Receivable",
        "accounts_payable": "Accounts Payable",
        "inventory": "Inventory",
        "cash": "Cash",
    }
    header_cells = [
        html.Th(
            header_labels.get(col, col.replace("_", " ").title()),
            className="text-center" if col == "fiscal_year" else "text-end",
            style={"whiteSpace": "nowrap"},
        )
        for col in display_cols
    ]
    body_rows = [
        html.Tr(
            [
                html.Td(
                    html.Span(str(int(row["fiscal_year"])), className="wc-fy-badge"),
                    className="text-center",
                )
                if col == "fiscal_year"
                else html.Td(
                    fmt_money(row[col]),
                    className="text-end font-monospace",
                    style={"whiteSpace": "nowrap"},
                )
                for col in display_cols
            ]
        )
        for _, row in company_df[display_cols].iterrows()
    ]
    table = modern_table(header_cells, body_rows)

    return revenue_fig, margin_fig, bs_fig, table, kpis
