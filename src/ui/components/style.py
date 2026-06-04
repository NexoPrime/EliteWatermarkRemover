"""Application stylesheet.

Provides an ultra-premium, studio-grade aesthetic optimized for high-focus
and dopamine-inducing user experience. Dark mode deep-space backgrounds
with vibrant neon-cyan and indigo accents.
"""

from __future__ import annotations

STYLE_SHEET: str = """
/* ===== Base Typography & Colors ===== */
QMainWindow {
    background-color: #0b0d17;
}
QWidget {
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', 'Roboto', Arial, sans-serif;
    font-size: 10pt;
    color: #e0e6ed;
}

/* ===== Buttons (Primary Call to Actions) ===== */
QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #3b82f6);
    color: #ffffff;
    border: none;
    padding: 0.6em 1.2em;
    border-radius: 6px;
    font-weight: bold;
    font-size: 10pt;
}
QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818cf8, stop:1 #60a5fa);
}
QPushButton:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #2563eb);
}
QPushButton:disabled {
    background-color: #1f2937;
    color: #4b5563;
}
QPushButton[class="danger"] {
    background-color: #ef4444;
}
QPushButton[class="danger"]:hover {
    background-color: #f87171;
}

/* ===== Tool Buttons (Toolbar Items) ===== */
QToolButton {
    background-color: #151828;
    color: #94a3b8;
    border: 1px solid #1e293b;
    padding: 0.6em 1.0em;
    border-radius: 6px;
    font-weight: bold;
}
QToolButton:checked {
    background-color: #1e1b4b;
    color: #00e5ff;
    border: 1px solid #3b82f6;
}
QToolButton:hover {
    background-color: #1e293b;
    color: #e0e6ed;
    border: 1px solid #334155;
}
QToolButton:checked:hover {
    background-color: #2e1065;
    border: 1px solid #00e5ff;
}

/* ===== Labels ===== */
QLabel {
    color: #cbd5e1;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #0f111a;
}
QTabBar::tab {
    background-color: #151828;
    color: #64748b;
    padding: 0.6em 1.5em;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    border: 1px solid transparent;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #0f111a;
    color: #00e5ff;
    border-top: 2px solid #00e5ff;
    border-left: 1px solid #1e293b;
    border-right: 1px solid #1e293b;
}
QTabBar::tab:hover:!selected {
    background-color: #1e293b;
    color: #cbd5e1;
}

/* ===== Group Boxes ===== */
QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 1.5em;
    background-color: #12141f;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 1.0em;
    padding: 0 0.5em;
    color: #3b82f6;
    font-weight: bold;
    font-size: 11pt;
}

/* ===== Inputs (SpinBox, LineEdit, ComboBox) ===== */
QComboBox, QSpinBox, QLineEdit {
    background-color: #0b0d17;
    color: #e0e6ed;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 0.5em 0.8em;
    font-weight: 500;
}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border: 1px solid #00e5ff;
    background-color: #0f111a;
}
QComboBox::drop-down {
    border: none;
    padding-right: 0.8em;
}

/* ===== Progress Bar ===== */
QProgressBar {
    border: none;
    border-radius: 6px;
    text-align: center;
    background-color: #1e293b;
    color: #ffffff;
    font-weight: bold;
    height: 18px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #00e5ff);
    border-radius: 6px;
}

/* ===== Graphics View (Image Canvas) ===== */
QGraphicsView {
    border: 1px solid #1e293b;
    background-color: #050608;
    border-radius: 8px;
}

/* ===== Scroll Bars ===== */
QScrollBar:vertical, QScrollBar:horizontal {
    background: #0b0d17;
    border: none;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #475569;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* ===== Check Boxes ===== */
QCheckBox {
    spacing: 0.8em;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 1.2em;
    height: 1.2em;
    border-radius: 4px;
    border: 1px solid #334155;
    background-color: #0b0d17;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border: 1px solid #3b82f6;
}
QCheckBox::indicator:hover {
    border: 1px solid #00e5ff;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background-color: #0b0d17;
    color: #cbd5e1;
    border-bottom: 1px solid #1e293b;
    padding: 0.3em 0px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 0.4em 1.0em;
    border-radius: 4px;
    font-weight: 500;
}
QMenuBar::item:selected {
    background-color: #1e293b;
    color: #ffffff;
}
QMenu {
    background-color: #151828;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 0.4em;
}
QMenu::item {
    padding: 0.6em 2.0em 0.6em 1.2em;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #1e293b;
    margin: 0.4em 0.8em;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #0b0d17;
    color: #64748b;
    border-top: 1px solid #1e293b;
    font-size: 9pt;
    font-weight: 500;
}
QStatusBar::item {
    border: none;
}

/* ===== Tooltips ===== */
QToolTip {
    background-color: #0b0d17;
    color: #00e5ff;
    border: 1px solid #00e5ff;
    border-radius: 4px;
    padding: 0.4em 0.8em;
    font-weight: bold;
}

/* ===== Dialogs & File Explorers ===== */
QDialog, QMessageBox {
    background-color: #0b0d17;
    color: #e0e6ed;
}
QTableView, QTreeView, QListView {
    background-color: #0f111a;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    gridline-color: #1e293b;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #151828;
    color: #94a3b8;
    border: none;
    border-right: 1px solid #1e293b;
    border-bottom: 1px solid #1e293b;
    padding: 0.4em;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background-color: #1e293b;
    width: 2px;
}
QSplitter::handle:hover {
    background-color: #00e5ff;
}
"""
