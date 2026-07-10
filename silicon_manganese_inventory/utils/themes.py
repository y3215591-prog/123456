THEMES = {
    "sky": {
        "name": "天空蓝",
        "accent": "#007aff",
        "bg": "#f2f5f9",
        "card": "rgba(255,255,255,0.85)",
        "sidebar": "rgba(245,248,252,0.92)",
        "text_primary": "#1d1d1f",
        "text_secondary": "#86868b",
        "table_header": "#007aff",
        "success": "#34c759",
        "warning": "#ff9500",
        "danger": "#ff3b30",
    },
    "ocean": {
        "name": "深海蓝",
        "accent": "#0a84ff",
        "bg": "#e8f0fe",
        "card": "rgba(255,255,255,0.82)",
        "sidebar": "rgba(235,242,252,0.90)",
        "text_primary": "#1c2331",
        "text_secondary": "#5f6b7a",
        "table_header": "#0a84ff",
        "success": "#30d158",
        "warning": "#ff9f0a",
        "danger": "#ff453a",
    },
    "forest": {
        "name": "森林绿",
        "accent": "#30b553",
        "bg": "#eef5ef",
        "card": "rgba(255,255,255,0.84)",
        "sidebar": "rgba(240,248,242,0.90)",
        "text_primary": "#1d2d1d",
        "text_secondary": "#6b7d6b",
        "table_header": "#30b553",
        "success": "#30b553",
        "warning": "#e6a300",
        "danger": "#e74c3c",
    },
    "sunset": {
        "name": "日落橙",
        "accent": "#ff6b35",
        "bg": "#fef6f0",
        "card": "rgba(255,255,255,0.84)",
        "sidebar": "rgba(254,248,244,0.90)",
        "text_primary": "#2d1d1a",
        "text_secondary": "#8b7d74",
        "table_header": "#ff6b35",
        "success": "#34c759",
        "warning": "#ff9500",
        "danger": "#ff3b30",
    },
    "lavender": {
        "name": "薰衣草紫",
        "accent": "#8b5cf6",
        "bg": "#f5f1fe",
        "card": "rgba(255,255,255,0.84)",
        "sidebar": "rgba(248,245,254,0.90)",
        "text_primary": "#2d1d3d",
        "text_secondary": "#8b7d9b",
        "table_header": "#8b5cf6",
        "success": "#34c759",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    },
    "rose": {
        "name": "玫瑰粉",
        "accent": "#f43f5e",
        "bg": "#fff1f3",
        "card": "rgba(255,255,255,0.84)",
        "sidebar": "rgba(255,245,246,0.90)",
        "text_primary": "#2d1d20",
        "text_secondary": "#9b7d80",
        "table_header": "#f43f5e",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#e11d48",
    },
    "mocha": {
        "name": "摩卡棕",
        "accent": "#a67c52",
        "bg": "#f9f5f0",
        "card": "rgba(255,255,255,0.85)",
        "sidebar": "rgba(250,247,243,0.92)",
        "text_primary": "#2d2018",
        "text_secondary": "#8b7060",
        "table_header": "#a67c52",
        "success": "#34c759",
        "warning": "#ff9500",
        "danger": "#e74c3c",
    },
    "mint": {
        "name": "薄荷绿",
        "accent": "#00b894",
        "bg": "#eefaf5",
        "card": "rgba(255,255,255,0.84)",
        "sidebar": "rgba(240,250,246,0.90)",
        "text_primary": "#1d2d25",
        "text_secondary": "#6b7d6f",
        "table_header": "#00b894",
        "success": "#00b894",
        "warning": "#e17055",
        "danger": "#d63031",
    },
    "midnight": {
        "name": "午夜黑",
        "accent": "#6366f1",
        "bg": "#1e1e24",
        "card": "rgba(40,40,50,0.90)",
        "sidebar": "rgba(30,30,40,0.95)",
        "text_primary": "#e4e4e7",
        "text_secondary": "#a1a1aa",
        "table_header": "#6366f1",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    },
    "pearl": {
        "name": "珍珠白",
        "accent": "#94a3b8",
        "bg": "#f8f9fb",
        "card": "rgba(255,255,255,0.88)",
        "sidebar": "rgba(248,249,251,0.94)",
        "text_primary": "#1e293b",
        "text_secondary": "#94a3b8",
        "table_header": "#64748b",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    },
}

DEFAULT_THEME = "sky"

FROSTED_BASE = """
QWidget {{
    background: transparent;
}}

QMainWindow, QDialog {{
    background: {bg};
}}

QTableWidget {{
    background: {card};
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 12px;
    gridline-color: rgba(0,0,0,0.04);
    font-size: 13px;
    color: {text_primary};
}}

QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid rgba(0,0,0,0.03);
}}

QTableWidget::item:selected {{
    background: rgba({accent_r},{accent_g},{accent_b},0.12);
    color: {text_primary};
}}

QHeaderView::section {{
    background: {table_header};
    color: white;
    font-weight: bold;
    padding: 8px;
    border: none;
    border-right: 1px solid rgba(255,255,255,0.15);
}}

QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    border: 1px solid rgba(0,0,0,0.1);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    background: rgba(0,0,0,0.03);
    color: {text_primary};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {accent};
    background: rgba({accent_r},{accent_g},{accent_b},0.04);
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: rgba(255,255,255,0.95);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 8px;
    selection-background-color: rgba({accent_r},{accent_g},{accent_b},0.12);
    color: {text_primary};
}}

QPushButton {{
    border-radius: 8px;
    font-size: 13px;
}}

QLabel {{
    color: {text_primary};
}}
"""

FROSTED_CARD = """
QWidget#card, QWidget#frostedCard {{
    background: {card};
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.3);
}}
"""

NAVBAR_STYLE = """
QFrame#navBar {{
    background: {sidebar};
    border-right: 1px solid rgba(0,0,0,0.06);
    border-radius: 0px;
}}

QPushButton#navBtn {{
    background: transparent;
    border: none;
    border-radius: 10px;
    color: {text_primary};
    font-size: 14px;
    text-align: left;
    padding: 10px 16px;
}}

QPushButton#navBtn:hover {{
    background: rgba({accent_r},{accent_g},{accent_b},0.08);
}}

QPushButton#navBtn[active="true"] {{
    background: rgba({accent_r},{accent_g},{accent_b},0.15);
    color: {accent};
    font-weight: bold;
}}
"""
