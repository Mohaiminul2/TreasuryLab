"""
pages/5_company_comparison.py

Page 5: Multi-Company Comparison
Benchmarks CCC and liquidity across all loaded companies side-by-side.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, html

from pages._data_loader import safe_load_metrics
from pages._ui import (
    HLINE_COLORS,
    apply_chart_defaults,
    chart_card_with_header,
    company_colors,
    day_colors,
    empty_state,
    fmt_days,
    fmt_ratio,
    insight_card,
    loading_wrap,
    normalize_theme,
    page_header,
    style_figure,
)

dash.register_page(__name__, path="/compare", name="Company Comparison")


def layout():
    df = safe_load_metrics()

    if df.empty:
        return dbc.Container(
            [
                page_header(
                    "Multi-Company Comparison",
                    "Compare working capital efficiency and liquidity across "
                    "all loaded companies for the most recent fiscal year.",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/compare",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )

    years = df["fiscal_year"].astype(int)
    latest_year = int(years.max())
    return dbc.Container(
        [
            page_header(
                "Multi-Company Comparison",
                "Compare working capital efficiency and liquidity across "
                "all loaded companies for the most recent fiscal year.",
                meta=[f"Latest FY {latest_year}", f"{df['ticker'].nunique()} companies", "Cross-company"],
            ),
            # Row 1 — Days Breakdown and Liquidity charts side-by-side
            dbc.Row(
                [
                    dbc.Col(
                        loading_wrap(chart_card_with_header(
                            "compare-days-breakdown-chart",
                            title="Days Breakdown",
                            subtitle="DSO / DPO / DIO per company",
                            icon="neutral",
                            badge="DAYS",
                        )),
                        xs=12, lg=6,
                    ),
                    dbc.Col(
                        loading_wrap(chart_card_with_header(
                            "compare-liquidity-chart",
                            title="Liquidity Ratios",
                            subtitle="Current vs Quick ratio · most recent year",
                            icon="ocf",
                            badge="×",
                        )),
                        xs=12, lg=6,
                    ),
                ],
                className="g-3 mb-4",
            ),
            # Insights row - compact insights side by side
            dbc.Row(
                [
                    dbc.Col(
                        loading_wrap(html.Div(id="compare-days-insight", className="mb-3")),
                        xs=12, lg=6,
                    ),
                    dbc.Col(
                        loading_wrap(html.Div(id="compare-liquidity-insight", className="mb-3")),
                        xs=12, lg=6,
                    ),
                ],
                className="g-3 mb-4",
            ),
            # Row 2 — CCC chart (full width)
            dbc.Row(
                [
                    dbc.Col(
                        loading_wrap(chart_card_with_header(
                            "compare-ccc-chart",
                            title="Cash Conversion Cycle",
                            subtitle="Companies compared · most recent year",
                            icon="ccc",
                            badge="DAYS",
                        )),
                        xs=12,
                    ),
                ],
                className="g-3 mb-4",
            ),
            # CCC Insight
            loading_wrap(html.Div(id="compare-ccc-insight", className="mb-3")),
        ],
        fluid=True,
        className="wc-page",
    )


@callback(
    Output("compare-ccc-chart", "figure"),
    Output("compare-liquidity-chart", "figure"),
    Output("compare-days-breakdown-chart", "figure"),
    Output("compare-ccc-insight", "children"),
    Output("compare-liquidity-insight", "children"),
    Output("compare-days-insight", "children"),
    Input("url", "pathname"),
    Input("store-theme", "data"),
)
def update_comparison(pathname, theme):
    df = safe_load_metrics()
    if df.empty:
        empty = style_figure(go.Figure(), theme)
        note = empty_state(
            "No comparable metrics available.",
            "Run the pipeline (data_fetcher.py + finance_logic.py) to load company data.",
            action_link="/compare",
            action_text="Refresh Page"
        )
        return empty, empty, empty, note, note, note

    t = normalize_theme(theme)
    # Shared, theme-aware palettes: per-company hues from _ui (blue /
    # amber / green trio) and the same DSO/DPO/DIO hues as page 2.
    company_palette = company_colors(theme)
    days_palette = day_colors(theme)

    # Take latest fiscal year available per ticker
    latest_rows = df.sort_values("fiscal_year").groupby("ticker").tail(1)
    latest_rows = latest_rows.dropna(subset=["ccc", "current_ratio", "quick_ratio"], how="all")
    tickers = latest_rows["ticker"].tolist()

    if not tickers:
        empty = style_figure(go.Figure(), theme)
        note = empty_state(
            "No comparable metrics available.",
            "Loaded companies lack CCC / liquidity data for the latest fiscal year.",
            action_link="/compare",
            action_text="Refresh Page"
        )
        return empty, empty, empty, note, note, note

    # Helper to assign colors round-robin
    def _bar_color(i):
        return company_palette[i % len(company_palette)]

    # ---- CCC Chart (single series, multiple companies) ----
    ccc_fig = go.Figure()
    for i, ticker in enumerate(tickers):
        ccc_fig.add_trace(go.Bar(
            x=[ticker],
            y=[latest_rows.loc[latest_rows["ticker"] == ticker, "ccc"].values[0]],
            name=ticker,
            marker=dict(color=_bar_color(i), line=dict(width=0), cornerradius=8),
            text=[fmt_days(latest_rows.loc[latest_rows["ticker"] == ticker, "ccc"].values[0])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"{ticker}: %{{y:.0f}} d<extra></extra>",
        ))
    ccc_fig.add_hline(y=0, line_dash="dot", line_color=HLINE_COLORS[t], line_width=1)
    style_figure(ccc_fig, theme, title=None)
    apply_chart_defaults(ccc_fig, theme, with_legend=False)
    ccc_fig.update_layout(
        barmode="group",
        bargap=0.32,
        bargroupgap=0.12,
        showlegend=False,
        yaxis=dict(ticksuffix=" d"),
        xaxis=dict(tickangle=0),
        uniformtext_minsize=9,
        uniformtext_mode="show",
    )

    # ---- Liquidity Chart (two grouped series per company) ----
    liq_fig = go.Figure()
    for i, ticker in enumerate(tickers):
        curr_val = latest_rows.loc[latest_rows["ticker"] == ticker, "current_ratio"].values[0]
        quick_val = latest_rows.loc[latest_rows["ticker"] == ticker, "quick_ratio"].values[0]
        color = _bar_color(i)
        # Current ratio
        liq_fig.add_trace(go.Bar(
            x=[ticker],
            y=[curr_val],
            name=f"{ticker} · Current",
            marker=dict(color=color, line=dict(width=0), cornerradius=8),
            text=[fmt_ratio(curr_val)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"{ticker}<br>Current: %{{y:.2f}}×<extra></extra>",
        ))
        # Quick ratio
        liq_fig.add_trace(go.Bar(
            x=[ticker],
            y=[quick_val],
            name=f"{ticker} · Quick",
            marker=dict(color=color, opacity=0.55, line=dict(width=0), cornerradius=8),
            text=[fmt_ratio(quick_val)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"{ticker}<br>Quick: %{{y:.2f}}×<extra></extra>",
        ))
    style_figure(liq_fig, theme, title=None)
    apply_chart_defaults(liq_fig, theme, with_legend=True, legend_small=True)
    liq_fig.update_layout(
        barmode="group",
        bargap=0.32,
        bargroupgap=0.12,
        yaxis=dict(ticksuffix="×"),
        xaxis=dict(tickangle=0),
        uniformtext_minsize=9,
        uniformtext_mode="show",
    )

    # ---- Days Breakdown Chart — 3 legend items (DSO/DPO/DIO) fits one line ----
    days_fig = go.Figure()
    for col, label in [("dso", "DSO"), ("dpo", "DPO"), ("dio", "DIO")]:
        vals = [latest_rows.loc[latest_rows["ticker"] == t, col].values[0] for t in tickers]
        days_fig.add_trace(go.Bar(
            x=tickers,
            y=vals,
            name=label,
            marker=dict(color=days_palette[col], line=dict(width=0), cornerradius=8),
            text=[fmt_days(v) for v in vals],
            textposition="outside",
            cliponaxis=False,
        ))
    style_figure(days_fig, theme, title=None)
    apply_chart_defaults(days_fig, theme, with_legend=True, legend_small=True)
    days_fig.update_layout(
        barmode="group",
        bargap=0.32,
        bargroupgap=0.12,
        yaxis=dict(ticksuffix=" d"),
        xaxis=dict(tickangle=0),
        uniformtext_minsize=9,
        uniformtext_mode="show",
    )

    # ---- Insight Cards ----
    # CCC Insight
    ccc_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "ccc"].values[0] for t in tickers}
    best_ccc = min(ccc_vals, key=ccc_vals.get)
    worst_ccc = max(ccc_vals, key=ccc_vals.get)
    ccc_range = abs(ccc_vals[worst_ccc] - ccc_vals[best_ccc])
    has_neg = any(v < 0 for v in ccc_vals.values())
    if has_neg:
        neg_comps = [t for t, v in ccc_vals.items() if v < 0]
        ccc_note = f"{', '.join(neg_comps)} have negative CCC — they fund ops from suppliers before collecting."
    else:
        ccc_note = f"All companies carry positive CCC. {worst_ccc} ties up capital the longest."
    ccc_insight = insight_card(
        "CCC Insight",
        f"{best_ccc} leads with {fmt_days(ccc_vals[best_ccc])}, {worst_ccc} lags at "
        f"{fmt_days(ccc_vals[worst_ccc])}. Spread: {fmt_days(ccc_range)}. {ccc_note}",
        tone="warning",
    )

    # Liquidity Insight
    curr_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "current_ratio"].values[0] for t in tickers}
    quick_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "quick_ratio"].values[0] for t in tickers}
    strong_liq = max(curr_vals, key=curr_vals.get)
    weak_liq = [t for t in tickers if curr_vals[t] < 1.0]
    inv_gaps = {t: curr_vals[t] - quick_vals[t] for t in tickers}
    high_inv = max(inv_gaps, key=inv_gaps.get)
    liq_parts = [f"{strong_liq} strongest at {fmt_ratio(curr_vals[strong_liq])}."]
    if weak_liq:
        liq_parts.append(f"{', '.join(weak_liq)} below 1.0× — monitor closely.")
    else:
        liq_parts.append("All above 1.0× threshold.")
    liq_parts.append(f"{high_inv} most inventory-dependent ({fmt_ratio(inv_gaps[high_inv])} gap).")
    liq_insight = insight_card(
        "Liquidity Insight",
        " ".join(liq_parts),
        tone="info",
    )

    # Days Breakdown Insight
    dso_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "dso"].values[0] for t in tickers}
    dpo_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "dpo"].values[0] for t in tickers}
    dio_vals = {t: latest_rows.loc[latest_rows["ticker"] == t, "dio"].values[0] for t in tickers}
    fast_coll = min(dso_vals, key=dso_vals.get)
    slow_coll = max(dso_vals, key=dso_vals.get)
    fast_pay = min(dpo_vals, key=dpo_vals.get)
    slow_pay = max(dpo_vals, key=dpo_vals.get)
    fast_inv = min(dio_vals, key=dio_vals.get)
    slow_inv = max(dio_vals, key=dio_vals.get)
    days_parts = [
        f"DSO: {fast_coll} collects fastest ({fmt_days(dso_vals[fast_coll])}), "
        f"{slow_coll} slowest ({fmt_days(dso_vals[slow_coll])}). ",
        f"DPO: {fast_pay} pays fastest ({fmt_days(dpo_vals[fast_pay])}), "
        f"{slow_pay} slowest ({fmt_days(dpo_vals[slow_pay])}). ",
        f"DIO: {fast_inv} moves inventory fastest ({fmt_days(dio_vals[fast_inv])}), "
        f"{slow_inv} slowest ({fmt_days(dio_vals[slow_inv])}).",
    ]
    days_insight = insight_card(
        "Days Breakdown Insight",
        "".join(days_parts),
        tone="success",
    )

    return ccc_fig, liq_fig, days_fig, ccc_insight, liq_insight, days_insight
