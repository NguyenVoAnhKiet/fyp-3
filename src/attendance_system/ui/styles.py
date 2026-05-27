from __future__ import annotations

from PyQt5.QtGui import QFont


# Brand / Accent
ACCENT_PRIMARY = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_LIGHT = "#dbeafe"

# Backgrounds
BG_WINDOW = "#f8fafc"
BG_CARD = "#ffffff"
BG_SIDEBAR = "#1e293b"
BG_INPUT = "#f1f5f9"
BG_HOVER = "#f1f5f9"

# Text
TEXT_PRIMARY = "#0f172a"
TEXT_SECONDARY = "#64748b"
TEXT_MUTED = "#94a3b8"
TEXT_ON_DARK = "#f8fafc"
TEXT_ON_DARK_MUTED = "#94a3b8"

# Borders
BORDER = "#e2e8f0"
BORDER_FOCUS = "#2563eb"

# Status colors
STATUS_SUCCESS = "#16a34a"
STATUS_WARNING = "#d97706"
STATUS_ERROR = "#dc2626"
STATUS_INFO = "#2563eb"

# Shadows (QSS doesn't support box-shadow, use these for reference in code)
CARD_SHADOW = "0 2px 8px rgba(0,0,0,0.08)"


def _make_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(size)
    font.setWeight(weight)
    return font


FONT_H1 = _make_font(26, QFont.Weight.Bold)
FONT_H2 = _make_font(20, QFont.Weight.Bold)
FONT_H3 = _make_font(17, QFont.Weight.DemiBold)
FONT_BODY = _make_font(15)
FONT_SMALL = _make_font(13)
FONT_BUTTON = _make_font(15, QFont.Weight.DemiBold)
FONT_TAB = _make_font(13)
FONT_STATS = _make_font(30, QFont.Weight.Bold)


GLOBAL_QSS = """
QWidget {
    font-family: "Segoe UI";
    font-size: 15px;
    color: #0f172a;
    background-color: #f8fafc;
}
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 15px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QLineEdit {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 15px;
    color: #0f172a;
}
QLineEdit:focus {
    border: 2px solid #2563eb;
    background-color: #ffffff;
}
QComboBox {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 15px;
}
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    font-size: 14px;
    text-transform: uppercase;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #f1f5f9;
}
QListWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px;
    padding-top: 24px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QProgressBar {
    background-color: #f1f5f9;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}
QScrollBar:vertical {
    background-color: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
    font-size: 13px;
    color: #64748b;
}
QSplitter::handle {
    background-color: #e2e8f0;
    width: 1px;
}
"""
