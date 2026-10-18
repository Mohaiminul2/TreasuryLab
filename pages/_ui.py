"""
pages/_ui.py

Shared design-system helpers for the Working Capital dashboard.
All pages should build their layout through these helpers so the six
pages feel like one unified FP&A tool.

This is now a facade module that imports from the specialized UI modules
for better maintainability.
"""

# Import from specialized modules
from .ui_modules.theme_utils import (
    DARK,
    LIGHT,
    normalize_theme,
    plotly_template,
    theme_colors,
    get_theme_color,
)

from .ui_modules.formatting_utils import (
    fmt_money,
    fmt_money_full,
    fmt_days,
    fmt_pct,
    fmt_pp,
    fmt_ratio,
    fmt_year,
    year_labels,
)

from .ui_modules.chart_utils import (
    CHART_COLOR,
    day_colors,
    bs_colors,
    scenario_colors,
    series_colors,
    company_colors,
    marker_edge,
    CHART_PALETTES,
    ICON_TONE,
    PLOTLY_FONTS,
    CHART_FONT,
    CHART_MARGINS,
    CHART_MARGINS_WIDE,
    GRID_COLORS,
    HLINE_COLORS,
    HOVER_BG,
    HOVER_FONT,
    LEGEND_LAYOUT,
    LEGEND_LAYOUT_SMALL,
    get_plotly_template,
    style_figure,
    apply_chart_defaults,
)

from .ui_modules.layout_components import (
    ICON_GLYPHS,
    INSIGHT_TONES,
    page_header,
    ticker_dropdown_row,
    kpi_card,
    kpi_row,
    modern_table,
    chart_card_with_header,
    panel_card,
    action_button,
    section_card,
    insight_card,
    empty_state,
    loading_wrap,
    status_banner,
    shortfall_alert,
)