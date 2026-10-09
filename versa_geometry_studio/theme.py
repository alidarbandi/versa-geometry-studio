"""Restrained instrument-console colors and reusable Qt styling."""
DARK = dict(bg="#0b1120", panel="#111b2c", raised="#17243a", border="#263650", text="#e7eef9", muted="#91a3bc", cyan="#52dfd1", amber="#f7ba62", violet="#b99bff", red="#ff7f87", grid="#1c2a40")
LIGHT = dict(bg="#edf2f7", panel="#ffffff", raised="#e4ecf6", border="#ccd8e5", text="#172b45", muted="#546a83", cyan="#007f7b", amber="#ac6500", violet="#7650c2", red="#b83e4b", grid="#dce6ef")


def stylesheet(c):
    return f"""
    QWidget {{ background: {c['bg']}; color: {c['text']}; font-family: 'Segoe UI'; font-size: 12px; }}
    QMainWindow, QDialog {{ background: {c['bg']}; }}
    QFrame#panel {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 10px; }}
    QFrame#card {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 8px; }}
    QLabel {{ background: transparent; border: none; }}
    QLabel#muted {{ color: {c['muted']}; }}
    QLabel#eyebrow {{ color: {c['cyan']}; font-size: 10px; font-weight: 600; letter-spacing: 2px; }}
    QLabel#title {{ font-size: 23px; font-weight: 650; }}
    QLabel#metric {{ font-size: 23px; font-weight: 600; color: {c['cyan']}; }}
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 5px; padding: 6px; min-height: 17px; selection-background-color: {c['cyan']}; }}
    QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {c['cyan']}; }}
    QLineEdit[invalid="true"] {{ border: 1px solid {c['red']}; }}
    QComboBox QAbstractItemView {{ background: {c['raised']}; selection-background-color: {c['border']}; }}
    QPushButton, QToolButton {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 5px; padding: 7px 11px; }}
    QPushButton:hover, QToolButton:hover {{ border-color: {c['cyan']}; }}
    QPushButton#primary {{ background: {c['cyan']}; color: {c['bg']}; font-weight: 650; border: none; }}
    QPushButton:disabled {{ color: {c['muted']}; background: {c['panel']}; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ background: transparent; padding: 9px 10px; color: {c['muted']}; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {c['cyan']}; border-bottom: 2px solid {c['cyan']}; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 7px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 25px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QSlider::groove:horizontal {{ background: {c['border']}; height: 4px; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {c['cyan']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {c['cyan']}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
    QCheckBox {{ background: transparent; spacing: 6px; }}
    QCheckBox::indicator {{ width: 13px; height: 13px; border: 1px solid {c['muted']}; border-radius: 3px; background: {c['raised']}; }}
    QCheckBox::indicator:checked {{ background: {c['cyan']}; border-color: {c['cyan']}; }}
    QMenuBar, QMenu, QStatusBar {{ background: {c['panel']}; }}
    QMenu::item:selected {{ background: {c['raised']}; }}
    QToolTip {{ background: {c['raised']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 5px; }}
    QPlainTextEdit, QTextBrowser, QTableWidget {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 5px; }}
    QHeaderView::section {{ background: {c['raised']}; color: {c['text']}; padding: 6px; border: none; }}
    QSplitter::handle {{ background: transparent; width: 7px; }}
    """
