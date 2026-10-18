"""
pages/ui_modules/chart_utils.py

Chart-related utilities for the Working Capital dashboard.
Extracted from pages/_ui.py for better modularity.
"""

# --------------------------------------------------------------------------
# Chart colour system (ui-ux-pro-max)
#
# One hue per concept across every page, theme-aware so each mark keeps
# >=3:1 contrast against the card surface it is drawn on (WCAG 1.4.11
# graphical objects): dark tokens are tuned for surface #1E293B, light
# tokens for #FFFFFF. Charts must never hardcode hex values — pages go
# through the accessor functions below.
# --------------------------------------------------------------------------
CHART_COLOR = {
    "blue":   {"dark": "#3B82F6", "light": "#3B82F6"},  # primary / AR / DSO / CCC
    "slate":  {"dark": "#94A3B8", "light": "#64748B"},  # secondary (COGS)
    "amber":  {"dark": "#F59E0B", "light": "#B45309"},  # DPO / inventory / quick
    "green":  {"dark": "#10B981", "light": "#047857"},   # DIO / cash / OCF
    "rose":   {"dark": "#F43F5E", "light": "#BE123C"},   # worst / AP
    "teal":   {"dark": "#2DD4BF", "light": "#0F766E"},   # best
    "gold":   {"dark": "#FBBF24", "light": "#B45309"},   # base
    "purple": {"dark": "#8B5CF6", "light": "#7C3AED"},   # neutral accent
    "cyan":   {"dark": "#22D3EE", "light": "#0891B2"},   # OCF banner accent
}


def day_colors(theme) -> dict:
    """DSO / DPO / DIO / CCC / liquidity hues — shared by pages 2 and 5."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return {
        "dso": CHART_COLOR["blue"][t],
        "dpo": CHART_COLOR["amber"][t],
        "dio": CHART_COLOR["green"][t],
        "current_ratio": CHART_COLOR["blue"][t],
        "quick_ratio": CHART_COLOR["amber"][t],
        "ocf": CHART_COLOR["green"][t],
        "ccc": CHART_COLOR["blue"][t],
    }


def bs_colors(theme) -> dict:
    """Balance-sheet working-capital items (Overview line chart)."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return {
        "accounts_receivable": CHART_COLOR["blue"][t],
        "inventory": CHART_COLOR["amber"][t],
        "accounts_payable": CHART_COLOR["rose"][t],
        "cash": CHART_COLOR["green"][t],
    }


def scenario_colors(theme) -> dict:
    """Worst / Base / Best — same blue / amber / green column trio as the
    Days Breakdown chart (page 5), assigned in bar order so Worst / Base /
    Best read left-to-right exactly like DSO / DPO / DIO."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return {
        "worst": CHART_COLOR["blue"][t],
        "base": CHART_COLOR["amber"][t],
        "best": CHART_COLOR["green"][t],
    }


def series_colors(theme) -> dict:
    """Core series: primary (revenue), secondary (COGS), ccc accent."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return {
        "primary": CHART_COLOR["blue"][t],
        "secondary": CHART_COLOR["slate"][t],
        "ccc": CHART_COLOR["purple"][t],
    }


def company_colors(theme) -> list:
    """Per-company hues for page 5 — same trio as the day-metric palette."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return [
        CHART_COLOR["blue"][t],
        CHART_COLOR["amber"][t],
        CHART_COLOR["green"][t],
    ]


# Marker edge = the card surface colour, so line-chart markers read as
# outlined dots on both dark and light themes (white would vanish on
# the light surface).
MARKER_EDGE = {"dark": "#1E293B", "light": "#FFFFFF"}


def marker_edge(theme) -> str:
    """Get the marker edge color for the given theme."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return MARKER_EDGE[t]


# --------------------------------------------------------------------------
# Chart Palette — fintech indigo / cyan (ui-ux-pro-max)
# --------------------------------------------------------------------------
# Designed for the Cash Flow Forecast chart and similar forward-looking
# visualisations: muted bars carry the historical actuals, saturated bars
# mark the projection, and a soft indigo zone shades the forecast slot.
CHART_PALETTES = {
    # Dark theme
    "dark": {
        "ni_actual":    "rgba(129,140,248,0.50)",  # indigo — muted history
        "ni_forecast":  "#818CF8",                  # indigo-400 — vivid projection
        "ocf_actual":   "rgba(34,211,238,0.50)",    # cyan — muted history
        "ocf_forecast": "#22D3EE",                  # cyan-400 — vivid projection
        "zone":         "rgba(99,102,241,0.08)",   # projection-zone band
        "separator":    "rgba(148,163,184,0.35)",  # actuals→forecast divider
        "zone_label":   "#A5B4FC",                  # zone caption
        "zero_line":    "rgba(148,163,184,0.30)",
    },
    # Light theme
    "light": {
        "ni_actual":    "rgba(79,70,229,0.40)",     # indigo-600 @ 40%
        "ni_forecast":  "#4F46E5",                  # indigo-600
        "ocf_actual":   "rgba(8,145,178,0.40)",     # cyan-600 @ 40%
        "ocf_forecast": "#0891B2",                  # cyan-600
        "zone":         "rgba(79,70,229,0.06)",
        "separator":    "rgba(100,116,139,0.30)",
        "zone_label":   "#4F46E5",
        "zero_line":    "rgba(100,116,139,0.32)",
    },
}


