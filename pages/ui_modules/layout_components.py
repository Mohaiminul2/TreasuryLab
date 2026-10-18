"""
pages/ui_modules/layout_components.py

Layout primitives and UI components for the Working Capital dashboard.
Extracted from pages/_ui.py for better modularity.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

# --------------------------------------------------------------------------
# Icon glyphs
# --------------------------------------------------------------------------

ICON_GLYPHS = {
    "ocf": "◈",
    "ccc": "⬥",
    "neutral": "⬣",
    "sliders": "⚙",
    "insight": "◉",
}

# Insight-card icon tones — kept in lock-step with the .wc-tone-* classes
# (good / warn / info / bad) so visual weight matches the rest of the UI.
INSIGHT_TONES = {
    "warning": "warn",
    "info": "info",
    "success": "good",
    "bad": "bad",
}


# --------------------------------------------------------------------------
# Layout components
# --------------------------------------------------------------------------

def page_header(title: str, description: str, meta: list[str] | None = None):
    """Page title + description + optional meta chips (e.g. data source,
    fiscal years covered) so every page opens with the same rhythm.
    The .wc-page-header rule adds the consistent bottom divider."""
    children = [
        html.H2(title, className="wc-page-title"),
        html.P(description, className="wc-page-subtitle"),
    ]
    if meta:
        children.append(
            html.Div(
                [html.Span(m, className="wc-meta-chip") for m in meta],
                className="wc-meta-chips",
            )
        )
    return html.Div(children, className="wc-page-header mb-4")


def ticker_dropdown_row(dropdown_id: str, tickers: list[str], label: str = "Company"):
    return dbc.Row(
        dbc.Col(
            [
                html.Label(label, className="wc-field-label", htmlFor=dropdown_id),
                dcc.Dropdown(
                    id=dropdown_id,
                    options=[{"label": t, "value": t} for t in tickers],
                    value=tickers[0] if tickers else None,
                    clearable=False,
                ),
            ],
            xs=12,
            sm=6,
            md=3,
        ),
        className="mb-4",
    )


def kpi_card(
    label: str,
    value: str,
    sub: str | None = None,
    tone: str = "default",
    delta: str | None = None,
    delta_tone: str | None = None,
):
    """Small stat card. tone: default | good | bad | warn | info.
    The tone tints the value and adds a top accent bar, so a shortfall
    card reads at a glance (color + text both carry the meaning).

    `delta` renders a small trend badge beside the value (e.g. "+4.2%",
    "-3 d"); `delta_tone` (good | bad | neutral) colors it."""
    value_row = [html.Div(value, className=f"wc-kpi-value wc-tone-{tone}")]
    if delta:
        value_row.append(
            html.Span(
                delta,
                className=f"wc-kpi-delta wc-kpi-delta--{delta_tone or 'neutral'}",
            )
        )
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="wc-kpi-label"),
                html.Div(value_row, className="wc-kpi-value-row"),
                html.Div(sub or "", className="wc-kpi-sub"),
            ]
        ),
        className=f"wc-kpi-card h-100 wc-kpi--{tone}",
    )


def kpi_row(cards: list) -> dbc.Row:
    width = {1: 12, 2: 6, 3: 4, 4: 3, 5: 2, 6: 2}.get(len(cards), 3)
    if len(cards) == 5:
        # Five cards: 2 + 2 + 2 + 3 + 3 keeps every column >= 2/12 wide.
        widths = [2, 2, 2, 3, 3]
    else:
        widths = [width] * len(cards)
    cols = [
        dbc.Col(card, xs=12, sm=6, lg=w, className="mb-3")
        for card, w in zip(cards, widths)
    ]
    return dbc.Row(cols, className="mb-1")


def modern_table(header_cells, body_rows) -> html.Div:
    """The one table markup used across all pages: dense, header pills,
    horizontal scroll wrapper. `header_cells` / `body_rows` are lists of
    dash components (Th/Td) so pages keep custom cell styling."""
    return html.Div(
        dbc.Table(
            [html.Thead(html.Tr(header_cells)), html.Tbody(body_rows)],
            striped=True,
            hover=True,
            bordered=False,
            responsive=True,
            size="sm",
            className="wc-table-modern align-middle mb-0",
        ),
        className="table-responsive wc-table-wrap",
    )


# Chart-icon tokens — kept here so pages don't pick glyphs ad-hoc.


def chart_card_with_header(
    graph_id: str,
    *,
    title: str,
    subtitle: str,
    icon: str = "ocf",
    badge: str | None = None,
    height: int = 360,
    config: dict | None = None,
    body_class: str | None = None,
    above_graph: list | None = None,
    below_graph: list | None = None,
):
    """Bento-style chart card with title + subtitle + icon chip header.

    `icon` selects a glyph + tone (ocf/ccc/neutral). `badge` is the
    small pill on the right (e.g. "USD", "DAYS", "%", "×"). `body_class`
    appends to the CardBody classes (e.g. vertical centering of the
    graph inside a taller card). `above_graph` / `below_graph` render
    extra components (e.g. an insight banner div) before / after the
    chart inside the card body.
    """
    glyph = ICON_GLYPHS.get(icon, icon)
    icon_class = f"wc-chart-icon wc-chart-icon--{icon}"
    body_children = list(above_graph or []) + [
        dcc.Graph(
            id=graph_id,
            config=config or {"displayModeBar": False},
            style={"height": f"{height}px"},
        )
    ] + list(below_graph or [])
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(glyph, className=icon_class),
                                html.Div(
                                    [
                                        html.Div(title, className="wc-chart-title"),
                                        html.Div(subtitle, className="wc-chart-subtitle"),
                                    ]
                                ),
                            ],
                            className="d-flex align-items-center gap-2",
                        ),
                        html.Span(badge, className="wc-chart-badge") if badge else None,
                    ],
                    className="d-flex align-items-center justify-content-between",
                ),
                className="wc-card-header wc-card-header--bento",
            ),
            dbc.CardBody(
                body_children,
                className=f"p-2{f' {body_class}' if body_class else ''}",
            ),
        ],
        className="wc-chart-card h-100 bento-card wc-surface-card",
    )


def panel_card(title: str, subtitle: str, icon: str = "sliders", children=None,
               className: str | None = None):
    """A bento card without a chart, e.g. the Forecast sliders column.

    Uses the same header markup as `chart_card_with_header` so all
    page-3 panels match the chart cards.
    """
    glyph = ICON_GLYPHS.get(icon, icon)
    icon_class = f"wc-chart-icon wc-chart-icon--{icon}"
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.Span(glyph, className=icon_class),
                        html.Div(
                            [
                                html.Div(title, className="wc-chart-title"),
                                html.Div(subtitle, className="wc-chart-subtitle"),
                            ]
                        ),
                    ],
                    className="d-flex align-items-center gap-2",
                ),
                className="wc-card-header wc-card-header--bento",
            ),
            dbc.CardBody(children, className="p-3"),
        ],
        className=f"h-100 bento-card wc-surface-card{f' {className}' if className else ''}",
    )


def action_button(text: str, btn_id: str, kind: str = "primary"):
    """Themed button used for page actions (downloads, etc.) so no page
    falls back to stock Bootstrap color classes. kind: primary | ghost."""
    return dbc.Button(
        text,
        id=btn_id,
        className=f"wc-btn wc-btn--{kind}",
    )


def section_card(title: str, children, subtitle: str | None = None):
    header = [html.H5(title, className="wc-section-title mb-0")]
    if subtitle:
        header.append(html.Div(subtitle, className="wc-section-subtitle"))
    return dbc.Card(
        [
            dbc.CardHeader(header, className="wc-card-header"),
            dbc.CardBody(children),
        ],
        className="wc-section-card mb-3",
    )


def insight_card(title: str, body: str, tone: str = "info"):
    """A borderless insight card (consistent header markup, tone-coloured dot).
    Used by page 5 today; available everywhere via `_ui`."""
    bs_class = INSIGHT_TONES.get(tone, tone)
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Span(
                            ICON_GLYPHS["insight"],
                            className=f"me-2 wc-tone-{bs_class}",
                            style={"fontSize": "1rem", "lineHeight": 1},
                        ),
                        html.Strong(title),
                    ],
                    className="d-flex align-items-center mb-2",
                ),
                html.P(body, className="mb-0 wc-kpi-sub"),
            ],
            className="p-3",
        ),
        className="wc-insight-card",
    )


def empty_state(message: str = "No data available.", hint: str | None = None, action_link: str | None = None, action_text: str | None = None):
    """Enhanced empty/placeholder state with optional action link."""
    body = [
        html.Span("◌", className="wc-empty-icon", **{"aria-hidden": "true"}),
        html.Div(message, className="wc-empty-message"),
    ]
    if hint:
        body.append(html.Div(hint, className="wc-empty-hint"))

    # Add optional action button/link
    if action_link and action_text:
        body.append(
            html.Div(
                dbc.Button(
                    action_text,
                    href=action_link,
                    className="wc-btn wc-btn--primary btn-sm",
                ),
                className="wc-empty-action"
            )
        )

    return html.Div(body, className="wc-empty-state text-center")


def loading_wrap(children):
    return dcc.Loading(children=children, type="circle")


# Status banners — one markup for SHORTFALL RISK / OK everywhere.
STATUS_ICON = {"risk": "◆", "ok": "◇"}


def status_banner(kind: str, headline: str, body: str):
    """Unified status banner. kind: risk | ok. `headline` is the strong
    prefix (e.g. "SHORTFALL RISK"), `body` the explanation sentence.
    Color + icon + explicit text label carry the meaning (never emoji-only)."""
    return html.Div(
        [
            html.Span(STATUS_ICON.get(kind, "◇"), className=f"wc-banner-icon wc-banner-icon--{kind} me-2"),
            html.Strong(f"{headline} — ", className=f"wc-banner-head wc-banner-head--{kind}"),
            html.Span(body),
        ],
        className=f"wc-banner wc-banner--{kind}",
        role="status",
    )


def shortfall_alert(ticker: str, shortfall_scenarios: list[str]):
    """Consistent SHORTFALL RISK / OK banner for the fixed scenarios
    (page 4) and any other preset-driven view."""
    if shortfall_scenarios:
        names = ", ".join(s.capitalize() for s in shortfall_scenarios)
        return status_banner(
            "risk",
            "SHORTFALL RISK",
            f"{ticker} shows projected negative operating cash flow under: {names}.",
        )
    return status_banner(
        "ok",
        "OK",
        f"No cash shortfall flagged for {ticker} under any scenario.",
    )
