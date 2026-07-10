from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from silicon_manganese_inventory.utils.preferences import UIPreferences


_prefs = UIPreferences()


class BasePage(QWidget):
    def __init__(self, db, title="", page_key=None):
        super().__init__()
        self.db = db
        self.title = title
        self.page_key = page_key or title
        self._filter_widgets = []
        self._column_count = 0
        self._restored = False
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)

        header = QHBoxLayout()
        title_lbl = QLabel(self.title)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title_lbl)
        header.addStretch()
        self.header_buttons = QHBoxLayout()
        header.addLayout(self.header_buttons)
        self.main_layout.addLayout(header)

        self.search_layout = QHBoxLayout()
        self.search_layout.setSpacing(8)
        self.main_layout.addLayout(self.search_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        self.table.setStyleSheet("""
            QTableWidget { gridline-color: #ddd; font-size: 13px; }
            QTableWidget::item { padding: 4px 8px; }
            QHeaderView::section {
                background-color: #3498db; color: white; font-weight: bold;
                padding: 6px; border: none;
            }
        """)
        self.main_layout.addWidget(self.table)

        self.status_layout = QHBoxLayout()
        self.main_layout.addLayout(self.status_layout)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._save_column_widths)

    def add_search_field(self, label, widget):
        self.search_layout.addWidget(QLabel(label))
        self.search_layout.addWidget(widget)
        self._filter_widgets.append(widget)
        field_idx = len(self._filter_widgets) - 1
        saved = _prefs.load_filter(self.page_key, field_idx)
        if saved:
            if isinstance(widget, QComboBox):
                idx = widget.findText(saved)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText(saved)
            elif isinstance(widget, QLineEdit):
                widget.setText(saved)
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(
                lambda val, i=field_idx: _prefs.save_filter(self.page_key, i, val))
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(
                lambda val, i=field_idx: _prefs.save_filter(self.page_key, i, val))

    def add_search_button(self, text, callback):
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border: none;
                          padding: 6px 16px; border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn.clicked.connect(callback)
        self.search_layout.addWidget(btn)

    def add_header_button(self, text, callback, color="#27ae60"):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {color}; color: white; border: none;
                          padding: 6px 16px; border-radius: 4px; font-size: 13px; }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(callback)
        self.header_buttons.addWidget(btn)

    def set_table_headers(self, headers):
        self._column_count = len(headers)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        saved_widths = _prefs.load_column_widths(self.page_key)
        if saved_widths and len(saved_widths) == len(headers):
            self._restoring = True
            for i, w in enumerate(saved_widths):
                if w > 0:
                    self.table.setColumnWidth(i, w)
            self._restoring = False
            self._restored = True
        else:
            self._restoring = False
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeToContents)
            QTimer.singleShot(200, self._initial_auto_fit_done)

    def _initial_auto_fit_done(self):
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._save_column_widths()

    def _on_column_resized(self, column, old_width, new_width):
        if getattr(self, '_restoring', False):
            return
        self._save_timer.start()

    def _save_column_widths(self):
        if self._column_count <= 0:
            return
        widths = [self.table.columnWidth(i) for i in range(self._column_count)]
        _prefs.save_column_widths(self.page_key, widths)

    def populate_table(self, rows, highlight_col=None, highlight_threshold=None):
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                if highlight_col is not None and c == highlight_col:
                    try:
                        if float(val) < highlight_threshold:
                            item.setForeground(Qt.red)
                    except (ValueError, TypeError):
                        pass
                self.table.setItem(r, c, item)

    def show_error(self, msg):
        QMessageBox.warning(self, "错误", msg)

    def show_info(self, msg):
        QMessageBox.information(self, "提示", msg)

    def refresh(self):
        pass