# Theme-aware accent for icon "chips" inside chart card headers.
ICON_TONE = {
    "ocf": "ocf",          # amber  (matches existing --ocf variant)
    "ccc": "ccc",          # blue
    "neutral": "neutral",  # purple — was inlined per page
}


# --------------------------------------------------------------------------
# Plotly Defaults
# --------------------------------------------------------------------------

PLOTLY_FONTS = {
    "dark": {"color": "#F8FAFC"},
    "light": {"color": "#0F172A"},
}

# Single chart font token (must match the webfont loaded in app.py so
# chart text renders identically to the surrounding UI).
CHART_FONT = "Inter, 'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, sans-serif"

# Plotly chart defaults shared across every figure (charts looked slightly
# different on each page — these bring margins, grid colour, bar styling,
# and tick marks into one place).
CHART_MARGINS = dict(l=56, r=16, t=12, b=36)
CHART_MARGINS_WIDE = dict(l=56, r=16, t=12, b=56)  # for charts with bottom legend

# Grid colour as Plotly expects it. Pre-baked so we don't recompute
# the dark/light variant in every callback.
GRID_COLORS = {
    "dark": "rgba(148,163,184,0.10)",
    "light": "rgba(100,116,139,0.18)",
}

HLINE_COLORS = {
    "dark": "rgba(148,163,184,0.35)",
    "light": "rgba(100,116,139,0.25)",
}

HOVER_BG = {
    "dark": "rgba(30,41,59,0.96)",
    "light": "rgba(255,255,255,0.98)",
}
HOVER_FONT = {
    "dark": "#F8FAFC",
    "light": "#0F172A",
}

LEGEND_LAYOUT = dict(
    orientation="h",
    yanchor="top", y=-0.18,
    xanchor="center", x=0.5,
    bgcolor="rgba(0,0,0,0)",
    bordercolor="rgba(0,0,0,0)",
    font=dict(size=11),
    itemwidth=30,
)
LEGEND_LAYOUT_SMALL = dict(
    orientation="h",
    yanchor="top", y=-0.18,
    xanchor="center", x=0.5,
    bgcolor="rgba(0,0,0,0)",
    bordercolor="rgba(0,0,0,0)",
    font=dict(size=10),
    itemwidth=30,
)


def get_plotly_template(theme) -> str:
    """Get the appropriate Plotly template for the given theme."""
    t = "light" if str(theme).lower() == "light" else "dark"
    return "plotly_white" if t == "light" else "plotly_dark"


def style_figure(fig, theme, title: str | None = None):
    """Apply theme template + readable fonts to a Plotly figure in place.

    Paper/plot use the theme's surface color (not transparent) so the
    figure stays consistent with .wc-chart-card even if the card's CSS
    variable hasn't propagated yet — fixes dark chart on light page
    seen in Scenario Comparison where transparent relied on card bg.
    """
    t = "light" if str(theme).lower() == "light" else "dark"
    surface = "#FFFFFF" if t == "light" else "#1E293B"
    fig.update_layout(
        template=get_plotly_template(theme),
        font=dict(color=PLOTLY_FONTS[t]["color"], family=CHART_FONT),
        margin=dict(l=48, r=24, t=56, b=48),
        paper_bgcolor=surface,
        plot_bgcolor=surface,
    )
    if title is not None:
        fig.update_layout(title=title)
    return fig


def apply_chart_defaults(fig, theme, *, with_legend: bool = False, legend_small: bool = False):
    """Apply the shared grid colour, hover styling, and bar/legend defaults
    so every chart on every page looks the same.

    `with_legend=True` puts a horizontal legend under the chart; pass
    `legend_small=True` when the legend has many short labels.
    """
    t = "light" if str(theme).lower() == "light" else "dark"
    fig.update_layout(
        margin=CHART_MARGINS_WIDE if (with_legend or legend_small) else CHART_MARGINS,
        legend=(LEGEND_LAYOUT_SMALL if legend_small else LEGEND_LAYOUT) if with_legend else None,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=HOVER_BG[t],
            bordercolor=HLINE_COLORS[t],
            font=dict(size=11, color=HOVER_FONT[t], family=CHART_FONT),
        ),
    )
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLORS[t], zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig