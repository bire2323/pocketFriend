"""The PocketFriend design system.

One stylesheet, one set of tokens, injected once per run. The goal is a calm
paper-and-ink workspace rather than a dashboard: content sits on open surfaces,
dividers do the work that boxes usually do, and the accent colour is used for
the one thing that matters on a screen.

Everything here is offline: system font stack, inline SVG icons, no CDN, no
webfont, no network request of any kind.
"""

from __future__ import annotations

import streamlit as st

BRAND = "PocketFriend"
TAGLINE = "Your private study companion"

# ---------------------------------------------------------------------------
# Icons: one line-icon set (24x24 grid, 1.7 stroke, round caps).
# The same paths are used inline (components.icon) and as CSS masks, so a nav
# item and a row header share exactly the same drawing.
# ---------------------------------------------------------------------------

_ICON_PATHS = {
    "home": '<path d="M3.2 10.6 12 3.2l8.8 7.4"/><path d="M5.6 9.6V20h12.8V9.6"/><path d="M9.6 20v-5.6h4.8V20"/>',
    "ask": '<circle cx="11" cy="11" r="6.6"/><path d="m15.9 15.9 4.6 4.6"/>',
    "plan": '<rect x="3.4" y="5.2" width="17.2" height="15.4" rx="2.4"/><path d="M8 3.4v3.4M16 3.4v3.4M3.4 10.2h17.2"/><path d="m8.8 15.2 2.1 2.1 4.3-4.3"/>',
    "quiz": '<circle cx="12" cy="12" r="8.6"/><path d="m8.4 12.2 2.5 2.5 4.7-5"/>',
    "docs": '<path d="M14 3.4H7.4A1.6 1.6 0 0 0 5.8 5v14a1.6 1.6 0 0 0 1.6 1.6h9.2a1.6 1.6 0 0 0 1.6-1.6V7.4z"/><path d="M14 3.4v4h4.2"/><path d="M9 12h6M9 15.4h4.2"/>',
    "settings": '<path d="M4 7.2h9.4M17.6 7.2H20M4 12h4.2M12.4 12H20M4 16.8h7.2M15.4 16.8H20"/><circle cx="15.5" cy="7.2" r="2.1"/><circle cx="10.3" cy="12" r="2.1"/><circle cx="13.3" cy="16.8" r="2.1"/>',
    "file": '<path d="M14 3.4H7.4A1.6 1.6 0 0 0 5.8 5v14a1.6 1.6 0 0 0 1.6 1.6h9.2a1.6 1.6 0 0 0 1.6-1.6V7.4z"/><path d="M14 3.4v4h4.2"/>',
    "list": '<path d="M8.5 6.5h11M8.5 12h11M8.5 17.5h11"/><path d="M4.6 6.5h.01M4.6 12h.01M4.6 17.5h.01"/>',
    "plus": '<path d="M12 5.2v13.6M5.2 12h13.6"/>',
    "check": '<path d="m5 12.6 4.6 4.6L19 6.8"/>',
    "close": '<path d="m6.4 6.4 11.2 11.2M17.6 6.4 6.4 17.6"/>',
    "arrow": '<path d="M4.6 12h14.2M13.2 6.4 18.8 12l-5.6 5.6"/>',
    "chevron": '<path d="m9.6 5.8 6.2 6.2-6.2 6.2"/>',
    "trash": '<path d="M4.6 7h14.8M9.6 7V4.6h4.8V7M6.6 7l.9 12.4h9l.9-12.4"/>',
    "clock": '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.4V12l3.2 2"/>',
    "book": '<path d="M4 5.6A1.6 1.6 0 0 1 5.6 4H11v15.4H5.6A1.6 1.6 0 0 1 4 18.4z"/><path d="M20 5.6A1.6 1.6 0 0 0 18.4 4H13v15.4h5.4a1.6 1.6 0 0 0 1.6-1.6z"/>',
    "upload": '<path d="M12 16.2V4.4M7.8 8.6 12 4.4l4.2 4.2"/><path d="M4.6 15.6V19a1.6 1.6 0 0 0 1.6 1.6h11.6A1.6 1.6 0 0 0 19.4 19v-3.4"/>',
    "quote": '<path d="M9.6 7.4H6.8a2 2 0 0 0-2 2v2.8a2 2 0 0 0 2 2h1v1.2a2 2 0 0 1-2 2"/><path d="M19.2 7.4h-2.8a2 2 0 0 0-2 2v2.8a2 2 0 0 0 2 2h1v1.2a2 2 0 0 1-2 2"/>',
    "spark": '<path d="m11 3.6 1.7 4.7 4.7 1.7-4.7 1.7L11 16.4 9.3 11.7 4.6 10l4.7-1.7z"/><path d="m18 15.4.9 2.4 2.4.9-2.4.9-.9 2.4-.9-2.4-2.4-.9 2.4-.9z"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.2"/>',
    "alert": '<path d="M12 4.2 21 19.8H3z"/><path d="M12 9.8v4.4M12 17.2h.01"/>',
    "bolt": '<path d="M13.2 3.2 5.4 13.4h5.4l-1 7.4 7.8-10.2h-5.4z"/>',
    "layers": '<rect x="3.6" y="4.2" width="16.8" height="15.6" rx="2"/><path d="M8 8.4h8M8 12h8M8 15.6h5"/>',
    "pin": '<path d="M12 3.6 19.6 9 12 20.4 4.4 9z"/><circle cx="12" cy="9.6" r="2.1"/>',
    "lock": '<rect x="5" y="10.4" width="14" height="9.6" rx="2"/><path d="M8.4 10.4V8a3.6 3.6 0 0 1 7.2 0v2.4"/>',
    "send": '<path d="M20.2 4.4 3.8 10.6l6.4 2.6 2.6 6.4z"/><path d="m10.2 13.2 4.4-4.4"/>',
    "play": '<path d="M8.4 5.4 18.6 12 8.4 18.6z"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 4.6V10h-5.2"/>',
    "download": '<path d="M12 4.4v11.4M7.8 11.6 12 15.8l4.2-4.2"/><path d="M4.6 16.2V19a1.6 1.6 0 0 0 1.6 1.6h11.6A1.6 1.6 0 0 0 19.4 19v-2.8"/>',
    "science": '<path d="M9.6 3.6h4.8M10.4 3.6v5.2L5.6 17a2.4 2.4 0 0 0 2.1 3.6h8.6a2.4 2.4 0 0 0 2.1-3.6l-4.8-8.2V3.6"/><path d="M8 14.4h8"/>',
    "folder": '<path d="M3.8 7.4a1.6 1.6 0 0 1 1.6-1.6h3.4l1.8 2.2h7.2a1.6 1.6 0 0 1 1.6 1.6v8.2a1.6 1.6 0 0 1-1.6 1.6H5.4a1.6 1.6 0 0 1-1.6-1.6z"/>',
    "thumbsup": '<path d="M7.4 20V10.4l4.2-6a1.8 1.8 0 0 1 2.6 2.4l-1 3.6h5.2a1.8 1.8 0 0 1 1.8 2.2l-1.8 6a1.8 1.8 0 0 1-1.8 1.4z"/><path d="M7.4 10.4H4.6V20h2.8z"/>',
    "thumbsdown": '<path d="M16.6 4v9.6l-4.2 6a1.8 1.8 0 0 1-2.6-2.4l1-3.6H5.6a1.8 1.8 0 0 1-1.8-2.2l1.8-6A1.8 1.8 0 0 1 7.4 4z"/><path d="M16.6 13.6h2.8V4h-2.8z"/>',
    "menu": '<path d="M3.5 6.5h17M3.5 12h17M3.5 17.5h17"/>',
}


def _mask_url(name: str) -> str:
    """The icon as a CSS mask, so a Streamlit button can carry an icon."""
    path = _ICON_PATHS[name]
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='black' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>"
        f"{path}</svg>"
    )
    encoded = svg.replace("<", "%3C").replace(">", "%3E").replace('"', "'")
    return f'url("data:image/svg+xml,{encoded}")'


def model_label(model: str) -> str:
    """'gemma3:1b' -> 'Gemma 3 1B' for humans."""
    name = (model or "").strip()
    if not name:
        return "Local model"
    name = name.split(":")[0]
    tag = (model.split(":")[1] if ":" in model else "").upper()
    pretty = name.replace("gemma", "Gemma").replace("llama", "Llama").replace("qwen", "Qwen")
    pretty = pretty.replace("-", " ").replace("_", " ").title()
    return f"{pretty} {tag}".strip()


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def _tokens() -> str:
    icons = "\n".join(f"  --i-{name}: {_mask_url(name)};" for name in sorted(_ICON_PATHS))
    return f"""
:root {{
  /* 2.1 Color Tokens - Light mode (quiet paper workspace) */
  --bg: #F7F8FB;          /* Canvas: page background, warm off-white */
  --surface: #FFFFFF;     /* Cards, inputs, sidebar */
  --surface-2: #F4F6FA;   /* Nested panels, hovered rows */
  --surface-3: #EBEEF5;   /* Pills, tags, inactive chips */
  --border: #E5E8F0;      /* Hairline dividers */
  --border-2: #D0D6E2;    /* Input outlines, emphasis */
  --text: #0F1528;        /* Primary ink, near-black with blue undertone */
  --text-2: #333A4F;      /* Body copy */
  --text-3: #5A6379;      /* Meta, captions */
  --text-4: #8A93A8;      /* Placeholders, disabled */

  /* Accent (the only loud color: gold, not blue) */
  --accent: #A97C0B;
  --accent-light: #D9A82B;
  --accent-soft: #FBF3E2;
  --accent-line: #E9D6A6;
  --accent-dark: #8A6108;

  /* Semantic feedback */
  --ok: #059669;
  --ok-soft: #ECFDF5;
  --ok-line: #A7F3D0;
  --sage: #059669;
  --sage-soft: #ECFDF3;
  --sage-line: #D1FADF;
  --warn: #B45309;
  --warn-soft: #FFFBEB;
  --warn-line: #FDE68A;
  --danger: #DC2626;
  --danger-soft: #FEF2F2;
  --danger-line: #FECACA;

  /* 2.2 Typography Scale & Stack */
  --font: "Inter", "Inter var", ui-sans-serif, system-ui, -apple-system,
    "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Mono", "SFMono-Regular", "Segoe UI Mono", monospace;
  --fs-app: 13px;
  --fs-title: 30px;
  --fs-section: 18px;
  --fs-body: 15px;
  --fs-meta: 13px;

  /* 2.3 Spacing Scale (8pt-based: 6, 10, 16, 24, 32, 40, 56, 80) */
  --s1: 6px;
  --s2: 10px;
  --s3: 16px;
  --s4: 24px;
  --s5: 32px;
  --s6: 40px;
  --s7: 56px;
  --s8: 80px;

  /* 2.4 Radius Scale */
  --r-xs: 6px;    /* small chips, tag pills, letter badges */
  --r-sm: 10px;   /* inputs, nav items, small panels */
  --r-md: 14px;   /* buttons, cards, panels */
  --r-lg: 20px;   /* dialogs, modals, composer, bubbles */
  --r-xl: 26px;   /* hero containers */
  --r-full: 9999px; /* full pill for tags, status dots */

  /* 2.5 Elevation (Warm-tinted based on #0F1528) */
  --shadow-xs: 0 1px 2px rgba(15, 21, 40, 0.04);
  --shadow-1: 0 2px 5px -1px rgba(15, 21, 40, 0.06), 0 1px 3px -1px rgba(15, 21, 40, 0.04);
  --shadow-2: 0 10px 24px -4px rgba(15, 21, 40, 0.08), 0 4px 10px -4px rgba(15, 21, 40, 0.04);
  --shadow-3: 0 20px 35px -8px rgba(15, 21, 40, 0.14), 0 8px 16px -6px rgba(15, 21, 40, 0.08);
  --focus: 0 0 0 4px rgba(169, 124, 11, 0.22);

  /* 2.6 Motion */
  --ease-default: cubic-bezier(.22, .61, .36, 1);
  --ease-spring: cubic-bezier(.34, 1.56, .64, 1);
  --dur-hover: 140ms;
  --dur-state: 160ms;
  --dur-enter: 220ms;

  /* 2.7 Phone navigation bar: one number for the bar, the page's bottom padding
     and anything else that has to sit clear of it. */
  --mobnav-h: 58px;

{icons}
}}

/* Dark Mode: mirrored tokens respecting prefers-color-scheme */
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0B0F1A;          /* Canvas: deep navy-black */
    --surface: #121724;     /* Layer 1: cards, inputs, sidebar */
    --surface-2: #171D2C;   /* Layer 2: nested panels, hovered rows */
    --surface-3: #1F2739;   /* Layer 3: pills, tags, inactive chips */
    --border: #232B3E;      /* Hairline dividers */
    --border-2: #344059;    /* Input outlines, emphasis */
    --text: #F1F4FA;        /* Primary ink: crisp off-white */
    --text-2: #C5CEE0;      /* Body copy */
    --text-3: #8F9BB3;      /* Meta, captions */
    --text-4: #5E6C84;      /* Placeholders, disabled */

    --accent: #E3B341;      /* Brightened gold for dark mode legibility */
    --accent-light: #F2D283;
    --accent-soft: #241D0C;
    --accent-line: #4C3D16;
    --accent-dark: #C2931F;

    --ok: #10B981;
    --ok-soft: #063726;
    --ok-line: #0D5C40;
    --sage: #10B981;
    --sage-soft: #063726;
    --sage-line: #0D5C40;
    --warn: #F59E0B;
    --warn-soft: #3D2406;
    --warn-line: #613C0A;
    --danger: #EF4444;
    --danger-soft: #3E1515;
    --danger-line: #652323;

    --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.2);
    --shadow-1: 0 2px 5px -1px rgba(0, 0, 0, 0.3), 0 1px 3px -1px rgba(0, 0, 0, 0.2);
    --shadow-2: 0 10px 24px -4px rgba(0, 0, 0, 0.4), 0 4px 10px -4px rgba(0, 0, 0, 0.25);
    --shadow-3: 0 20px 35px -8px rgba(0, 0, 0, 0.55), 0 8px 16px -6px rgba(0, 0, 0, 0.35);
    --focus: 0 0 0 4px rgba(227, 179, 65, 0.28);
  }}
}}
"""


# ---------------------------------------------------------------------------
# 1. Base: typography, rhythm, native Streamlit surfaces
# ---------------------------------------------------------------------------


def _base() -> str:
    return """
html, body, .stApp, [data-testid="stAppViewContainer"] {
  font-family: var(--font);
  color: var(--text);
  font-size: var(--fs-body);
  font-feature-settings: "cv05" 1, "ss01" 1, "tnum" 1;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: var(--bg); }
[data-testid="stMain"] { background: var(--surface); }
[data-testid="stMainBlockContainer"],
.block-container {
  padding: var(--s5) var(--s6) var(--s8) !important;
  max-width: 1480px;
}
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stVerticalBlock"] { gap: var(--s4); }
[data-testid="stHorizontalBlock"] { gap: var(--s4); }
[data-testid="stVerticalBlockBorderWrapper"] { gap: var(--s4); }

/* markdown defaults inside the workspace */
.stMarkdown p {
  font-size: var(--fs-body);
  line-height: 1.65;
  font-weight: 460;
  color: var(--text);
  margin: 0 0 var(--s3);
  text-align: left;
}
.stMarkdown p:last-child { margin-bottom: 0; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
  font-family: var(--font);
  color: var(--text);
  line-height: 1.22;
  margin: 0 0 var(--s3);
  text-align: left;
}
.stMarkdown h1 { font-size: var(--fs-title); font-weight: 680; letter-spacing: -0.026em; }
.stMarkdown h2 { font-size: 20px; font-weight: 640; letter-spacing: -0.014em; }
.stMarkdown h3 { font-size: var(--fs-section); font-weight: 640; letter-spacing: -0.014em; }
.stMarkdown h4 { font-size: 15px; font-weight: 600; color: var(--text-2); }
.stMarkdown ul, .stMarkdown ol { margin: 0 0 var(--s3); padding-left: 1.15rem; text-align: left; }
.stMarkdown li { font-size: var(--fs-body); line-height: 1.65; font-weight: 460; margin-bottom: var(--s1); }
.stMarkdown li::marker { color: var(--text-4); }
.stMarkdown strong { font-weight: 620; color: var(--text); }
.stMarkdown a { color: var(--accent); text-decoration: none; border-bottom: 1px solid var(--accent-line); }
.stMarkdown hr { border: 0; border-top: 1px solid var(--border); margin: var(--s5) 0; }
.stMarkdown code {
  font-family: var(--mono);
  font-size: 12px;
  font-feature-settings: "tnum" 1;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: var(--r-xs);
  padding: 1px 5px;
}
.stMarkdown pre {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--s4);
  font-size: 12.5px;
  overflow-x: auto;
}
.stMarkdown blockquote {
  border-left: 2px solid var(--accent-line);
  margin: 0 0 var(--s3);
  padding-left: var(--s4);
  color: var(--text-2);
  text-align: left;
}
.stMarkdown table { font-size: var(--fs-body); border-color: var(--border); width: 100%; font-feature-settings: "tnum" 1; }
.stMarkdown table th { color: var(--text-2); font-weight: 600; background: var(--surface-2); }

/* prevent long words / filenames / URLs from overflowing */
.stMarkdown, .stMarkdown * { word-break: break-word; overflow-wrap: anywhere; }

/* captions and labels */
.stCaption, [data-testid="stCaptionContainer"] { font-size: var(--fs-meta); color: var(--text-3); text-align: left; }
label, .stMarkdown label, [data-testid="stWidgetLabel"] p {
  font-size: var(--fs-meta) !important;
  font-weight: 580 !important;
  letter-spacing: 0.055em;
  text-transform: uppercase;
  color: var(--text-3) !important;
  text-align: left;
}
[data-testid="stWidgetLabel"] { padding-bottom: 2px !important; }
[data-testid="stWidgetLabel"] p { margin: 0; }
[data-testid="stTooltipIcon"] { color: var(--text-4); }

hr, [data-testid="stDivider"] { border-color: var(--border); }
"""


# ---------------------------------------------------------------------------
# 2. Streamlit chrome removal
# ---------------------------------------------------------------------------


def _chrome() -> str:
    return """
footer, [data-testid="stStatusWidget"],
[data-testid="stToolbar"] [data-testid="stDecoration"],
[data-testid="stDeployButton"] { display: none !important; }
[data-testid="stHeader"] { background: transparent; pointer-events: none; height: auto; padding-top: var(--s2); }
[data-testid="stHeader"] > * { pointer-events: auto; }
[data-testid="stToolbar"] { opacity: 0.15; transition: opacity 0.2s; right: var(--s4); top: var(--s2); }
[data-testid="stToolbar"]:hover { opacity: 1; }

/* ── Sidebar toggle / hamburger button ──────────────────────────────────── */
/* Streamlit moved this button between releases. In 1.64 there are two, with
   different test ids, and neither is inside stHeader:
     sidebar open  -> stSidebarHeader > stSidebarCollapseButton  (collapse it)
     sidebar closed-> stHeader > stExpandSidebarButton           (reopen it)
   Both are listed below so neither state is left with a bare button. */
/* The button itself: zero font-size kills the bare Material Symbols ligature
   ("keyboard_double_arrow_left") that shows when the icon font cannot load
   offline. color:transparent is a belt-and-suspenders guard. */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"] button {
  width: 36px !important;
  height: 36px !important;
  min-height: 36px !important;
  padding: 0 !important;
  font-size: 0 !important;
  line-height: 0 !important;
  color: transparent !important;
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important;
  box-shadow: var(--shadow-1) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  position: relative !important;
  overflow: hidden !important;
  transition: background .14s ease, border-color .14s ease, box-shadow .14s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"] button:hover {
  background: var(--surface-2) !important;
  border-color: var(--border-2) !important;
  box-shadow: var(--shadow-2) !important;
}
/* Hide the ligature wherever it is written: Streamlit wraps it in its own
   element, so the button alone is not enough. */
[data-testid="stSidebarCollapseButton"] button *,
[data-testid="stExpandSidebarButton"] button * {
  font-size: 0 !important;
  line-height: 0 !important;
  color: transparent !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
/* Paint our hamburger icon via ::before using the inline SVG CSS mask.
   Pseudo-elements are not affected by the parent font-size:0, so the size is
   restored explicitly here. */
[data-testid="stSidebarCollapseButton"] button::before,
[data-testid="stExpandSidebarButton"] button::before {
  content: "" !important;
  display: block !important;
  position: static !important;
  width: 18px !important;
  height: 18px !important;
  font-size: 14px !important;
  opacity: 1 !important;
  flex: 0 0 18px !important;
  background: var(--text-3) !important;
  -webkit-mask: var(--i-menu) no-repeat center / contain !important;
  mask: var(--i-menu) no-repeat center / contain !important;
  transition: background .14s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover::before,
[data-testid="stExpandSidebarButton"] button:hover::before {
  background: var(--accent) !important;
}
/* The sidebar's own header row has room for the button; keep it from being
   squeezed by Streamlit's default padding. */
[data-testid="stSidebarHeader"] { gap: var(--s2); }

/* expanders become plain disclosure rows */
[data-testid="stExpander"] {
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  background: var(--surface);
  box-shadow: none;
  overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: var(--fs-meta); color: var(--text-2); }
details summary { cursor: pointer; }
summary::-webkit-details-marker { display: none; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p { font-size: var(--fs-meta); }
/* alerts */
[data-testid="stAlert"] { border-radius: var(--r-md); font-size: var(--fs-body); }
/* spinner only where Streamlit insists */
[data-testid="stSpinner"] i { border-top-color: var(--accent) !important; }
"""


