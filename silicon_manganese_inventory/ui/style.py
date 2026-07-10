STYLE_QSS = """
QMainWindow {
    background-color: #f0f2f5;
}

QStatusBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 12px;
    padding: 2px 8px;
}

QTableWidget {
    gridline-color: #dcdde1;
    font-size: 13px;
    background-color: white;
    alternate-background-color: #f8f9fa;
    selection-background-color: #d5e8d4;
    selection-color: #2c3e50;
    border: 1px solid #dcdde1;
    border-radius: 4px;
}

QTableWidget::item {
    padding: 4px 8px;
}

QHeaderView::section {
    background-color: #34495e;
    color: white;
    font-weight: bold;
    padding: 8px 6px;
    border: none;
    border-right: 1px solid #2c3e50;
}

QPushButton {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 6px 14px;
    background-color: #ecf0f1;
    color: #2c3e50;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #d5dbdb;
}

QPushButton:pressed {
    background-color: #bdc3c7;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 5px 8px;
    background-color: white;
    font-size: 13px;
    color: #2c3e50;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border-color: #3498db;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QDialog {
    background-color: #f8f9fa;
}

QLabel {
    color: #2c3e50;
}

QFormLayout QLabel {
    font-weight: bold;
    min-width: 80px;
}

QScrollBar:vertical {
    background-color: #f0f2f5;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #bdc3c7;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #95a5a6;
}
"""
