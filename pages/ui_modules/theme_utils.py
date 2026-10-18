"""
pages/ui_modules/theme_utils.py

Theme-related utilities for the Working Capital dashboard.
Extracted from pages/_ui.py for better modularity.
"""

# --------------------------------------------------------------------------
# Theme tokens
# --------------------------------------------------------------------------

DARK = "dark"
LIGHT = "light"

THEMES = {
    DARK: {
        "plotly_template": "plotly_dark",
        "bg": "#0F172A",
        "surface": "#1E293B",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "border": "#334155",
        "primary": "#F59E0B",
        "success": "#2ECC71",
        "danger": "#EF4444",
        "info": "#3498DB",
    },
    LIGHT: {
        "plotly_template": "plotly_white",
        "bg": "#F1F5F9",
        "surface": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#64748B",
        "border": "#CBD5E1",
        "primary": "#1E40AF",
        "success": "#15803D",
        "danger": "#B91C1C",
        "info": "#0369A1",
    },
}


def normalize_theme(theme) -> str:
    """Coerce any stored theme value to 'dark' or 'light' (dark default)."""
    return LIGHT if str(theme).lower() == LIGHT else DARK


def plotly_template(theme) -> str:
    """Get the appropriate Plotly template for the given theme."""
    return THEMES[normalize_theme(theme)]["plotly_template"]


def theme_colors(theme) -> dict:
    """Get all color tokens for the given theme."""
    return THEMES[normalize_theme(theme)]


def get_theme_color(theme, color_name: str) -> str:
    """Get a specific color token from the theme."""
    t = normalize_theme(theme)
    return THEMES[t].get(color_name, "#000000")  # fallback to black