# ---------------------------------------------------------------------------
# 3. Inputs
# ---------------------------------------------------------------------------


def _inputs() -> str:
    return """
input[type="text"], input[type="number"], input[type="date"], textarea, [data-baseweb="input"] {
  font-family: var(--font) !important;
  font-size: var(--fs-body) !important;
  color: var(--text) !important;
  background: var(--surface) !important;
  border: 1px solid var(--border-2) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-1) !important;
}
input[type="text"]:focus, input[type="number"]:focus, textarea:focus,
[data-baseweb="input"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: var(--focus) !important;
  outline: none !important;
}
input::placeholder, textarea::placeholder { color: var(--text-4) !important; }
textarea { line-height: 1.6 !important; padding: var(--s3) var(--s4) !important; }
input[type="text"], input[type="number"], input[type="date"] { padding: 0.75rem var(--s3) !important; }
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stNumberInputRootElement"], [data-testid="stDateInputRootElement"] { width: 100%; }

/* selectbox */
[data-testid="stSelectbox"] > div > div {
  border-radius: var(--r-md) !important;
  border-color: var(--border-2) !important;
  background: var(--surface) !important;
  font-size: var(--fs-body);
  min-height: 2.5rem;
}
[data-testid="stSelectbox"] svg { color: var(--text-3); }

/* checkbox: a tick, not a big box */
[data-testid="stCheckbox"] [role="checkbox"] {
  width: 17px; height: 17px;
  border-radius: 5px;
  border-color: var(--border-2);
  background: var(--surface);
}
[data-testid="stCheckbox"] [role="checkbox"]:checked {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
}
[data-testid="stCheckbox"] [role="checkbox"]:checked svg { stroke: #fff; }
[data-testid="stCheckbox"] label { text-transform: none !important; font-size: var(--fs-body) !important; color: var(--text) !important; font-weight: 450 !important; }
[data-testid="stCheckbox"] label p { font-size: var(--fs-body) !important; text-transform: none !important; letter-spacing: 0 !important; color: var(--text) !important; }

/* toggle */
[data-testid="stToggle"] [data-baseweb="checkbox"] {
  width: 34px; height: 19px; border-radius: 999px;
  background: var(--border-2); border: none;
}
[data-testid="stToggle"] [data-baseweb="checkbox"][aria-checked="true"] { background: var(--accent); }
[data-testid="stToggle"] [role="switch"], [data-testid="stToggle"] [role="checkbox"] { transition: background .14s ease; }
[data-testid="stToggle"] label p { text-transform: none !important; letter-spacing: 0 !important; color: var(--text) !important; font-size: var(--fs-body) !important; }

/* slider */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
  background: var(--accent) !important; border-color: #fff !important;
  box-shadow: var(--shadow-1) !important; width: 15px !important; height: 15px !important;
}
[data-testid="stSlider"] [data-testid="stThumbValue"] { font-size: var(--fs-meta); color: var(--text-2); }

/* file uploader: a quiet drop target. Streamlit's own instructions stay
   visible - they are the only explanation of what is accepted. */
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface-2) !important;
  border: 1px dashed var(--border-2) !important;
  border-radius: var(--r-md) !important;
  min-height: 76px;
  padding: var(--s3) var(--s4) !important;
  transition: border-color .14s ease, background .14s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--accent-line) !important;
  background: var(--accent-soft) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div {
  color: var(--text-3) !important;
  font-size: var(--fs-meta) !important;
}
[data-testid="stFileUploaderDropzone"] button[data-testid^="stBaseButton"] {
  min-height: 1.9rem; font-size: var(--fs-meta);
}
/* The drop zone's own Upload button is Streamlit's, so its icon is the ligature
   span hidden above. Paint the same line icon the app's buttons use. */
[data-testid="stFileUploaderDropzone"] button::before {
  content: "";
  display: inline-block;
  width: 15px; height: 15px;
  flex: 0 0 15px;
  margin-right: 8px;
  background: currentColor;
  -webkit-mask: var(--i-upload) no-repeat center / contain;
  mask: var(--i-upload) no-repeat center / contain;
}
/* With files present Streamlit adds a borderless "Add files" button whose only
   content was the ligature. It needs the icon but no gap. */
[data-testid="stFileUploaderDropzone"] button[aria-label="Add files"]::before {
  margin-right: 0;
  -webkit-mask-image: var(--i-plus);
  mask-image: var(--i-plus);
}
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderFile"] {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-sm);
  font-size: var(--fs-meta); padding: var(--s1) var(--s2);
}
"""


# ---------------------------------------------------------------------------
# 4. Buttons
# ---------------------------------------------------------------------------


def _buttons() -> str:
    return """
button[data-testid^="stBaseButton"] {
  font-family: var(--font);
  font-size: var(--fs-body);
  font-weight: 560;
  letter-spacing: 0;
  border-radius: var(--r-md);
  min-height: 44px;
  padding: 0 var(--s4);
  box-shadow: var(--shadow-1);
  transition: transform var(--dur-hover) var(--ease-default),
              background var(--dur-hover) var(--ease-default),
              border-color var(--dur-hover) var(--ease-default),
              box-shadow var(--dur-hover) var(--ease-default);
}
button[data-testid^="stBaseButton"] * { font-family: var(--font); }
button[data-testid^="stBaseButton-secondary"] {
  background: var(--surface);
  border: 1px solid var(--border-2);
  color: var(--text);
}
button[data-testid^="stBaseButton-secondary"]:hover {
  background: var(--surface-2);
  border-color: var(--text-4);
  color: var(--text);
  box-shadow: var(--shadow-2);
  transform: translateY(-1px);
}
button[data-testid^="stBaseButton-primary"] {
  background: linear-gradient(180deg, var(--accent-light) 0%, var(--accent) 100%);
  border: 1px solid var(--accent-dark);
  color: #FFFFFF;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28), var(--shadow-1);
}
button[data-testid^="stBaseButton-primary"]:hover {
  background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
  border-color: var(--accent-dark);
  color: #FFFFFF;
  box-shadow: 0 4px 14px rgba(169, 124, 11, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}
button[data-testid^="stBaseButton"]:focus-visible,
button[data-testid^="stBaseButton"]:focus {
  outline: none !important;
  box-shadow: var(--focus) !important;
}
button[data-testid^="stBaseButton"]:active { transform: translateY(0.5px); }
button[data-testid^="stBaseButton"] svg { stroke-width: 1.7; }
/* Streamlit draws Material icons as font ligatures: the element literally holds
   the text "upload". PocketFriend runs offline, so the icon font never loads and
   that word prints next to the button's own label. Every icon this app shows is
   its own mask on a ::before, so drop the ligature and keep the label. */
button[data-testid^="stBaseButton"] [data-testid="stIconMaterial"] {
  display: none !important;
}
/* A label wraps one letter per row when its column gets too narrow to hold a
   word. Never break a label; the layout gives the button room instead. */
button[data-testid^="stBaseButton"],
button[data-testid^="stBaseButton"] * { white-space: nowrap; }

/* Icons on buttons. `ui.button(icon=...)` wraps the button in a keyed container
   that carries the icon name; display:contents keeps the layout untouched and
   the ::before mask paints the same line icon the HTML uses. */
[class*="pf-ic-"] { display: contents; }
[class*="pf-ic-"] button::before {
  content: "";
  display: inline-block;
  width: 15px; height: 15px;
  flex: 0 0 15px;
  margin-right: 8px;
  background: currentColor;
  -webkit-mask: var(--i-file) no-repeat center / contain;
  mask: var(--i-file) no-repeat center / contain;
}
[class*="pf-ic-home-"] button::before { -webkit-mask-image: var(--i-home); mask-image: var(--i-home); }
[class*="pf-ic-ask-"] button::before { -webkit-mask-image: var(--i-ask); mask-image: var(--i-ask); }
[class*="pf-ic-plan-"] button::before { -webkit-mask-image: var(--i-plan); mask-image: var(--i-plan); }
[class*="pf-ic-quiz-"] button::before { -webkit-mask-image: var(--i-quiz); mask-image: var(--i-quiz); }
[class*="pf-ic-folder-"] button::before { -webkit-mask-image: var(--i-folder); mask-image: var(--i-folder); }
[class*="pf-ic-docs-"] button::before { -webkit-mask-image: var(--i-docs); mask-image: var(--i-docs); }
[class*="pf-ic-settings-"] button::before { -webkit-mask-image: var(--i-settings); mask-image: var(--i-settings); }
[class*="pf-ic-file-"] button::before { -webkit-mask-image: var(--i-file); mask-image: var(--i-file); }
[class*="pf-ic-list-"] button::before { -webkit-mask-image: var(--i-list); mask-image: var(--i-list); }
[class*="pf-ic-plus-"] button::before { -webkit-mask-image: var(--i-plus); mask-image: var(--i-plus); }
[class*="pf-ic-check-"] button::before { -webkit-mask-image: var(--i-check); mask-image: var(--i-check); }
[class*="pf-ic-trash-"] button::before { -webkit-mask-image: var(--i-trash); mask-image: var(--i-trash); }
[class*="pf-ic-send-"] button::before { -webkit-mask-image: var(--i-send); mask-image: var(--i-send); }
[class*="pf-ic-spark-"] button::before { -webkit-mask-image: var(--i-spark); mask-image: var(--i-spark); }
[class*="pf-ic-refresh-"] button::before { -webkit-mask-image: var(--i-refresh); mask-image: var(--i-refresh); }
[class*="pf-ic-download-"] button::before { -webkit-mask-image: var(--i-download); mask-image: var(--i-download); }
[class*="pf-ic-close-"] button::before { -webkit-mask-image: var(--i-close); mask-image: var(--i-close); }
[class*="pf-ic-play-"] button::before { -webkit-mask-image: var(--i-play); mask-image: var(--i-play); }
[class*="pf-ic-science-"] button::before { -webkit-mask-image: var(--i-science); mask-image: var(--i-science); }
[class*="pf-ic-arrow-"] button::before { -webkit-mask-image: var(--i-arrow); mask-image: var(--i-arrow); }
[class*="pf-ic-target-"] button::before { -webkit-mask-image: var(--i-target); mask-image: var(--i-target); }
[class*="pf-ic-upload-"] button::before { -webkit-mask-image: var(--i-upload); mask-image: var(--i-upload); }
[class*="pf-ic-layers-"] button::before { -webkit-mask-image: var(--i-layers); mask-image: var(--i-layers); }
[class*="pf-ic-quote-"] button::before { -webkit-mask-image: var(--i-quote); mask-image: var(--i-quote); }
[class*="pf-ic-book-"] button::before { -webkit-mask-image: var(--i-book); mask-image: var(--i-book); }
[class*="pf-ic-clock-"] button::before { -webkit-mask-image: var(--i-clock); mask-image: var(--i-clock); }
[class*="pf-ic-bolt-"] button::before { -webkit-mask-image: var(--i-bolt); mask-image: var(--i-bolt); }
[class*="pf-ic-lock-"] button::before { -webkit-mask-image: var(--i-lock); mask-image: var(--i-lock); }
/* download button */
[data-testid="stDownloadButton"] button { width: 100%; }
"""


# ---------------------------------------------------------------------------
# 4b. Dialogs
# ---------------------------------------------------------------------------


def _dialogs() -> str:
    return """
/* st.dialog, used to confirm a destructive action before it runs. Streamlit
   ships a plain white sheet with its own padding; this gives it the same
   surface, border and shadow as the rest of the app. */
div[data-testid="stDialog"] {
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: var(--r-lg) !important;
  box-shadow: var(--shadow-3) !important;
  padding: var(--s5) var(--s5) var(--s4) !important;
  font-family: var(--font);
}
div[data-testid="stDialog"] h1,
div[data-testid="stDialog"] h2,
div[data-testid="stDialog"] h3,
div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {
  font-family: var(--font) !important;
}
/* The close control is a borderless icon button, so the global button padding
   would blow it up to the size of a full button. */
div[data-testid="stDialog"] button[aria-label="Close"] {
  width: 32px !important;
  min-height: 32px !important;
  height: 32px !important;
  padding: 0 !important;
  border: 1px solid transparent !important;
  border-radius: var(--r-xs) !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text-3) !important;
  transition: background var(--dur-hover) var(--ease-default), color var(--dur-hover) var(--ease-default);
}
div[data-testid="stDialog"] button[aria-label="Close"]:hover {
  background: var(--surface-2) !important;
  color: var(--text) !important;
}
div[data-testid="stDialog"] button[aria-label="Close"] svg { stroke-width: 1.9; }
/* Body copy and the actions: a readable column, buttons full width. */
div[data-testid="stDialog"] [data-testid="stVerticalBlock"] { gap: var(--s4); }
div[data-testid="stDialog"] [data-testid="stHorizontalBlock"] { gap: var(--s3); }
"""


# ---------------------------------------------------------------------------
# 5. Sidebar
# ---------------------------------------------------------------------------


def _sidebar() -> str:
    return """
/* ── Sidebar shell ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border);
  width: 264px !important;
  min-width: 264px !important;
  max-width: 264px !important;
  box-shadow: 2px 0 12px -4px rgba(15, 21, 40, 0.05);
}
section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div {
  padding: var(--s4) var(--s3) var(--s5) !important;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: var(--s3); }
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { gap: var(--s2); }

/* ── Brand ──────────────────────────────────────────────────────────────── */
.pf-brand {
  display: flex; align-items: center; gap: 11px;
  padding: var(--s2) var(--s2) var(--s3);
  margin-bottom: 2px;
}
.pf-brand__mark {
  width: 36px; height: 36px; flex: 0 0 36px;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--accent-light) 0%, var(--accent-dark) 100%);
  color: #FFFFFF;
  display: grid; place-items: center;
  box-shadow: 0 2px 8px rgba(169, 124, 11, 0.35);
}
.pf-brand__mark svg { width: 18px; height: 18px; }
.pf-brand__text { min-width: 0; }
.pf-brand__name {
  font-size: 14.5px; font-weight: 700; color: var(--text);
  letter-spacing: -0.02em; line-height: 1.2;
}
.pf-brand__tag { font-size: 11.5px; font-weight: 400; color: var(--text-4); line-height: 1.3; margin-top: 2px; }

/* ── Navigation list ────────────────────────────────────────────────────── */
[class*="pf-navlist-"] { gap: 2px; }
[class*="pf-navlist-"] [data-testid="stVerticalBlock"] { gap: 2px; }
[class*="pf-navitem-"] { position: relative; }

/* default (inactive) nav button */
[class*="pf-navitem-"] button[data-testid^="stBaseButton"] {
  width: 100%;
  justify-content: flex-start;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-3);
  font-weight: 500;
  font-size: 14px;
  min-height: 2.5rem;
  padding: 0 var(--s3);
  border-radius: var(--r-sm);
  text-align: left;
  letter-spacing: 0;
  box-shadow: none;
  transition: background var(--dur-hover) var(--ease-default),
              color var(--dur-hover) var(--ease-default),
              transform var(--dur-hover) var(--ease-default);
}
[class*="pf-navitem-"] button[data-testid^="stBaseButton"]:hover {
  background: var(--surface-2);
  color: var(--text);
  border-color: var(--border);
  transform: translateX(2px);
}
/* icon before text on inactive items */
[class*="pf-navitem-"] button[data-testid^="stBaseButton-secondary"]::before {
  opacity: 0.55;
  transition: opacity var(--dur-hover) var(--ease-default);
}
[class*="pf-navitem-"] button[data-testid^="stBaseButton-secondary"]:hover::before {
  opacity: 0.9;
}
/* active nav button */
[class*="pf-navitem-"] button[data-testid="stBaseButton-primary"] {
  background: var(--accent-soft);
  border-color: var(--accent-line);
  color: var(--accent);
  font-weight: 640;
  position: relative;
  box-shadow: inset 0 0 0 1px var(--accent-line);
}
/* active accent rail with subtle glow */
[class*="pf-navitem-"] button[data-testid="stBaseButton-primary"]::after {
  content: "";
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 18px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
  box-shadow: 0 0 8px rgba(169, 124, 11, 0.5);
}
[class*="pf-navitem-"] button[data-testid="stBaseButton-primary"]:hover {
  background: var(--accent-soft);
  color: var(--accent);
  transform: none;
}
[class*="pf-navitem-"] [data-testid="stElementContainer"] { width: 100%; }
[class*="pf-navitem-"] button p { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Nav section divider */
[class*="pf-navlist-"] + * { margin-top: var(--s2); }

/* ── Sidebar flex grow spacer ───────────────────────────────────────────── */
[data-testid="stSidebarUserContent"] { display: flex; flex-direction: column; }
[class*="pf-sidebarfill-"] { flex: 1 1 auto; min-height: var(--s4); }

/* ── Sidebar section labels ─────────────────────────────────────────────── */
.pf-navlabel {
  font-size: 10px; font-weight: 680; letter-spacing: .09em;
  text-transform: uppercase; color: var(--text-4);
  padding: 0 var(--s2);
  margin: 0 0 var(--s1);
}

/* ── Library / status facts ─────────────────────────────────────────────── */
.pf-facts {
  display: flex; flex-direction: column; gap: 2px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: var(--s2) var(--s3);
}
.pf-fact {
  display: flex; justify-content: space-between; align-items: center;
  gap: var(--s3); font-size: var(--fs-meta);
  padding: 3px 0;
}
.pf-fact__label { color: var(--text-3); }
.pf-fact__value {
  color: var(--text); font-weight: 620; text-align: right;
  font-variant-numeric: tabular-nums;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: var(--r-xs);
  padding: 1px 6px;
  font-size: 11.5px;
}

/* ── Sidebar footnote ───────────────────────────────────────────────────── */
.pf-side-note {
  font-size: 11.5px; color: var(--text-4); line-height: 1.5;
  padding: var(--s2) var(--s2) 0;
}
.pf-side-note strong { color: var(--text-3); font-weight: 580; }

/* ── Status indicators ──────────────────────────────────────────────────── */
.pf-status {
  display: flex; gap: var(--s2); align-items: flex-start;
  padding: var(--s2) var(--s2);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.pf-status__dot {
  width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex: 0 0 8px;
  background: var(--text-4);
  position: relative;
}
.pf-status--ok .pf-status__dot {
  background: var(--ok);
  box-shadow: 0 0 0 3px var(--ok-soft);
}
.pf-status--ok .pf-status__dot::after {
  content: "";
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 1.5px solid var(--ok);
  animation: pf-ping 2.4s cubic-bezier(0, 0, 0.2, 1) infinite;
}
@keyframes pf-ping {
  0% { transform: scale(1); opacity: 0.8; }
  70% { transform: scale(2.2); opacity: 0; }
  100% { transform: scale(2.2); opacity: 0; }
}
.pf-status--warn .pf-status__dot { background: var(--warn); box-shadow: 0 0 0 3px var(--warn-soft); }
.pf-status--danger .pf-status__dot { background: var(--danger); box-shadow: 0 0 0 3px var(--danger-soft); }
.pf-status--accent .pf-status__dot { background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.pf-status__label { font-size: var(--fs-meta); font-weight: 620; color: var(--text); }
.pf-status__detail { font-size: 11.5px; color: var(--text-3); line-height: 1.4; }

/* ── Notes (inline callouts) ────────────────────────────────────────────── */
.pf-note {
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-2);
  background: var(--surface-2);
  border-radius: var(--r-md);
  padding: var(--s3) var(--s4);
  font-size: var(--fs-meta);
  line-height: 1.6;
  color: var(--text-2);
}
.pf-note--accent { background: var(--accent-soft); border-color: var(--accent-line); border-left-color: var(--accent); color: var(--text-2); }
.pf-note--ok     { background: var(--ok-soft);     border-color: var(--ok-line);     border-left-color: var(--ok); }
.pf-note--warn   { background: var(--warn-soft);   border-color: var(--warn-line);   border-left-color: var(--warn); }
.pf-note--danger { background: var(--danger-soft); border-color: var(--danger-line); border-left-color: var(--danger); }
.pf-note--quiet  { background: transparent; border-style: dashed; color: var(--text-3); }
.pf-note__title {
  display: block; font-weight: 640; color: var(--text);
  margin-bottom: 3px; font-size: var(--fs-meta);
}
.pf-note pre {
  font-family: var(--mono); font-size: 11.5px; white-space: pre-wrap; margin: 0;
}
"""


