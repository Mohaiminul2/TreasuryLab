"""
pages/3_forecast.py

Page 3: Forecast & Assumptions
Lets the user adjust growth rate / DSO / DPO / DIO / opex assumptions
via sliders and see the resulting 12-month forecast update live.
This is a CUSTOM scenario on top of the fixed Best/Base/Worst presets
(those live on Page 4 — Scenario Comparison).
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from forecasting import custom_scenario
from pages._data_loader import safe_available_tickers, safe_load_metrics
from pages._ui import (
    CHART_PALETTES,
    apply_chart_defaults,
    chart_card_with_header,
    empty_state,
    fmt_days,
    fmt_money,
    kpi_card,
    kpi_row,
    loading_wrap,
    normalize_theme,
    page_header,
    panel_card,
    status_banner,
    style_figure,
    ticker_dropdown_row,
)

dash.register_page(__name__, path="/forecast", name="Forecast & Assumptions")


def layout():
    tickers = safe_available_tickers()
    df = safe_load_metrics()

    if df.empty:
        return dbc.Container(
            [
                page_header(
                    "Forecast & Assumptions",
                    "Adjust assumptions below to see how the 12-month cash flow "
                    "forecast responds. This is a custom scenario — use the "
                    "Scenario Comparison page for the fixed Best/Base/Worst presets.",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/forecast",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )

    return dbc.Container(
        [
            page_header(
                "Forecast & Assumptions",
                "Adjust assumptions below to see how the 12-month cash flow "
                "forecast responds. This is a custom scenario — use the "
                "Scenario Comparison page for the fixed Best/Base/Worst presets.",
                meta=["Custom scenario", "12-month horizon", "Sliders vs historical baseline"],
            ),
            # Row 1 — Ticker selector
            ticker_dropdown_row("forecast-ticker-dropdown", tickers),
            # Row 2 — KPIs (same position as every other page)
            loading_wrap(html.Div(id="forecast-kpis")),
            # Row 3 — Controls (left) + Chart (right, with the insight
            # banner rendered inside the card above the graph)
            dbc.Row(
                [
                    # Sliders panel — left side
                    dbc.Col(
                        html.Div(
                            [
                                panel_card(
                                    "Assumptions",
                                    "Adjust to project cash flow",
                                    icon="sliders",
                                    className="wc-assumptions-panel",
                                    children=[
                                        _slider_group("growth", "Revenue Growth", "pp", -20, 20, "vs hist avg"),
                                        _slider_group("dso",  "DSO",           "days", -30, 30, "collection days"),
                                        _slider_group("dpo",  "DPO",           "days", -30, 30, "payment days"),
                                        _slider_group("dio",  "DIO",           "days", -30, 30, "inventory days"),
                                        _slider_group("opex", "Opex Ratio",    "pp", -10, 10, "% of revenue"),
                                    ],
                                ),
                            ],
                            className="h-100",
                        ),
                        xs=12,
                        lg=3,
                        className="mb-4",
                    ),
                    # Chart panel — right side (insight banner sits inside
                    # the card, below the chart + its legend, centered)
                    dbc.Col(
                        chart_card_with_header(
                            "forecast-cf-chart",
                            title="Cash Flow Forecast",
                            subtitle="Custom scenario · Net Income + OCF",
                            icon="ocf",
                            badge="USD",
                            height=400,
                            below_graph=[
                                html.Div(
                                    id="forecast-insight-box",
                                    className="d-flex justify-content-center pt-3 pb-1",
                                ),
                            ],
                        ),
                        xs=12,
                        lg=9,
                        className="mb-4",
                    ),
                ],
                className="g-3",
            ),
        ],
        fluid=True,
        className="wc-page",
    )


def _slider_group(slider_id, label, unit, min_val, max_val, hint):
    """Enhanced slider group with label + live value badge + hint."""
    return html.Div(
        [
            html.Div(
                [
                    html.Strong(label, className="me-2"),
                    html.Small(f"({unit})", className="text-muted me-2"),
                    html.Span("0", id=f"slider-{slider_id}-val", className="slider-val-badge ms-auto"),
                ],
                className="d-flex align-items-between mb-2",
            ),
            html.Small(hint, className="text-muted"),
            dcc.Slider(
                id=f"slider-{slider_id}",
                min=min_val, max=max_val, step=1, value=0,
                marks=None,
                className="mt-2",
            ),
        ],
        className="mb-4",
    )


@callback(
    Output("forecast-cf-chart", "figure"),
    Output("forecast-insight-box", "children"),
    Output("forecast-kpis", "children"),
    Output("slider-growth-val", "children"),
    Output("slider-dso-val", "children"),
    Output("slider-dpo-val", "children"),
    Output("slider-dio-val", "children"),
    Output("slider-opex-val", "children"),
    Input("forecast-ticker-dropdown", "value"),
    Input("slider-growth", "value"),
    Input("slider-dso", "value"),
    Input("slider-dpo", "value"),
    Input("slider-dio", "value"),
    Input("slider-opex", "value"),
    Input("store-theme", "data"),
)
def update_forecast(ticker, growth_adj, dso_adj, dpo_adj, dio_adj, opex_adj, theme):
    # Badges must tolerate float slider values ("+5.0" is valid input,
    # but the old "{:+d}" format crashed on it with a ValueError).
    badges = [f"{int(v):+d}" if v else "0" for v in (growth_adj or 0, dso_adj or 0, dpo_adj or 0,
                                                    dio_adj or 0, opex_adj or 0)]
    if ticker is None:
        empty = style_figure(go.Figure(), theme)
        note = empty_state("No company selected.",
                           "Choose a ticker to load its forecast.",
                           action_link="/forecast", action_text="Refresh Page")
        return (empty, note, note, *badges)

    df = safe_load_metrics()
    company_df = df[df["ticker"] == ticker].sort_values("fiscal_year")
    if company_df.empty:
        empty = style_figure(go.Figure(), theme)
        note = empty_state(f"No data for {ticker}.",
                           "Re-run data_fetcher.py and finance_logic.py to refresh the pipeline.",
                           action_link="/forecast", action_text="Refresh Data")
        return (empty, note, note, *badges)

    # Single source of truth: same engine as the fixed presets.
    result = custom_scenario(
        df, ticker=ticker,
        growth_adj_pp=growth_adj or 0,
        dso_adj_days=dso_adj or 0,
        dpo_adj_days=dpo_adj or 0,
        dio_adj_days=dio_adj or 0,
        opex_adj_pp=opex_adj or 0,
    )
    forecast_net_income = result["net_income_estimate"]
    forecast_ocf = result["operating_cf_estimate"]
    delta_wcr = result["delta_wcr_vs_latest"]

    # Forecast CF — Bento column: historical actuals + vivid projection slot
    # (replaces the old dual-area chart: stacking summed the two series and
    #  placed 2 values on a 13-point month axis).
    t = normalize_theme(theme)
    pal = CHART_PALETTES[t]

    hist = company_df.tail(4)  # last four fiscal years of actuals
    forecast_year = int(result["forecast_year"])
    x_labels = [str(int(y)) for y in hist["fiscal_year"]] + [f"{forecast_year}E"]

    # Net income: muted bars for actuals, one vivid bar for the estimate
    ni_y = hist["net_income"].tolist() + [forecast_net_income]
    ocf_y = hist["operating_cf"].tolist() + [forecast_ocf]

    fig = go.Figure()
    for i, (year, val) in enumerate(zip(x_labels, ni_y)):
        is_forecast = i == len(x_labels) - 1
        fig.add_trace(go.Bar(
            x=[year], y=[val], name="Net Income" if not is_forecast else "Net Income (est.)",
            legendgroup="ni",
            showlegend=(i == 0),
            marker=dict(
                color=pal["ni_forecast"] if is_forecast else pal["ni_actual"],
                line=dict(width=0), cornerradius=8,
            ),
            text=[fmt_money(val)], textposition="outside", cliponaxis=False,
            hovertemplate="%{x}<br>Net Income: %{y:$,.0f}<extra></extra>",
        ))
    for i, (year, val) in enumerate(zip(x_labels, ocf_y)):
        is_forecast = i == len(x_labels) - 1
        fig.add_trace(go.Bar(
            x=[year], y=[val], name="Est. OCF" if is_forecast else "Operating CF",
            legendgroup="ocf",
            showlegend=(i == 0),
            marker=dict(
                color=pal["ocf_forecast"] if is_forecast else pal["ocf_actual"],
                line=dict(width=0), cornerradius=8,
            ),
            text=[fmt_money(val)], textposition="outside", cliponaxis=False,
            hovertemplate="%{x}<br>Operating CF: %{y:$,.0f}<extra></extra>",
        ))

    style_figure(fig, theme, title=None)
    apply_chart_defaults(fig, theme, with_legend=True, legend_small=True)

    # Shade the projection slot + divider between actuals and forecast
    fig.add_vrect(
        x0=-0.5, x1=len(x_labels) - 1.5,
        fillcolor=pal["zone"], line_width=0,
    )
    fig.add_vline(
        x=len(x_labels) - 1.5, line_dash="dot",
        line_color=pal["separator"], line_width=1.2,
    )
    fig.add_annotation(
        x=len(x_labels) - 1, y=1.02, yref="y domain", xref="x",
        text="PROJECTION", showarrow=False,
        font=dict(size=9, color=pal["zone_label"], family="Inter, sans-serif"),
        yanchor="bottom",
    )

    fig.update_layout(
        yaxis_tickprefix="$",
        barmode="group", bargap=0.32, bargroupgap=0.08,
        uniformtext_minsize=10, uniformtext_mode="show",
    )
    fig.add_hline(y=0, line_dash="dot", line_color=pal["zero_line"], line_width=1)

    ocf_tone = "bad" if forecast_ocf is not None and forecast_ocf < 0 else "good"
    kpis = kpi_row(
        [
            kpi_card("Est. net income", fmt_money(forecast_net_income),
                     f"FY {result['forecast_year']}", "info"),
            kpi_card("Est. operating CF", fmt_money(forecast_ocf),
                     result["cash_flag"], ocf_tone),
            kpi_card("Δ work. cap. req.", fmt_money(delta_wcr),
                     "↑ consumes cash", "warn"),
            kpi_card("Forecast CCC", fmt_days(result["ccc"]),
                     f"DSO {result['dso']:.0f} + DIO {result['dio']:.0f} − "
                     f"DPO {result['dpo']:.0f}", "default"),
        ]
    )

    # Unified status banner (same markup as the Scenario page) — cyan
    # OCF context is kept via the chart palette; the banner itself uses
    # the shared risk/ok treatment so both pages read identically.
    if result["cash_flag"] == "SHORTFALL RISK":
        insight = status_banner(
            "risk",
            "SHORTFALL RISK",
            f"Under these assumptions, {ticker}'s estimated operating cash flow "
            f"turns negative ({fmt_money(forecast_ocf)}). Working capital "
            f"requirement is projected to increase by {fmt_money(delta_wcr)}, "
            "consuming cash faster than net income generates it.",
        )
    else:
        insight = status_banner(
            "ok",
            "OK",
            f"Under these assumptions, {ticker}'s estimated operating cash flow "
            f"remains positive ({fmt_money(forecast_ocf)}).",
        )

    return fig, insight, kpis, *badges
