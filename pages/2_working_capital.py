"""
pages/2_working_capital.py

Page 2: Working Capital Analysis
DSO / DPO / DIO / Cash Conversion Cycle trend, plus liquidity ratios.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, html

from pages._data_loader import safe_available_tickers, safe_load_metrics
from pages._ui import (
    HLINE_COLORS,
    apply_chart_defaults,
    chart_card_with_header,
    day_colors,
    empty_state,
    fmt_days,
    fmt_ratio,
    kpi_card,
    kpi_row,
    loading_wrap,
    marker_edge,
    normalize_theme,
    page_header,
    style_figure,
    ticker_dropdown_row,
    year_labels,
)

dash.register_page(__name__, path="/working-capital", name="Working Capital")


def layout():
    tickers = safe_available_tickers()
    df = safe_load_metrics()

    if df.empty:
        return dbc.Container(
            [
                page_header(
                    "Working Capital Analysis",
                    "Days Sales Outstanding (DSO), Days Payable Outstanding (DPO), "
                    "Days Inventory Outstanding (DIO), and the resulting Cash "
                    "Conversion Cycle (CCC = DSO + DIO − DPO).",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/working-capital",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )

    return dbc.Container(
        [
            page_header(
                "Working Capital Analysis",
                "Days Sales Outstanding (DSO), Days Payable Outstanding (DPO), "
                "Days Inventory Outstanding (DIO), and the resulting Cash "
                "Conversion Cycle (CCC = DSO + DIO − DPO).",
                meta=["DSO / DPO / DIO · × 365", "CCC = DSO + DIO − DPO", "Days"],
            ),
            ticker_dropdown_row("wc-ticker-dropdown", tickers),
            loading_wrap(html.Div(id="wc-kpis")),
            dbc.Row(
                [
                    dbc.Col(
                        chart_card_with_header(
                            "wc-days-chart",
                            title="DSO / DPO / DIO (days)",
                            subtitle="Collection · Payment · Inventory days",
                            icon="ocf",
                            badge="DAYS",
                        ),
                        xs=12, lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        chart_card_with_header(
                            "wc-ccc-chart",
                            title="Cash Conversion Cycle",
                            subtitle="DSO + DIO − DPO · days",
                            icon="ccc",
                            badge="DAYS",
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
                            "wc-liquidity-chart",
                            title="Liquidity Ratios",
                            subtitle="Current · Quick ratio",
                            icon="neutral",
                            badge="×",
                        ),
                        xs=12,
                        className="mb-4",
                    ),
                ],
                className="g-3 mb-4",
            ),
        ],
        fluid=True,
        className="wc-page",
    )


@callback(
    Output("wc-days-chart", "figure"),
    Output("wc-ccc-chart", "figure"),
    Output("wc-liquidity-chart", "figure"),
    Output("wc-kpis", "children"),
    Input("wc-ticker-dropdown", "value"),
    Input("store-theme", "data"),
)
def update_wc_page(ticker, theme):
    if ticker is None:
        empty = style_figure(go.Figure(), theme)
        return empty, empty, empty, empty_state(
            "No company selected.", "Choose a ticker to load its working capital metrics.",
            action_link="/working-capital",
            action_text="Refresh Page"
        )

    df = safe_load_metrics()
    company_df = df[df["ticker"] == ticker].sort_values("fiscal_year")
    years = year_labels(company_df)
    if company_df.empty:
        empty = style_figure(go.Figure(), theme)
        return empty, empty, empty, empty_state(
            f"No data for {ticker}.",
            "Re-run data_fetcher.py and finance_logic.py to refresh the pipeline.",
            action_link="/working-capital",
            action_text="Refresh Data"
        )

    latest = company_df.iloc[-1]
    liq_tone = (
        "good" if latest.get("current_ratio") and latest["current_ratio"] >= 1.0
        else "bad"
    )
    kpis = kpi_row(
        [
            kpi_card("DSO", fmt_days(latest.get("dso")), "Collection days", "info"),
            kpi_card("DPO", fmt_days(latest.get("dpo")), "Payment days", "info"),
            kpi_card("DIO", fmt_days(latest.get("dio")), "Inventory days", "info"),
            kpi_card("CCC", fmt_days(latest.get("ccc")), "DSO + DIO − DPO", "default"),
            kpi_card("Current ratio", fmt_ratio(latest.get("current_ratio")),
                     "≥ 1.0× is healthy", liq_tone),
            kpi_card("Quick ratio", fmt_ratio(latest.get("quick_ratio")),
                     "Excl. inventory", liq_tone),
        ]
    )

    # DSO / DPO / DIO — Bento spline lines (hover styling shared via _ui)
    t = normalize_theme(theme)
    palette = day_colors(theme)
    edge = marker_edge(theme)
    days_fig = go.Figure()
    for col, label in [("dso", "DSO"), ("dpo", "DPO"), ("dio", "DIO")]:
        color = palette[col]
        days_fig.add_trace(go.Scatter(
            x=years, y=company_df[col],
            mode="lines+markers", name=label,
            line=dict(width=2.6, color=color, shape="spline", smoothing=0.35),
            marker=dict(size=7, color=color, line=dict(width=1.5, color=edge)),
            hovertemplate=f"{label}<br>%{{x}}: %{{y:.0f}} d<extra></extra>",
        ))
    style_figure(days_fig, theme, title=None)
    apply_chart_defaults(days_fig, theme, with_legend=True, legend_small=True)
    days_fig.update_layout(yaxis=dict(ticksuffix=" d"))

    # CCC — Bento bars matching Scenario Comparison style (rounded, outside labels)
    ccc_fig = go.Figure()
    ccc_fig.add_trace(go.Bar(
        x=years, y=company_df["ccc"], name="CCC",
        marker=dict(color=palette["ccc"], line=dict(width=0), cornerradius=8),
        text=[f"{v:.0f} d" for v in company_df["ccc"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x}: %{y:.0f} d<extra></extra>",
    ))
    style_figure(ccc_fig, theme, title=None)
    apply_chart_defaults(ccc_fig, theme, with_legend=False)
    ccc_fig.update_layout(
        showlegend=False,
        barmode="group", bargap=0.32, bargroupgap=0.12,
        yaxis=dict(ticksuffix=" d"),
        uniformtext_minsize=10, uniformtext_mode="show",
    )

    # Liquidity — Bento spline lines with threshold reference
    liq_fig = go.Figure()
    for col, label in [("current_ratio", "Current Ratio"), ("quick_ratio", "Quick Ratio")]:
        color = palette[col]
        liq_fig.add_trace(go.Scatter(
            x=years, y=company_df[col],
            mode="lines+markers", name=label,
            line=dict(width=2.6, color=color, shape="spline", smoothing=0.35),
            marker=dict(size=7, color=color, line=dict(width=1.5, color=edge)),
            hovertemplate=f"{label}<br>%{{x}}: %{{y:.2f}}×<extra></extra>",
        ))
    liq_fig.add_hline(y=1.0, line_dash="dot", line_color=HLINE_COLORS[t], line_width=1.5)
    style_figure(liq_fig, theme, title=None)
    apply_chart_defaults(liq_fig, theme, with_legend=True, legend_small=True)
    liq_fig.update_layout(yaxis=dict(ticksuffix="×"))

    return days_fig, ccc_fig, liq_fig, kpis