# ---------------------------------------------------------------------------
# 6. Page furniture: top bar, section headers, dividers
# ---------------------------------------------------------------------------


def _furniture() -> str:
    return """
.pf-top {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: var(--s5); flex-wrap: wrap;
  padding-bottom: var(--s4);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--s2);
}
.pf-top__main { min-width: 0; }
.pf-top__eyebrow {
  font-size: 10.5px; font-weight: 620; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 5px;
}
.pf-top__title {
  font-size: var(--fs-title); font-weight: 680; letter-spacing: -0.026em;
  color: var(--text); line-height: 1.18; margin: 0;
}
.pf-top__sub {
  font-size: var(--fs-body); color: var(--text-3); margin: 4px 0 0;
  line-height: 1.6; max-width: 74ch;
}
.pf-top__meta { display: flex; flex-wrap: wrap; gap: var(--s2); margin-top: var(--s3); }
.pf-top__actions { display: flex; align-items: center; gap: var(--s2); }

/* the page bar: title on the left, real actions on the right, one hairline under
   both. Keyed container: st.container(key="pf-bar-...") */
[class*="pf-bar-"] {
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--s4);
  margin-bottom: var(--s5);
}
[class*="pf-bar-"] .pf-top { border: 0; padding: 0; margin: 0; }
[class*="pf-bar-"] [data-testid="stHorizontalBlock"] { align-items: flex-end; gap: var(--s5); }
[class*="pf-bar-"] [data-testid="stColumn"] { padding: 0; }
[class*="pf-bar-"] [data-testid="stVerticalBlock"] { gap: var(--s3); }
[class*="pf-bar-"] [data-testid="stButton"] button { white-space: nowrap; }

/* a section that is the whole working surface on a light page */
[class*="pf-sheet-"] {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
  margin-bottom: var(--s6);
}
[class*="pf-sheet-"] [data-testid="stVerticalBlock"] { gap: var(--s5); }
.pf-muted { color: var(--text-3); }
.pf-nowrap { white-space: nowrap; }

.pf-section {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: var(--s4); margin: var(--s2) 0 var(--s3);
}
.pf-section__title {
  display: flex; align-items: center; gap: 7px;
  font-size: var(--fs-section); font-weight: 640; color: var(--text);
  letter-spacing: -0.014em;
}
.pf-section__title svg { width: 14px; height: 14px; color: var(--text-3); }
.pf-section__sub { font-size: var(--fs-meta); color: var(--text-3); margin-top: 2px; }
.pf-section__aside { font-size: var(--fs-meta); color: var(--text-4); white-space: nowrap; }
.pf-rule { border: 0; border-top: 1px solid var(--border); margin: var(--s5) 0; }
.pf-rule--tight { margin: var(--s3) 0; }
.pf-spacer { display: block; }
.pf-spacer--sm { height: var(--s3); }
.pf-spacer--md { height: var(--s5); }
.pf-spacer--lg { height: var(--s6); }
.pf-i { vertical-align: -2.5px; }
.pf-i--sm { width: 13px; height: 13px; }
.pf-i--lg { width: 18px; height: 18px; }

/* tags: the only full-pill in the system, used for metadata and scope */
.pf-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: var(--fs-meta); font-weight: 560; color: var(--text-2);
  background: var(--surface-3);
  border: 1px solid transparent;
  border-radius: var(--r-full);
  padding: 2px 9px;
  white-space: nowrap;
  /* A pill never gets to be as wide as its own text: as a flex item it may
     shrink, and `nowrap` can then no longer widen the row it sits in. */
  min-width: 0;
  max-width: 100%;
}
/* The same pill for a value that is a sentence rather than a label: it wraps
   inside the pill instead of pushing the row past the edge of the page. */
.pf-tag--wrap {
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.5;
  border-radius: var(--r-md);
}
.pf-tag--accent { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-line); }
.pf-tag--sage { background: var(--sage-soft); color: var(--sage); border-color: var(--sage-line); }
.pf-tag--ok { background: var(--ok-soft); color: var(--ok); border-color: var(--ok-line); }
.pf-tag--warn { background: var(--warn-soft); color: var(--warn); border-color: var(--warn-line); }
.pf-tag--danger { background: var(--danger-soft); color: var(--danger); border-color: var(--danger-line); }
.pf-tag--quiet { background: transparent; color: var(--text-3); border-color: var(--border); }
.pf-tag svg { width: 11px; height: 11px; }
.pf-tags { display: flex; flex-wrap: wrap; gap: var(--s2); align-items: center; min-width: 0; }
/* Inside a wrapping meta row a tag is a flex item, so it needs `min-width: 0`
   before `max-width: 100%` can actually do its job. */
.pf-tags > *, .pf-item__meta > * { min-width: 0; max-width: 100%; }
"""


# ---------------------------------------------------------------------------
# 7. Workspace zones: the three-column research layout
# ---------------------------------------------------------------------------


def _workspace() -> str:
    return """
/* A workspace is a framed surface split by dividers, not three cards.
   Keyed container: st.container(key="pf-zone-...") */
[class*="pf-zone-"] {
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  padding: 0 var(--s5);
}
[class*="pf-zone-"] > div { gap: 0 !important; }
[class*="pf-zone-"] [data-testid="stVerticalBlock"] { gap: var(--s4); }
[class*="pf-zone-"] [data-testid="stMainBlockContainer"],
[class*="pf-zone-"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
  padding: 0;
}
[class*="pf-zone-"] [data-testid="stHorizontalBlock"] { gap: 0; align-items: stretch; }
[class*="pf-zone-"] [data-testid="stColumn"] { padding: 0 var(--s5); min-width: 0; }
[class*="pf-zone-"] [data-testid="stColumn"] + [data-testid="stColumn"] {
  border-left: 1px solid var(--border);
}
/* the row of zones carries the frame, so the three panels read as one surface */
[data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) {
  gap: 0;
  align-items: stretch;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
  border-top: 1px solid var(--border);
  padding-top: var(--s4);
}
[data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) > [data-testid="stColumn"] {
  padding: 0;
  min-width: 0;
}
[data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) > [data-testid="stColumn"]
  + [data-testid="stColumn"] { border-left: 1px solid var(--border); }
.pf-zonehead {
  display: flex; align-items: center; gap: 6px;
  font-size: 10.5px; font-weight: 640; letter-spacing: .07em;
  text-transform: uppercase; color: var(--text-4);
  margin-bottom: var(--s4);
}
.pf-zonehead svg { width: 13px; height: 13px; }
.pf-zonebody { height: 100%; }

/* a zone that scrolls instead of stretching the page */
[class*="pf-scroll-"] {
  max-height: 64vh; overflow-y: auto;
  margin-right: calc(-1 * var(--s3)); padding-right: var(--s3);
}
[class*="pf-scroll-"]::-webkit-scrollbar { width: 6px; }
[class*="pf-scroll-"]::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 99px; }
[class*="pf-scroll-"]::-webkit-scrollbar-track { background: transparent; }

/* The conversation is the one zone that outgrows the window. It scrolls inside
   its own column, so the page stays the same height and the composer keeps the
   bottom of the screen instead of being pushed off it. */
[class*="pf-scroll-ask-conversation"] {
  max-height: calc(100vh - 238px);
  overscroll-behavior: contain;
  scrollbar-width: thin;
  margin-right: 0;
  padding-right: var(--s2);
}

/* flat panel used inside a zone */
.pf-panel {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--s5);
  box-shadow: var(--shadow-xs);
}
.pf-panel--flush { padding: 0; overflow: hidden; }
.pf-panel__title {
  font-size: var(--fs-meta); font-weight: 620; color: var(--text);
  display: flex; align-items: center; gap: 6px; margin-bottom: var(--s2);
}
.pf-panel__title svg { width: 13px; height: 13px; color: var(--text-3); }
.pf-panel__body { font-size: var(--fs-body); color: var(--text-2); line-height: 1.6; }

/* Make the Ask composer sticky like a modern workspace */
[class*="pf-composer-ask"] {
  position: sticky;
  bottom: 0;
  background: var(--surface);
  z-index: 100;
  padding: var(--s4) 0;
  border-top: 1px solid var(--border);
}
"""


# ---------------------------------------------------------------------------
# 8. Rows: documents, tasks, sources, answers
# ---------------------------------------------------------------------------


