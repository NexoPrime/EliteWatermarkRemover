"""Application stylesheet.

Provides an ultra-professional, Adobe/VSCode-style dark theme for the application.
Uses a cross-platform font stack and em-based relative sizing for perfect
proportional scaling on any resolution and DPI.
"""

from __future__ import annotations

STYLE_SHEET: str = """
/* ===== Base ===== */
QMainWindow {
    background-color: #1e1e1e;
    color: #cccccc;
}
QWidget {
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', 'Roboto', Arial, sans-serif;
    font-size: 10pt;
    color: #cccccc;
}

/* ===== Buttons ===== */
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 0.6em 1.2em;
    border-radius: 3px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:pressed {
    background-color: #094771;
}
QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}
QPushButton[class="danger"] {
    background-color: #ac2925;
}
QPushButton[class="danger"]:hover {
    background-color: #c9302c;
}

/* ===== Tool Buttons ===== */
QToolButton {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    padding: 0.5em 1.0em;
    border-radius: 3px;
    font-weight: bold;
}
QToolButton:checked {
    background-color: #0e639c;
    color: #ffffff;
    border: 1px solid #0e639c;
}
QToolButton:hover {
    background-color: #3e3e42;
}
QToolButton:checked:hover {
    background-color: #1177bb;
}

/* ===== Labels ===== */
QLabel {
    color: #cccccc;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #969696;
    padding: 0.5em 1.2em;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
    border: 1px solid transparent;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-top: 2px solid #007fd4;
    border-left: 1px solid #3e3e42;
    border-right: 1px solid #3e3e42;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #3e3e42;
    color: #cccccc;
}

/* ===== Group Boxes ===== */
QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    margin-top: 1.2em;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 0.8em;
    padding: 0 0.4em;
    color: #007fd4;
}

/* ===== Inputs ===== */
QComboBox, QSpinBox, QLineEdit {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 0.5em;
}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border: 1px solid #007fd4;
    background-color: #444444;
}
QComboBox::drop-down {
    border: none;
    padding-right: 0.6em;
}

/* ===== Progress Bar ===== */
QProgressBar {
    border: 1px solid #3e3e42;
    border-radius: 3px;
    text-align: center;
    background-color: #2d2d2d;
    color: #ffffff;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #0e639c;
    border-radius: 2px;
}

/* ===== Graphics View (Image Canvas) ===== */
QGraphicsView {
    border: 1px solid #3e3e42;
    background-color: #111111;
    border-radius: 4px;
}

/* ===== Scroll Bars ===== */
QScrollBar:vertical, QScrollBar:horizontal {
    background: #1e1e1e;
    border: none;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #424242;
    border-radius: 3px;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #4f4f4f;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* ===== Check Boxes ===== */
QCheckBox {
    spacing: 0.6em;
}
QCheckBox::indicator {
    width: 1.2em;
    height: 1.2em;
    border-radius: 3px;
    border: 1px solid #3c3c3c;
    background-color: #3c3c3c;
}
QCheckBox::indicator:checked {
    background-color: #0e639c;
    border: 1px solid #0e639c;
}
QCheckBox::indicator:hover {
    border: 1px solid #007fd4;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background-color: #252526;
    color: #cccccc;
    border-bottom: 1px solid #3e3e42;
    padding: 0.2em 0px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 0.3em 0.9em;
    border-radius: 3px;
}
QMenuBar::item:selected {
    background-color: #3e3e42;
}
QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 0.3em;
}
QMenu::item {
    padding: 0.5em 1.8em 0.5em 0.9em;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #0e639c;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #3e3e42;
    margin: 0.3em 0.6em;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #007fd4;
    color: #ffffff;
    border-top: 1px solid #007fd4;
    font-size: 9pt;
}
QStatusBar::item {
    border: none;
}

/* ===== Tooltips ===== */
QToolTip {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    padding: 0.3em 0.6em;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background-color: #3e3e42;
    width: 2px;
}
QSplitter::handle:hover {
    background-color: #007fd4;
}
"""
