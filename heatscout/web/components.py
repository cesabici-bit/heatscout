"""HeatScout UI — Reusable HTML components.

Provides helper functions that return raw HTML for hero sections,
KPI cards, temperature cards, impact banners, and footers.
"""

from __future__ import annotations


def hero_section(
    title: str = "HeatScout",
    subtitle: str = (
        "From wasted heat to savings &mdash; "
        "analyze your plant's thermal streams and discover the best recovery technologies."
    ),
    badge_text: str = "Open Source &middot; Screening Tool",
) -> str:
    """Return hero section HTML."""
    return f"""
<div class="hero-container">
    <p class="hero-title">{title}</p>
    <p class="hero-subtitle">{subtitle}</p>
    <span class="hero-badge">{badge_text}</span>
</div>
"""


def section_header(icon: str, title: str) -> str:
    """Return section header HTML."""
    return f'<div class="section-header"><h2>{icon} {title}</h2></div>'


def impact_banner(html_body: str) -> str:
    """Return impact banner HTML."""
    return f'<div class="impact-banner"><p>{html_body}</p></div>'


def temp_card(label: str, value: str, detail: str, css_class: str) -> str:
    """Return temperature class card HTML."""
    return f"""
<div class="temp-card {css_class}">
    <div class="temp-label">{label}</div>
    <div class="temp-value">{value}</div>
    <div class="temp-detail">{detail}</div>
</div>
"""


def footer(
    project: str = "HeatScout",
    tagline: str = "Industrial waste heat recovery analysis",
    github_url: str = "https://github.com/cesabici-bit/heatscout",
) -> str:
    """Return footer HTML."""
    return f"""
<div class="footer">
    <strong>{project}</strong> &middot; {tagline} &middot; Open Source (MIT)<br>
    <a href="{github_url}">GitHub</a> &middot;
    <a href="{github_url}/issues">Report an issue</a>
</div>
"""