def _rows() -> str:
    return """
/* One compact row per item. The key class supplies the frame; the CSS keeps the
   row flat with a hairline separator instead of a card. */
[class*="pf-item-"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: var(--s3) var(--s4);
  margin-bottom: var(--s2);
  box-shadow: var(--shadow-xs);
  transition: transform var(--dur-hover) var(--ease-default),
              border-color var(--dur-hover) var(--ease-default),
              box-shadow var(--dur-hover) var(--ease-default);
}
[class*="pf-item-"]:hover { 
  border-color: var(--border-2);
  box-shadow: var(--shadow-2);
  transform: translateY(-1px);
}
[class*="pf-item-"]:last-child { margin-bottom: 0; }
[class*="pf-item-"] [data-testid="stHorizontalBlock"] { gap: var(--s3); align-items: center; }
[class*="pf-item-"] [data-testid="stMarkdownContainer"] p { margin: 0; }
[class*="pf-item-"] [data-testid="stButton"] button { min-height: 1.95rem; }
[class*="pf-item-"] .pf-btn-icon::before { width: 14px; height: 14px; margin-right: 5px; }
/* the selected item in a source list */
[class*="pf-item-on-"] {
  border-color: var(--accent-line);
  background: var(--accent-soft);
}
[class*="pf-item-on-"] .pf-item__title { color: var(--accent); }

.pf-item__title {
  font-size: var(--fs-body); font-weight: 560; color: var(--text);
  line-height: 1.4; word-break: break-word;
}
.pf-item__title--done { color: var(--text-4); text-decoration: line-through; text-decoration-color: var(--border-2); }
.pf-item__note {
  font-size: var(--fs-meta); color: var(--text-3); line-height: 1.5;
  margin-top: 3px; overflow-wrap: anywhere;
}
.pf-item__meta { display: flex; flex-wrap: wrap; gap: var(--s2); align-items: center; margin-top: 5px; min-width: 0; }
.pf-item__body { display: flex; gap: var(--s3); align-items: flex-start; min-width: 0; }
.pf-item__glyph {
  flex: 0 0 auto; width: 26px; height: 26px; border-radius: 7px;
  display: grid; place-items: center;
  background: var(--surface-3); color: var(--text-3);
}
.pf-item__glyph svg { width: 14px; height: 14px; }
.pf-item__glyph--accent { background: var(--accent-soft); color: var(--accent); }
.pf-item__glyph--sage { background: var(--sage-soft); color: var(--sage); }
.pf-item__text { min-width: 0; flex: 1 1 auto; }

/* quiet action button that only shows on hover */
.pf-rowact button[data-testid^="stBaseButton"] {
  background: transparent; border-color: transparent; color: var(--text-4);
  padding: 0 var(--s2); min-height: 1.9rem; font-size: var(--fs-meta); font-weight: 520;
}
.pf-rowact button[data-testid^="stBaseButton"]:hover {
  background: var(--danger-soft); color: var(--danger); border-color: var(--danger-line);
}
.pf-rowact button[data-testid^="stBaseButton-primary"] { background: var(--surface); border-color: var(--border-2); color: var(--text-2); }

/* source rows in the Sources zone: real buttons, notebook-style */
[class*="pf-srcall-"] { margin-bottom: 1px; }
[class*="pf-srcall-"] + [class*="pf-srcitem-"],
[class*="pf-srcall-"] + div [class*="pf-srcitem-"] { margin-top: 1px; }
[class*="pf-srcall-"] button[data-testid^="stBaseButton"],
[class*="pf-srcitem-"] button[data-testid^="stBaseButton"] {
  width: 100%;
  justify-content: flex-start;
  text-align: left;
  min-height: 2.25rem;
  padding: 0 var(--s3);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  color: var(--text-2);
  font-size: var(--fs-body);
  font-weight: 520;
  overflow: hidden;
}
[class*="pf-srcall-"] button[data-testid^="stBaseButton"]::before,
[class*="pf-srcitem-"] button[data-testid^="stBaseButton"]::before { content: none; }
[class*="pf-srcall-"] button[data-testid^="stBaseButton"]:hover,
[class*="pf-srcitem-"] button[data-testid^="stBaseButton"]:hover {
  background: var(--surface-3);
  color: var(--text);
}
[class*="pf-srcall-"] button[data-testid="stBaseButton-primary"],
[class*="pf-srcitem-"] button[data-testid="stBaseButton-primary"] {
  background: var(--accent-soft);
  border-color: var(--accent-line);
  color: var(--accent);
  font-weight: 580;
}
[class*="pf-srcall-"] button[data-testid="stBaseButton-primary"]::before,
[class*="pf-srcitem-"] button[data-testid="stBaseButton-primary"]::before { content: none; }
[class*="pf-srcall-"] button[data-testid="stBaseButton-primary"]:hover,
[class*="pf-srcitem-"] button[data-testid="stBaseButton-primary"]:hover {
  background: var(--accent-soft);
  color: var(--accent);
}
[class*="pf-srcall-"] button p, [class*="pf-srcitem-"] button p {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;
}
"""


# ---------------------------------------------------------------------------
# 9. Conversation, answers, citations, evidence
# ---------------------------------------------------------------------------


def _conversation() -> str:
    return """
/* the student speaks in one quiet line; the answer gets the space */
.pf-ask {
  display: flex; justify-content: flex-end;
  margin: var(--s5) 0 var(--s3);
}
.pf-ask__bubble {
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  border-bottom-right-radius: var(--r-sm);
  padding: var(--s3) var(--s4);
  font-size: var(--fs-body);
  color: var(--text);
  line-height: 1.6;
  max-width: 82%;
}
.pf-answer { margin-bottom: var(--s5); }
[class*="pf-answerbody-"] {
  margin-bottom: var(--s5);
  animation: pf-fade-up var(--dur-enter) var(--ease-default) both;
}
@keyframes pf-fade-up {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}
[class*="pf-answerbody-"] [data-testid="stElementContainer"] > div { gap: var(--s3); }
[class*="pf-answerbody-"] .pf-note { margin-top: var(--s3); }
.pf-answer__head {
  display: flex; align-items: center; gap: 6px;
  font-size: 10.5px; font-weight: 640; letter-spacing: .07em;
  text-transform: uppercase; color: var(--text-4);
  margin-bottom: var(--s2);
}
.pf-answer__head svg { width: 12px; height: 12px; color: var(--accent); }
.pf-answer__body { font-size: 14.5px; line-height: 1.68; color: var(--text); }
.pf-answer__body p { margin-bottom: var(--s3); }
.pf-answer__body ul, .pf-answer__body ol { margin-bottom: var(--s3); }
.pf-answer__foot {
  margin-top: var(--s4); padding-top: var(--s3);
  border-top: 1px solid var(--border);
  display: flex; flex-wrap: wrap; gap: var(--s2); align-items: center;
}
.pf-answer__label {
  font-size: var(--fs-meta); color: var(--text-3); margin-right: 2px;
  display: inline-flex; align-items: center; gap: 5px;
}
.pf-answer__label svg { width: 12px; height: 12px; }

/* citations: [Document.pdf · p. 12 · 0.87] pills */
.pf-cite {
  display: inline-flex; align-items: baseline; gap: 6px;
  font-size: 12px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  border-radius: var(--r-full);
  padding: 2px 8px;
  color: var(--accent);
  margin-right: 4px;
  line-height: 1.5;
}
.pf-cite__file { font-weight: 620; color: var(--accent); }
.pf-cite__sep { opacity: 0.5; }
.pf-cite__page { color: var(--accent); opacity: 0.85; font-variant-numeric: tabular-nums; }
.pf-cite__match {
  font-variant-numeric: tabular-nums; color: var(--accent); opacity: 0.6;
  border-left: 1px solid var(--accent-line); padding-left: 6px;
}

/* evidence list in the right-hand zone */
.pf-ev {
  border-bottom: 1px solid var(--border);
  padding: var(--s3) 0;
}
.pf-ev:last-child { margin-bottom: 0; }
.pf-ev__head {
  display: flex; align-items: baseline; justify-content: space-between; gap: var(--s2);
  margin-bottom: 4px;
}
.pf-ev__file {
  font-size: var(--fs-meta); font-weight: 580; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pf-ev__page { font-size: var(--fs-meta); color: var(--accent); white-space: nowrap; font-variant-numeric: tabular-nums; }
.pf-ev__excerpt {
  font-size: 11.5px; line-height: 1.55; color: var(--text-3);
  display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical;
  overflow: hidden;
}
.pf-ev__match {
  display: flex; align-items: center; gap: 6px;
  font-size: 10.5px; color: var(--text-4); margin-top: 5px;
}
.pf-meter {
  flex: 1 1 auto; height: 3px; border-radius: 99px;
  background: var(--surface-3); overflow: hidden; max-width: 84px;
}
.pf-meter__fill { display: block; height: 100%; background: var(--accent); border-radius: 99px; }
"""


# ---------------------------------------------------------------------------
# 10. Composer, empty states, loading, quiz
# ---------------------------------------------------------------------------


