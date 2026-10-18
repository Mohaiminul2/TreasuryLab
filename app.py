"""
app.py

Main entry point for the Working Capital & Cash Flow Forecasting dashboard.

Run with:
    python app.py

Prerequisites (run once, in order):
    1. python test_tickers.py         # confirm your tickers return data
    2. python data_fetcher.py         # pull + cache yfinance data
    3. python finance_logic.py        # compute working capital metrics
    4. python app.py                  # launch dashboard
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html

from pages._ui import DARK, LIGHT, normalize_theme

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
)
app.title = "Treasury Lab — Working Capital & Cash Flow Forecasting"

# Sidebar information architecture: group the six pages into
# workflow sections so the nav reads as Analyze -> Compare -> Report.
NAV_SECTIONS = [
    ("Analyze", ["/", "/working-capital", "/forecast"]),
    ("Compare", ["/scenarios", "/compare"]),
    ("Report", ["/export"]),
]


def _nav_link(page, num: int):
    return dbc.NavLink(
        [
            html.Span(f"{num:02d}", className="wc-link-num"),
            html.Span(page["name"], className="ms-1"),
        ],
        href=page["path"],
        active="exact",
        className="wc-link",
    )


def _brand_row():
    # Shield logo from assets/branding/; the dark (amber) and light (blue)
    # variants are both rendered and swapped via CSS so the logo follows
    # the theme toggle without an extra callback. Covers the mobile drawer
    # too (wc-theme-* scopes), which portals outside #wc-app.
    return html.Div(
        [
            html.Img(
                src="/assets/branding/treasurylab-shield.svg",
                alt="TreasuryLab logo",
                className="wc-logo wc-logo--dark",
            ),
            html.Img(
                src="/assets/branding/treasurylab-shield-light.svg",
                alt="TreasuryLab logo",
                className="wc-logo wc-logo--light",
            ),
            html.Div(
                [
                    html.Div("TreasuryLab", className="wc-brand"),
                    html.Div("FP&A · Treasury", className="wc-brand-sub"),
                ]
            ),
        ],
        className="wc-brand-row",
    )


SECTION_META = {
    "Analyze": {"icon": "◈", "accent": "#F59E0B"},
    "Compare": {"icon": "⬥", "accent": "#3498DB"},
    "Report": {"icon": "⬣", "accent": "#8B5CF6"},
}

def _nav_sections():
    """Fresh nav-section components on every call (desktop sidebar and
    mobile drawer each need their own component instances)."""
    by_path = {page["path"]: page for page in dash.page_registry.values()}
    sections = []
    num = 0
    for label, paths in NAV_SECTIONS:
        links = []
        for path in paths:
            page = by_path.get(path)
            if page is None:
                continue
            num += 1
            links.append(_nav_link(page, num))
        meta = SECTION_META.get(label, {"icon": "•", "accent": "var(--wc-muted)"})
        sections.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(meta["icon"], className="wc-section-icon", style={"color": meta["accent"]}),
                            html.Span(label),
                        ],
                        className="wc-nav-section",
                    ),
                    dbc.Nav(links, vertical=True, pills=True, className="wc-nav"),
                ],
                className="wc-nav-group",
                **{"data-section": label.lower()},
            )
        )
    known = {p for _, paths in NAV_SECTIONS for p in paths}
    orphans = [p for p in dash.page_registry.values() if p["path"] not in known]
    if orphans:
        orphan_links = []
        for p in orphans:
            num += 1
            orphan_links.append(_nav_link(p, num))
        sections.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("•", className="wc-section-icon", style={"color": "var(--wc-muted)"}),
                            html.Span("More"),
                        ],
                        className="wc-nav-section",
                    ),
                    dbc.Nav(
                        orphan_links,
                        vertical=True,
                        pills=True,
                        className="wc-nav",
                    ),
                ],
                className="wc-nav-group",
                **{"data-section": "more"},
            )
        )
    return sections


def _sidebar_footer(theme_btn_id: str):
    return html.Div(
        [
            dbc.Button(
                "Theme: Dark",
                id=theme_btn_id,
                className="w-100 wc-btn wc-btn--ghost",
                size="sm",
            ),
            html.Div("Cash-cycle analytics", className="wc-side-note"),
        ],
        className="wc-sidebar-footer",
    )


def _build_sidebar():
    return html.Div(
        [
            _brand_row(),
            html.Div(_nav_sections(), className="wc-nav-wrap"),
            _sidebar_footer("theme-toggle"),
        ],
        className="wc-sidebar-inner",
    )


def _build_mobile_drawer():
    """Offcanvas drawer for <lg screens: brand + same pages + theme toggle."""
    return dbc.Offcanvas(
        [
            _brand_row(),
            html.Div(_nav_sections(), className="wc-nav-wrap"),
            _sidebar_footer("theme-toggle-m"),
        ],
        id="mobile-nav",
        title="",
        placement="start",
        backdrop=True,
        scrollable=True,
        is_open=False,
        className="wc-offcanvas",
    )


sidebar = _build_sidebar()
mobile_drawer = _build_mobile_drawer()

app.layout = html.Div(
    [
        # Brand favicon (browser tab) — 32px shield from the brand kit
        html.Link(
            rel="icon",
            type="image/png",
            href="/assets/branding/treasurylab-shield-32px.png",
        ),
        # Persisted UI state (local storage survives reloads + navigation)
        dcc.Store(id="store-theme", storage_type="local", data=DARK),
        dcc.Store(id="store-sidebar", storage_type="local", data={"collapsed": False}),
        dcc.Store(id="store-selected-ticker", data="PG"),  # reserved for future cross-page ticker sync
        dcc.Location(id="url", refresh=False),

        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            sidebar,
                            xs=12,
                            lg=2,
                            id="sidebar-col",
                            # Hidden below lg: mobile/tablet use the drawer.
                            # Grid stays 2 cols; custom.css widens the desktop
                            # sidebar by +32px (calc override on #sidebar-col)
                            # so nav labels get breathing room. The content
                            # col flexes to absorb the difference.
                            className="wc-sidebar d-none d-lg-block",
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        # Mobile/tablet only: opens the drawer.
                                        dbc.Button(
                                            "☰",
                                            id="mobile-nav-toggle",
                                            color="primary",
                                            outline=True,
                                            size="sm",
                                            style={"padding": "1px 5px", "fontSize": "0.82rem"},
                                            title="Open navigation menu",
                                            className="d-lg-none",
                                        ),
                                        # Desktop only: collapses the sidebar.
                                        dbc.Button(
                                            "«",
                                            id="sidebar-toggle",
                                            className="wc-btn wc-btn--bare d-none d-lg-inline-block",
                                            size="sm",
                                            style={"padding": "1px 5px", "fontSize": "0.82rem"},
                                            title="Hide / show the sidebar",
                                        ),
                                    ],
                                    className="wc-topbar",
                                ),
                                # Page container wrapper — explicit theme
                                # backdrop so the frame between page unmount
                                # and new-page mount paints the page bg
                                # (never the bare body or a flash of white).
                                html.Div(
                                    dash.page_container,
                                    id="wc-page-content",
                                    className="wc-page-content",
                                ),
                            ],
                            xs=12,
                            lg=10,
                            id="content-col",
                            className="p-3 p-lg-4",
                        ),
                    ]
                ),
            ],
            fluid=True,
        ),
        mobile_drawer,
    ],
    id="wc-app",
    **{"data-theme": DARK},
)


@app.callback(
    Output("store-sidebar", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("store-sidebar", "data"),
    prevent_initial_call=True,
)
def _toggle_sidebar(_n_clicks, state):
    # One-way toggle: button -> store. Store -> layout lives in
    # _apply_sidebar below, so there is no dependency cycle.
    collapsed = not bool((state or {}).get("collapsed", False))
    return {"collapsed": collapsed}


@app.callback(
    Output("sidebar-col", "className"),
    Output("content-col", "lg"),
    Output("sidebar-toggle", "children"),
    Input("store-sidebar", "data"),
    Input("url", "pathname"),
)
def _apply_sidebar(state, _pathname):
    """Hide/show the sidebar on toggle + nav, expand content when hidden.

    Uses className (d-none / d-lg-block) instead of inline style because
    d-lg-block is !important and would override an inline display:none at
    desktop widths, leaving the sidebar taking space while content tries to
    take 12 — wrapped content looks blank. Compact: sidebar 2 cols (16.6%),
    content 10 cols (83.3%) when visible.
    """
    collapsed = bool((state or {}).get("collapsed", False))
    if collapsed:
        return "wc-sidebar d-none", 12, "» Show menu"
    return "wc-sidebar d-none d-lg-block", 10, "« Hide menu"


@app.callback(
    Output("mobile-nav", "is_open"),
    Input("mobile-nav-toggle", "n_clicks"),
    Input("url", "pathname"),
    State("mobile-nav", "is_open"),
    prevent_initial_call=True,
)
def _toggle_mobile_nav(_n_clicks, _pathname, is_open):
    """Hamburger opens/closes the drawer; any navigation closes it."""
    trigger = dash.callback_context.triggered_id
    if trigger == "mobile-nav-toggle":
        return not is_open
    return False


@app.callback(
    Output("store-theme", "data"),
    Input("theme-toggle", "n_clicks"),
    Input("theme-toggle-m", "n_clicks"),
    State("store-theme", "data"),
    prevent_initial_call=True,
)
def _save_theme(_n1, _n2, current):
    # One-way toggle: buttons -> store. The store -> UI direction lives in
    # _apply_theme below, so there is no dependency cycle.
    return LIGHT if normalize_theme(current) == DARK else DARK


@app.callback(
    Output("wc-app", "data-theme"),
    Output("theme-toggle", "children"),
    Output("theme-toggle-m", "children"),
    Output("mobile-nav", "className"),
    Input("store-theme", "data"),
    Input("url", "pathname"),
)
def _apply_theme(theme, _pathname):
    """Apply stored theme to the shell on nav + reload; label the buttons.

    The mobile drawer gets its own theme class because it can portal
    outside #wc-app, where the data-theme scoped CSS cannot reach it.
    """
    t = normalize_theme(theme)
    is_dark = t == DARK
    label = "Theme: Dark" if is_dark else "Theme: Light"
    drawer_class = "wc-offcanvas wc-theme-dark" if is_dark else "wc-offcanvas wc-theme-light"
    return t, label, label, drawer_class


if __name__ == "__main__":
    import os
    # debug=True enables hot-reloading but also injects the floating
    # dev-tools toolbar (dash-debug-menu) and the Werkzeug debugger.
    # Default to debug=False for security (no debugger exposed on 0.0.0.0).
    # Set FLASK_ENV=development to enable debug mode for local development.
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host='0.0.0.0', port=8050, debug=debug_mode, dev_tools_ui=False)
