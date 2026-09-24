"""
Modern Dark DJ Aesthetic Theme and Qt Stylesheets.
High-contrast neon cyan (Deck A), neon orange (Deck B), and emerald green accents.
"""

# Color Palette Constants
BG_DARK = "#0d0f12"
PANEL_DARK = "#16191f"
PANEL_BORDER = "#252a36"
PANEL_HIGHLIGHT = "#2c3240"

TEXT_PRIMARY = "#f0f4f8"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#586069"

DECK_A_COLOR = "#00e5ff"       # Neon Cyan
DECK_A_HOVER = "#33ebff"
DECK_A_BG = "#06222b"

DECK_B_COLOR = "#ff6d00"       # Neon Orange
DECK_B_HOVER = "#ff8533"
DECK_B_BG = "#2b1406"

ACCENT_GREEN = "#00e676"       # Emerald Play / Active
ACCENT_RED = "#ff1744"         # Cue / Warning
ACCENT_AMBER = "#ffab00"       # Sync / Pause
ACCENT_PURPLE = "#b388ff"      # Auto-DJ

QSS_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-size: 12px;
}}

QGroupBox {{
    background-color: {PANEL_DARK};
    border: 1px solid {PANEL_BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: {TEXT_SECONDARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    background-color: {PANEL_DARK};
}}

QPushButton {{
    background-color: {PANEL_BORDER};
    color: {TEXT_PRIMARY};
    border: 1px solid {PANEL_HIGHLIGHT};
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {PANEL_HIGHLIGHT};
    border-color: #3e4659;
}}

QPushButton:pressed {{
    background-color: #1e222b;
}}

QPushButton:checked {{
    background-color: {ACCENT_GREEN};
    color: #000000;
    border-color: {ACCENT_GREEN};
}}

QLineEdit {{
    background-color: #101217;
    border: 1px solid {PANEL_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    selection-background-color: {DECK_A_COLOR};
    selection-color: #000000;
}}

QLineEdit:focus {{
    border-color: {DECK_A_COLOR};
}}

QComboBox {{
    background-color: {PANEL_DARK};
    border: 1px solid {PANEL_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    color: {TEXT_PRIMARY};
    min-height: 22px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {PANEL_DARK};
    border: 1px solid {PANEL_BORDER};
    color: {TEXT_PRIMARY};
    selection-background-color: {PANEL_HIGHLIGHT};
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #20242e;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {DECK_A_COLOR};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 1px solid #c0c5d0;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {DECK_A_COLOR};
    border-color: #ffffff;
}}

QSlider::groove:vertical {{
    width: 6px;
    background: #20242e;
    border-radius: 3px;
}}

QSlider::add-page:vertical {{
    background: {DECK_A_COLOR};
    border-radius: 3px;
}}

QSlider::handle:vertical {{
    background: #ffffff;
    border: 1px solid #c0c5d0;
    height: 16px;
    margin-left: -5px;
    margin-right: -5px;
    border-radius: 8px;
}}

QSlider::handle:vertical:hover {{
    background: {DECK_A_COLOR};
    border-color: #ffffff;
}}

QTableWidget {{
    background-color: {PANEL_DARK};
    border: 1px solid {PANEL_BORDER};
    gridline-color: #1f232c;
    border-radius: 6px;
    selection-background-color: #242936;
    selection-color: {TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: #12141a;
    color: {TEXT_SECONDARY};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {PANEL_BORDER};
    font-weight: 600;
    font-size: 11px;
}}

QProgressBar {{
    border: 1px solid {PANEL_BORDER};
    border-radius: 4px;
    text-align: center;
    background-color: #101217;
    height: 14px;
    font-size: 10px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}

QProgressBar::chunk {{
    background-color: {DECK_A_COLOR};
    border-radius: 3px;
}}

QScrollBar:vertical {{
    background: {BG_DARK};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {PANEL_HIGHLIGHT};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