def _composer() -> str:
    return """
/* the ask composer sits at the end of the conversation, like a real workspace */
[class*="pf-composer-"] {
  background: var(--surface);
  border: 1px solid var(--border-2);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-1);
  padding: var(--s4) var(--s4);
  transition: border-color var(--dur-state) var(--ease-default),
              box-shadow var(--dur-state) var(--ease-default);
}
[class*="pf-composer-"]:focus-within {
  border-color: var(--accent);
  box-shadow: var(--focus);
}
[class*="pf-composer-"] [data-testid="stTextAreaRootElement"] textarea {
  border: none !important; background: transparent !important;
  padding: var(--s2) 0 !important; min-height: 62px !important;
  font-size: 14px !important; line-height: 1.6 !important;
}
[class*="pf-composer-"] [data-testid="stTextAreaRootElement"] textarea:focus { box-shadow: none !important; }
[class*="pf-composer-"] [data-testid="stWidgetLabel"] { display: none; }
[class*="pf-composer-"] [data-testid="stHorizontalBlock"] { gap: var(--s3); align-items: flex-end; }

/* The footnote sits at the bottom left of the composer */
[class*="pf-composer-"] [data-testid="stCaptionContainer"] {
  padding: 0 !important;
  margin: 0 !important;
}
[class*="pf-composer-"] [data-testid="stCaptionContainer"] p {
  margin: 0;
  font-size: 11px;
  line-height: 1.3;
  letter-spacing: .012em;
  color: var(--text-4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* while a turn is running the box is locked, so say so with the cursor too */
[class*="pf-composer-"] [data-testid="stTextAreaRootElement"] textarea:disabled {
  background: var(--surface-2) !important;
  color: var(--text-3) !important;
  cursor: progress;
}

/* suggestion prompts above an empty conversation */
.pf-prompts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s2); }
[class*="pf-prompt-"] button[data-testid^="stBaseButton"] {
  width: 100%; justify-content: flex-start; text-align: left;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text-2); font-weight: 500; min-height: 2.35rem;
}
[class*="pf-prompt-"] button[data-testid^="stBaseButton"]:hover {
  background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent);
}

/* empty states: a small glyph, one sentence, one action */
.pf-empty {
  border: 1px dashed var(--border-2);
  border-radius: var(--r-md);
  background: var(--surface-2);
  padding: var(--s6) var(--s5);
  text-align: left;
}
.pf-empty__row { display: flex; gap: var(--s4); align-items: flex-start; }
.pf-empty__glyph {
  flex: 0 0 auto; width: 30px; height: 30px; border-radius: 9px;
  display: grid; place-items: center;
  background: var(--surface); border: 1px solid var(--border); color: var(--text-3);
}
.pf-empty__glyph svg { width: 15px; height: 15px; }
.pf-empty__title { font-size: var(--fs-body); font-weight: 580; color: var(--text); }
.pf-empty__body { font-size: var(--fs-meta); color: var(--text-3); line-height: 1.55; margin-top: 3px; }
.pf-empty__hint { font-size: var(--fs-meta); color: var(--text-4); margin-top: var(--s3); }
.pf-empty--center { text-align: center; }
.pf-empty--center .pf-empty__row { flex-direction: column; align-items: center; }

/* loading: three quiet dots, never a spinner with a stack trace attached */
.pf-loading {
  display: flex; align-items: center; gap: var(--s3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--s3) var(--s4);
  box-shadow: var(--shadow-1);
}
.pf-loading__dots { display: inline-flex; gap: 4px; }
.pf-loading__dots span {
  width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
  animation: pf-pulse 1.05s ease-in-out infinite;
}
.pf-loading__dots span:nth-child(2) { animation-delay: 160ms; }
.pf-loading__dots span:nth-child(3) { animation-delay: 320ms; }
.pf-loading__text { font-size: var(--fs-meta); color: var(--text-2); font-weight: 520; }
@keyframes pf-pulse {
  0%, 80%, 100% { opacity: .25; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-2px); }
}
.pf-fadein { animation: pf-in var(--dur-enter) var(--ease-default) both; }
@keyframes pf-in { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
"""


def _quiz() -> str:
    return """
/* a focused session: progress, question, choices, verdict */
.pf-progress { display: flex; align-items: center; gap: var(--s3); margin-bottom: var(--s4); }
.pf-progress__bar {
  flex: 1 1 auto; height: 3px; border-radius: 99px; background: var(--surface-3); overflow: hidden;
}
.pf-progress__fill { display: block; height: 100%; background: var(--accent); border-radius: 99px; transition: width .2s ease; }
.pf-progress__count { font-size: var(--fs-meta); color: var(--text-3); font-variant-numeric: tabular-nums; }
.pf-question {
  font-size: 17px; font-weight: 560; line-height: 1.5; color: var(--text);
  letter-spacing: -0.01em; margin-bottom: var(--s2);
}
.pf-question__hint { font-size: var(--fs-meta); color: var(--text-3); margin-bottom: var(--s4); }

/* native radios, styled as answer rows */
[class*="pf-choice-"] [data-testid="stRadioOption"] { display: block; }
[class*="pf-choice-"] [data-testid="stRadioOption"] + [data-testid="stRadioOption"] { margin-top: var(--s2); }
[class*="pf-choice-"] [data-testid="stRadioOption"] [role="radio"] {
  display: flex; align-items: center; gap: var(--s3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-sm); padding: 0.62rem var(--s4);
  font-size: var(--fs-body); color: var(--text); line-height: 1.5;
  transition: border-color var(--dur-hover) var(--ease-default),
              background var(--dur-hover) var(--ease-default);
}
[class*="pf-choice-"] [data-testid="stRadioOption"] [role="radio"]:hover {
  border-color: var(--accent-line); background: var(--accent-soft);
}
[class*="pf-choice-"] [data-testid="stRadioOption"] [role="radio"]:focus-visible { outline: none; box-shadow: var(--focus); }
[class*="pf-choice-"] [data-testid="stRadioOption"] [role="radio"] > div:first-child { display: none; }
[class*="pf-choice-"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
  margin: 0; font-size: var(--fs-body); color: inherit;
}
[class*="pf-choice-"] [data-testid="stRadioOption"] [role="radio"]::before {
  content: counter(pf-choice);
  counter-increment: pf-choice;
  flex: 0 0 22px; width: 22px; height: 22px; border-radius: 6px;
  display: grid; place-items: center;
  background: var(--surface-3); color: var(--text-3);
  font-size: 11px; font-weight: 640;
}
[class*="pf-choice-"] { counter-reset: pf-choice; }
[class*="pf-choice-"] [data-testid="stRadioOption"]:has([role="radio"][aria-checked="true"]) [role="radio"] {
  border-color: var(--accent); background: var(--accent-soft);
}
[class*="pf-choice-"] [data-testid="stRadioOption"]:has([role="radio"][aria-checked="true"]) [role="radio"]::before {
  background: var(--accent); color: #fff;
}

/* answered: the choice list becomes plain HTML so the result is unmistakable */
.pf-answerlist { display: grid; gap: var(--s2); }
.pf-answerrow {
  display: flex; align-items: center; gap: var(--s3);
  border: 1px solid var(--border); border-radius: var(--r-sm);
  background: var(--surface-2); padding: 0.6rem var(--s4);
  font-size: var(--fs-body); line-height: 1.5; color: var(--text-2);
}
.pf-answerrow--ok { border-color: var(--ok-line); background: var(--ok-soft); color: var(--text); }
.pf-answerrow--bad { border-color: var(--danger-line); background: var(--danger-soft); color: var(--text); }
.pf-answerrow__key {
  flex: 0 0 22px; width: 22px; height: 22px; border-radius: 6px;
  display: grid; place-items: center;
  background: var(--surface); border: 1px solid var(--border);
  font-size: 11px; font-weight: 640; color: var(--text-3);
}
.pf-answerrow--ok .pf-answerrow__key { background: var(--ok); border-color: var(--ok); color: #fff; }
.pf-answerrow--bad .pf-answerrow__key { background: var(--danger); border-color: var(--danger); color: #fff; }
.pf-answerrow__text { flex: 1 1 auto; min-width: 0; }
.pf-answerrow__flag {
  font-size: 10.5px; font-weight: 620; letter-spacing: .04em; text-transform: uppercase;
  white-space: nowrap; color: var(--text-4);
}
.pf-answerrow--ok .pf-answerrow__flag { color: var(--ok); }
.pf-answerrow--bad .pf-answerrow__flag { color: var(--danger); }

.pf-verdict {
  display: flex; gap: var(--s3); align-items: flex-start;
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--surface-2); padding: var(--s3) var(--s4);
  font-size: var(--fs-body); line-height: 1.6; color: var(--text-2);
}
.pf-verdict--ok { background: var(--ok-soft); border-color: var(--ok-line); }
.pf-verdict--bad { background: var(--danger-soft); border-color: var(--danger-line); }
.pf-verdict__glyph {
  flex: 0 0 20px; width: 20px; height: 20px; border-radius: 50%;
  display: grid; place-items: center; color: #fff; margin-top: 1px;
}
.pf-verdict--ok .pf-verdict__glyph { background: var(--ok); }
.pf-verdict--bad .pf-verdict__glyph { background: var(--danger); }
.pf-verdict__glyph svg { width: 12px; height: 12px; }
.pf-verdict__title { display: block; font-weight: 600; color: var(--text); margin-bottom: 2px; }

.pf-score {
  display: flex; align-items: center; gap: var(--s5);
  padding: var(--s5); border: 1px solid var(--border);
  border-radius: var(--r-lg); background: var(--surface);
  box-shadow: var(--shadow-1);
}
.pf-score__value {
  font-size: 30px; font-weight: 680; letter-spacing: -0.026em;
  color: var(--text); font-variant-numeric: tabular-nums; line-height: 1;
}
.pf-score__label { font-size: var(--fs-body); font-weight: 560; color: var(--text); }
.pf-score__meta { font-size: var(--fs-meta); color: var(--text-3); margin-top: 2px; }

/* tabs */
[class*="pf-tabs-"] [data-testid="stRadioGroup"] {
  flex-direction: row; gap: var(--s4); border-bottom: 1px solid var(--border); flex-wrap: wrap;
}
[class*="pf-tabs-"] [data-testid="stRadioOption"] { display: block; }
[class*="pf-tabs-"] [data-testid="stRadioOption"] [role="radio"] {
  background: transparent; border: none; border-bottom: 2px solid transparent;
  border-radius: 0; padding: var(--s2) 1px; margin-bottom: -1px;
  font-size: var(--fs-body); font-weight: 560; color: var(--text-3);
}
[class*="pf-tabs-"] [data-testid="stRadioOption"] [role="radio"]:hover { color: var(--text); }
[class*="pf-tabs-"] [data-testid="stRadioOption"]:has([role="radio"][aria-checked="true"]) [role="radio"] {
  color: var(--accent); border-bottom-color: var(--accent);
}
[class*="pf-tabs-"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
  margin: 0; font: inherit; color: inherit;
}
[data-testid="stTabs"] [role="tablist"] { gap: var(--s4); border-bottom: 1px solid var(--border); }
[data-testid="stTabs"] [role="tab"] {
  font-family: var(--font); font-size: var(--fs-body); font-weight: 560;
  color: var(--text-3); padding: var(--s2) 1px; border-radius: 0;
}
[data-testid="stTabs"] [role="tab"]:hover { color: var(--text); background: transparent; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: var(--accent) !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: var(--accent) !important; }
"""



# ---------------------------------------------------------------------------
# 11. Workspace-specific composition
# ---------------------------------------------------------------------------


