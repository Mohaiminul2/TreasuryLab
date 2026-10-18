"""
pages/4_scenario_comparison.py

Page 4: Scenario Comparison
Shows the fixed Best / Base / Worst case presets side-by-side, using
forecast_scenarios() from forecasting.py.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, html

from forecasting import SCENARIO_PRESETS, forecast_scenarios
from pages._data_loader import safe_available_tickers, safe_load_metrics
from pages._ui import (
    HLINE_COLORS,
    apply_chart_defaults,
    chart_card_with_header,
    empty_state,
    fmt_days,
    fmt_money,
    fmt_pp,
    kpi_card,
    kpi_row,
    loading_wrap,
    modern_table,
    normalize_theme,
    page_header,
    scenario_colors,
    section_card,
    shortfall_alert,
    style_figure,
    ticker_dropdown_row,
)

dash.register_page(__name__, path="/scenarios", name="Scenario Comparison")


def layout():
    tickers = safe_available_tickers()
    df = safe_load_metrics()

    if df.empty:
        return dbc.Container(
            [
                page_header(
                    "Scenario Comparison",
                    "Fixed Best / Base / Worst case assumptions applied to a "
                    "12-month forward cash flow projection.",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/scenarios",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )

    presets_header = [
        html.Th("Scenario"), html.Th("Growth Δ", className="text-end"),
        html.Th("DSO Δ", className="text-end"), html.Th("DPO Δ", className="text-end"),
        html.Th("DIO Δ", className="text-end"), html.Th("Opex Ratio Δ", className="text-end"),
    ]
    presets_rows = []
    for scenario, deltas in SCENARIO_PRESETS.items():
        presets_rows.append(
            html.Tr([
                html.Td(html.Span(scenario.capitalize(), className="wc-fy-badge")),
                html.Td(fmt_pp(deltas["revenue_growth_delta"]), className="text-end font-monospace"),
                html.Td(f"{deltas['dso_delta_days']:+d} days", className="text-end font-monospace"),
                html.Td(f"{deltas['dpo_delta_days']:+d} days", className="text-end font-monospace"),
                html.Td(f"{deltas['dio_delta_days']:+d} days", className="text-end font-monospace"),
                html.Td(fmt_pp(deltas["opex_ratio_delta"]), className="text-end font-monospace"),
            ])
        )

    return dbc.Container(
        [
            page_header(
                "Scenario Comparison",
                "Fixed Best / Base / Worst case assumptions applied to a "
                "12-month forward cash flow projection.",
                meta=["Worst / Base / Best", "12-month horizon", "OCF vs ΔWCR"],
            ),
            ticker_dropdown_row("scenario-ticker-dropdown", tickers),
            loading_wrap(html.Div(id="scenario-kpis")),
            # Status banner — directly under the KPI row so shortfall risk
            # is the first thing read after the numbers.
            html.Div(id="scenario-alert", className="mb-4"),
            dbc.Row(
                [
                    dbc.Col(
                        chart_card_with_header(
                            "scenario-ocf-chart",
                            title="Operating Cash Flow",
                            subtitle="Worst / Base / Best · FY estimate",
                            icon="ocf",
                            badge="USD",
                        ),
                        xs=12, lg=6,
                        className="mb-4",
                    ),
                    dbc.Col(
                        chart_card_with_header(
                            "scenario-ccc-chart",
                            title="Cash Conversion Cycle",
                            subtitle="Days by scenario · lower is better",
                            icon="ccc",
                            badge="DAYS",
                        ),
                        xs=12, lg=6,
                        className="mb-4",
                    ),
                ],
                className="g-3 mb-3",
            ),
            section_card(
                "Scenario Assumptions",
                modern_table(presets_header, presets_rows),
                subtitle="Fixed deltas applied to the historical baseline.",
            ),
            section_card(
                "Scenario Detail",
                loading_wrap(html.Div(id="scenario-detail-table")),
                subtitle="Per-scenario forecast output for the selected company.",
            ),
        ],
        fluid=True,
        className="wc-page",
    )


@callback(
    Output("scenario-ocf-chart", "figure"),
    Output("scenario-ccc-chart", "figure"),
    Output("scenario-detail-table", "children"),
    Output("scenario-kpis", "children"),
    Output("scenario-alert", "children"),
    Input("scenario-ticker-dropdown", "value"),
    Input("store-theme", "data"),
)
def update_scenarios(ticker, theme):
    if ticker is None:
        empty = style_figure(go.Figure(), theme)
        note = empty_state("No company selected.",
                           "Choose a ticker to load its scenario forecast.",
                           action_link="/scenarios", action_text="Refresh Page")
        return empty, empty, note, note, note

    metrics_df = safe_load_metrics()
    forecast_df = forecast_scenarios(metrics_df, ticker=ticker, horizon_months=12)
    if forecast_df.empty:
        empty = style_figure(go.Figure(), theme)
        note = empty_state(f"No forecast for {ticker}.",
                           "Re-run data_fetcher.py and finance_logic.py to refresh the pipeline.",
                           action_link="/scenarios", action_text="Refresh Data")
        return empty, empty, note, note, note

    # Modern Bento bars — rounded, value labels, subtle grid (ui-ux-pro-max)
    # Theme-aware scenario hues keep >=3:1 contrast on the card surface.
    scen = scenario_colors(theme)
    ocf_fig = go.Figure()
    for _, row in forecast_df.iterrows():
        ocf_fig.add_trace(go.Bar(
            x=[row["scenario"].capitalize()],
            y=[row["operating_cf_estimate"]],
            name=row["scenario"].capitalize(),
            marker=dict(color=scen.get(row["scenario"]), line=dict(width=0), cornerradius=8),
            text=[fmt_money(row["operating_cf_estimate"])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y:$,.0f}<extra></extra>",
        ))
    t = normalize_theme(theme)
    ocf_fig.add_hline(y=0, line_dash="dot", line_color=HLINE_COLORS[t], line_width=1)
    style_figure(ocf_fig, theme, title=None)
    apply_chart_defaults(ocf_fig, theme, with_legend=False)
    ocf_fig.update_layout(
        showlegend=False,
        barmode="group",
        bargap=0.32,
        bargroupgap=0.12,
        yaxis=dict(tickprefix="$"),
        uniformtext_minsize=10, uniformtext_mode="show",
    )

    ccc_fig = go.Figure()
    for _, row in forecast_df.iterrows():
        # CCC can be negative — bar still rounded, label outside
        ccc_fig.add_trace(go.Bar(
            x=[row["scenario"].capitalize()],
            y=[row["ccc"]],
            marker=dict(color=scen.get(row["scenario"]), line=dict(width=0), cornerradius=8),
            text=[fmt_days(row["ccc"])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y:.0f} d<extra></extra>",
        ))
    style_figure(ccc_fig, theme, title=None)
    apply_chart_defaults(ccc_fig, theme, with_legend=False)
    ccc_fig.update_layout(
        showlegend=False,
        barmode="group",
        bargap=0.32,
        bargroupgap=0.12,
        yaxis=dict(ticksuffix=" d"),
        uniformtext_minsize=10, uniformtext_mode="show",
    )

    by_scenario = {r["scenario"]: r for _, r in forecast_df.iterrows()}
    kpis = kpi_row(
        [
            kpi_card(
                f"{s.capitalize()} OCF",
                fmt_money(by_scenario[s]["operating_cf_estimate"]),
                by_scenario[s]["cash_flag"],
                "bad" if by_scenario[s]["cash_flag"] == "SHORTFALL RISK" else "good",
            )
            for s in ("worst", "base", "best") if s in by_scenario
        ] + [
            kpi_card(
                "Base CCC",
                fmt_days(by_scenario["base"]["ccc"]) if "base" in by_scenario else "—",
                f"FY {forecast_df['forecast_year'].iloc[0]}",
                "default",
            ),
        ]
    )

    display_cols = [
        "scenario", "forecast_year", "revenue", "ccc",
        "working_capital_requirement", "operating_cf_estimate", "cash_flag",
    ]
    detail_header = [
        html.Th("Scenario"),
        html.Th("FY", className="text-center"),
        html.Th("Revenue", className="text-end"),
        html.Th("CCC", className="text-end"),
        html.Th("Work. Cap. Req.", className="text-end"),
        html.Th("Est. OCF", className="text-end"),
        html.Th("Flag", className="text-end"),
    ]
    detail_rows = []
    for _, row in forecast_df[display_cols].iterrows():
        flag_tone = "wc-tone-bad" if row["cash_flag"] == "SHORTFALL RISK" else "wc-tone-good"
        detail_rows.append(
            html.Tr([
                html.Td(html.Span(str(row["scenario"]).capitalize(), className="wc-fy-badge")),
                html.Td(str(int(row["forecast_year"])), className="text-center font-monospace"),
                html.Td(fmt_money(row["revenue"]), className="text-end font-monospace"),
                html.Td(fmt_days(row["ccc"]), className="text-end font-monospace"),
                html.Td(fmt_money(row["working_capital_requirement"]), className="text-end font-monospace"),
                html.Td(fmt_money(row["operating_cf_estimate"]), className="text-end font-monospace"),
                html.Td(html.Span(row["cash_flag"], className=flag_tone),
                        className="text-end"),
            ])
        )
    table = modern_table(detail_header, detail_rows)

    shortfall_scenarios = forecast_df[
        forecast_df["cash_flag"] == "SHORTFALL RISK"
    ]["scenario"].tolist()
    alert = shortfall_alert(ticker, shortfall_scenarios)

    return ocf_fig, ccc_fig, table, kpis, alert
