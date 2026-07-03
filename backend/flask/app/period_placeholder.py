"""HTTP SVG placeholders for before/after panels (works in <img src> without admin token)."""

from __future__ import annotations

import urllib.parse

from app.config import Config


def esc_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(line1: str, line2: str, variant: str) -> str:
    c0, c1 = ("#1b4332", "#2d6a4f")
    if variant == "after":
        c0, c1 = "#4a3728", "#6b5344"
    elif variant == "error":
        c0, c1 = "#3d3d3d", "#5c5c5c"
    a, b = esc_xml(line1[:200]), esc_xml(line2[:200])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="768" height="512" viewBox="0 0 768 512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c0}"/>
      <stop offset="100%" style="stop-color:{c1}"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <text x="384" y="228" text-anchor="middle" fill="#e8f5e9" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="600">{a}</text>
  <text x="384" y="268" text-anchor="middle" fill="#b7e4c7" font-family="Segoe UI, Arial, sans-serif" font-size="15">{b}</text>
  <text x="384" y="312" text-anchor="middle" fill="#95d5b2" font-family="Segoe UI, Arial, sans-serif" font-size="12">Simulated / fallback — real NDVI tiles when GEE returns thumb URLs</text>
</svg>"""


def build_placeholder_url(line1: str, line2: str, variant: str) -> str:
    """Absolute URL so the React app (port 5173) loads images from Flask (5000)."""
    base = Config.PUBLIC_API_BASE_URL.rstrip("/")
    q = urllib.parse.urlencode(
        {
            "t1": line1[:180],
            "t2": line2[:180],
            "v": variant if variant in ("before", "after", "error") else "before",
        }
    )
    return f"{base}/public/period-preview.svg?{q}"