def _composition() -> str:
    return """
/* greeting on home: a workspace, not a hero */
.pf-greet { display: flex; align-items: baseline; gap: var(--s3); flex-wrap: wrap; }
.pf-greet__name { font-size: var(--fs-title); font-weight: 650; letter-spacing: -0.02em; }
.pf-greet__ask { font-size: var(--fs-body); color: var(--text-3); }
.pf-quick { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--s2); }
[class*="pf-quick-"] button[data-testid^="stBaseButton"] {
  width: 100%; justify-content: flex-start; background: var(--surface);
  border: 1px solid var(--border); color: var(--text-2);
  font-weight: 520; min-height: 2.5rem; padding: 0 var(--s3);
}
[class*="pf-quick-"] button[data-testid^="stBaseButton"]:hover {
  background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent);
}
.pf-quick svg { width: 15px; height: 15px; }

/* two-zone layout: work + supporting context */
.pf-split { display: grid; grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr); gap: var(--s5); align-items: start; }
.pf-split--even { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.pf-split__main { min-width: 0; }
.pf-split__side { min-width: 0; display: flex; flex-direction: column; gap: var(--s4); }

/* key/value detail lines, e.g. the settings table */
.pf-kv { display: flex; flex-direction: column; }
.pf-kv__row {
  display: flex; justify-content: space-between; gap: var(--s5);
  padding: 7px 0; border-bottom: 1px solid var(--border);
  font-size: var(--fs-body);
}
.pf-kv__row:last-child { border-bottom: none; }
.pf-kv__key { color: var(--text-3); }
.pf-kv__val { color: var(--text); font-weight: 520; text-align: right; word-break: break-word; }

/* plan day list */
.pf-day {
  display: flex; gap: var(--s4); padding: var(--s4) 0;
  border-bottom: 1px solid var(--border);
}
.pf-day:last-child { border-bottom: none; }
.pf-day__num {
  flex: 0 0 34px; height: 34px; border-radius: 9px;
  display: grid; place-items: center; background: var(--surface-2);
  border: 1px solid var(--border); font-size: var(--fs-meta); font-weight: 620;
  color: var(--text-3);
}
.pf-day__title { font-size: var(--fs-body); font-weight: 580; color: var(--text); }
.pf-day__meta { font-size: var(--fs-meta); color: var(--text-3); margin-top: 1px; }
.pf-day__list { margin: var(--s2) 0 0; padding-left: 1.1rem; }
.pf-day__list li { font-size: var(--fs-body); line-height: 1.6; color: var(--text-2); margin-bottom: 2px; }

/* small numeric summary, used sparingly (no dashboards) */
.pf-nums { display: flex; flex-wrap: wrap; gap: var(--s6); }
.pf-num__value {
  font-size: 19px; font-weight: 640; letter-spacing: -0.02em; color: var(--text);
  font-variant-numeric: tabular-nums; line-height: 1.15;
}
.pf-num__label { font-size: var(--fs-meta); color: var(--text-3); margin-top: 1px; }

/* sample / demo material list */
.pf-list { display: flex; flex-direction: column; }
.pf-list__row {
  display: flex; align-items: center; gap: var(--s3);
  padding: var(--s3) 0; border-bottom: 1px solid var(--border);
  font-size: var(--fs-body);
}
.pf-list__row:last-child { border-bottom: none; }
.pf-list__name { color: var(--text); font-weight: 520; }
.pf-list__meta { margin-left: auto; color: var(--text-3); font-size: var(--fs-meta); }
.pf-list__glyph { color: var(--text-4); display: grid; place-items: center; }
.pf-list__glyph svg { width: 15px; height: 15px; }
"""


# ---------------------------------------------------------------------------
# 12. Responsive: 1366, 1280, 1024 and below
# ---------------------------------------------------------------------------


def _responsive() -> str:
    return """
@media (max-width: 1400px) {
  [class*="pf-zone-"] { padding: var(--s4); }
}
@media (max-width: 1240px) {
  /* the zones drop below each other rather than squeezing the conversation.
     The row of zones is an ancestor of the zone keys, not a child, so it is
     matched through :has(). */
  [data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
  [data-testid="stHorizontalBlock"]:has([class*="pf-zone-"]) > [data-testid="stColumn"]
    + [data-testid="stColumn"] {
    border-left: 0;
    border-top: 1px solid var(--border);
  }
  .pf-split, .pf-split--even { grid-template-columns: minmax(0, 1fr); }
  .pf-prompts { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 1080px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: var(--s4) var(--s5) var(--s7) !important; }
  .pf-quick { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: var(--s4) var(--s4) var(--s7) !important; }
  .pf-top { align-items: flex-start; flex-direction: column; gap: var(--s3); }
  .pf-top__actions { width: 100%; }
  .pf-top__actions [data-testid="stButton"] { flex: 1 1 auto; }
  [class*="pf-zone-"] { padding: var(--s4) var(--s3); }
  .pf-nums { gap: var(--s5); }
  .pf-ask__bubble { max-width: 92%; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }
}
"""


# ---------------------------------------------------------------------------
# 13. Mobile: the sidebar steps aside, the pages become cards
# ---------------------------------------------------------------------------


def _mobile() -> str:
    return """
/* The card bar exists on every screen in the DOM and is hidden on all of them
   except a phone, where the sidebar goes away. Hiding it with display:none (and
   not `visibility`) also takes its five buttons out of the tab order. */
[class*="pf-mobnav-"] { display: none; }

@media (max-width: 860px) {
  /* Streamlit's sidebar is a fixed 264px column in this app. On a phone that is
     most of the screen, so it goes entirely, drawer handle included. */
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"],
  [data-testid="stSidebarHeader"],
  [data-testid="stSidebarUserContent"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stExpandSidebarButton"] { display: none !important; }

  /* Room for the bar, so the last row of a page is never hidden underneath it. */
  [data-testid="stMainBlockContainer"], .block-container {
    padding-bottom: calc(var(--mobnav-h) + var(--s6) + env(safe-area-inset-bottom, 0px)) !important;
  }

  /* ── The bar itself ─────────────────────────────────────────────────────── */
  [class*="pf-mobnav-"] {
    display: block;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 90;
    padding: 8px 10px calc(8px + env(safe-area-inset-bottom, 0px));
    background: var(--surface);
    background: color-mix(in srgb, var(--surface) 88%, transparent);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    backdrop-filter: saturate(180%) blur(16px);
    border-top: 1px solid var(--border);
    box-shadow: 0 -10px 30px -18px rgba(15, 21, 40, 0.45);
  }
  [class*="pf-mobnav-"] [data-testid="stVerticalBlock"],
  [class*="pf-mobnav-"] [data-testid="stHorizontalBlock"] { gap: 6px; align-items: stretch; }
  [class*="pf-mobnav-"] [data-testid="stColumn"] { padding: 0; min-width: 0; }
  [class*="pf-mobnav-"] [data-testid="stElementContainer"] { width: 100%; }

  /* ── One card per page ──────────────────────────────────────────────────── */
  [class*="pf-mobitem-"] { display: block; }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"] {
    width: 100%;
    min-height: var(--mobnav-h);
    padding: 8px 2px;
    border-radius: 16px;
    background: var(--surface-2);
    border: 1px solid transparent;
    color: var(--text-3);
    box-shadow: none;
    font-size: 11px;
    font-weight: 580;
    line-height: 1.2;
    justify-content: center;
    transition: background var(--dur-hover) var(--ease-default),
                color var(--dur-hover) var(--ease-default),
                box-shadow var(--dur-hover) var(--ease-default),
                transform var(--dur-hover) var(--ease-default);
  }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"]:hover {
    background: var(--surface-3);
    border-color: var(--border);
    color: var(--text);
    transform: none;
  }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"]:active { transform: scale(0.95); }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton-primary"] {
    background: linear-gradient(180deg, var(--accent-light) 0%, var(--accent) 100%);
    border-color: var(--accent-dark);
    color: #FFFFFF;
    box-shadow: 0 4px 12px -4px rgba(169, 124, 11, 0.45);
  }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton-primary"]:hover {
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
    border-color: var(--accent-dark);
    color: #FFFFFF;
    box-shadow: 0 6px 16px -4px rgba(169, 124, 11, 0.5);
    transform: none;
  }

  /* Icon above label. Streamlit wraps the label in its own div, so that wrapper
     is dropped from the layout and the button itself becomes the flex column. */
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"] > div { display: contents; }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"] {
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"]::before {
    width: 20px;
    height: 20px;
    margin-right: 0;
  }
  [class*="pf-mobitem-"] button[data-testid^="stBaseButton"] p {
    font-size: 11px;
    line-height: 1.2;
    margin: 0;
  }

  /* ── Page head: a phone gets smaller type ────────────────────────────────── */
  .pf-top__title { font-size: 23px; }
  .pf-top__sub { font-size: 13px; }
  .pf-top__meta { margin-top: var(--s2); }

  /* ── Suggestion chips: one per row, and their text may wrap ─────────────── */
  [data-testid="stHorizontalBlock"]:has([class*="pf-prompt-"]) > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
  [class*="pf-prompt-"] button[data-testid^="stBaseButton"] {
    white-space: normal;
    height: auto;
    min-height: 2.6rem;
    padding: 9px var(--s3);
    line-height: 1.45;
  }

  /* The Ask composer sticks to the bottom of the window, so it stops above
     the bar rather than under it. */
  [class*="pf-composer-ask"] {
    bottom: calc(var(--mobnav-h) + 16px + env(safe-area-inset-bottom, 0px));
  }
}
"""


SECTIONS = (
    _tokens,
    _base,
    _chrome,
    _inputs,
    _buttons,
    _dialogs,
    _sidebar,
    _furniture,
    _workspace,
    _rows,
    _conversation,
    _composer,
    _quiz,
    _composition,
    _responsive,
    _mobile,
)


def stylesheet() -> str:
    """The whole system as one stylesheet."""
    return "\n".join(section() for section in SECTIONS)


def favicon() -> str:
    """The brand mark as a data-URI favicon: no file, no network request."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='%23A97C0B' stroke-width='1.9' stroke-linecap='round' "
        f"stroke-linejoin='round'>{_ICON_PATHS['book']}</svg>"
    )
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")


def inject() -> None:
    st.markdown(f"<style>{stylesheet()}</style>", unsafe_allow_html=True)
