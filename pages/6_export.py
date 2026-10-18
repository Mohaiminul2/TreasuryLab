"""
pages/6_export.py

Page 6: Export
Download the current company's historical metrics + scenario forecast
as Excel or PDF.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from export_utils import build_excel_report, build_pdf_report
from forecasting import forecast_scenarios
from pages._data_loader import safe_available_tickers, safe_load_metrics
from pages._ui import (
    action_button,
    page_header,
    section_card,
    status_banner,
    ticker_dropdown_row,
)

dash.register_page(__name__, path="/export", name="Export")


def _report_data(ticker: str):
    """Historical + forecast frames for the selected ticker."""
    metrics_df = safe_load_metrics()
    historical_df = metrics_df[metrics_df["ticker"] == ticker].sort_values("fiscal_year")
    forecast_df = forecast_scenarios(metrics_df, ticker=ticker, horizon_months=12)
    return historical_df, forecast_df


def _download_button_col(label: str, btn_id: str, status_id: str, kind: str):
    """Button + its own status line (each callback needs a distinct output)."""
    return dbc.Col(
        [
            action_button(label, btn_id, kind=kind),
            html.Div(id=status_id, className="mt-2"),
        ],
        width="auto",
    )


def layout():
    tickers = safe_available_tickers()
    df = safe_load_metrics()

    if df.empty:
        return dbc.Container(
            [
                page_header(
                    "Export Report",
                    "Download a summary of historical working capital metrics "
                    "and the Best/Base/Worst scenario forecast for a company.",
                    meta=["No data loaded", "Run pipeline first"],
                ),
                empty_state(
                    "No financial data loaded.",
                    "Run the data pipeline first to populate metrics:\n"
                    "  python data_fetcher.py\n"
                    "  python finance_logic.py",
                    action_link="/export",
                    action_text="Refresh Page"
                ),
            ],
            fluid=True,
            className="wc-page",
        )

    return dbc.Container(
        [
            page_header(
                "Export Report",
                "Download a summary of historical working capital metrics "
                "and the Best/Base/Worst scenario forecast for a company.",
                meta=["Excel (.xlsx)", "PDF summary", "History + forecast"],
            ),
            ticker_dropdown_row("export-ticker-dropdown", tickers),
            section_card(
                "Download",
                [
                    dbc.Row(
                        [
                            _download_button_col(
                                "Download Excel", "btn-download-excel",
                                "export-status-excel", kind="primary",
                            ),
                            _download_button_col(
                                "Download PDF", "btn-download-pdf",
                                "export-status-pdf", kind="ghost",
                            ),
                        ],
                        className="mb-4 g-3",
                    ),
                    html.Div(
                        "Excel contains full historical + forecast tables; "
                        "PDF contains a compact summary (rounded values).",
                        className="wc-kpi-sub",
                    ),
                ],
                subtitle="One file per company — includes history and scenario forecast.",
            ),
            dcc.Download(id="download-excel-file"),
            dcc.Download(id="download-pdf-file"),
        ],
        fluid=True,
        className="wc-page",
    )


@callback(
    Output("download-excel-file", "data"),
    Output("export-status-excel", "children"),
    Input("btn-download-excel", "n_clicks"),
    State("export-ticker-dropdown", "value"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, ticker):
    if not ticker:
        return None, status_banner(
            "risk", "NO COMPANY SELECTED", "Choose a company from the dropdown above."
        )
    try:
        historical_df, forecast_df = _report_data(ticker)
        content = build_excel_report(ticker, historical_df, forecast_df)
    except Exception as exc:
        return None, status_banner(
            "risk", "EXPORT FAILED", f"Could not build the Excel report ({exc})."
        )
    filename = f"{ticker}_working_capital_forecast.xlsx"
    return (
        dcc.send_bytes(content, filename=filename),
        status_banner("ok", "EXCEL READY", f"{filename} — history + 12-month scenario forecast."),
    )


@callback(
    Output("download-pdf-file", "data"),
    Output("export-status-pdf", "children"),
    Input("btn-download-pdf", "n_clicks"),
    State("export-ticker-dropdown", "value"),
    prevent_initial_call=True,
)
def download_pdf(n_clicks, ticker):
    if not ticker:
        return None, status_banner(
            "risk", "NO COMPANY SELECTED", "Choose a company from the dropdown above."
        )
    try:
        historical_df, forecast_df = _report_data(ticker)
        content = build_pdf_report(ticker, historical_df, forecast_df)
    except Exception as exc:
        return None, status_banner(
            "risk", "EXPORT FAILED", f"Could not build the PDF report ({exc})."
        )
    filename = f"{ticker}_working_capital_forecast.pdf"
    return (
        dcc.send_bytes(content, filename=filename),
        status_banner("ok", "PDF READY", f"{filename} — compact summary of history + forecast."),
    )
