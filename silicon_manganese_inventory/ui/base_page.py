from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from silicon_manganese_inventory.utils.preferences import UIPreferences
from silicon_manganese_inventory.utils.theme_manager import ThemeManager

_prefs = UIPreferences()
_tm = ThemeManager.instance()


class BasePage(QWidget):
    def __init__(self, db, title="", page_key=None):
        super().__init__()
        self.db = db
        self.title = title
        self.page_key = page_key or title
        self._filter_widgets = []
        self._column_count = 0
        self._restoring = False
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.top_bar = QWidget()
        self.top_bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        title_lbl = QLabel(self.title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1D2939; border: none; background: transparent;")
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()
        self.header_buttons = QHBoxLayout()
        self.header_buttons.setSpacing(8)
        top_layout.addLayout(self.header_buttons)
        self.main_layout.addWidget(self.top_bar)

        self.search_bar = QWidget()
        self.search_bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        self.search_layout = QHBoxLayout(self.search_bar)
        self.search_layout.setContentsMargins(16, 6, 16, 6)
        self.search_layout.setSpacing(8)
        self.main_layout.addWidget(self.search_bar)

        self.table_frame = QWidget()
        self.table_frame.setStyleSheet("background: #FFFFFF;")
        table_layout = QVBoxLayout(self.table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().sectionResized.connect(self._on_header_changed)
        self.table.horizontalHeader().sectionMoved.connect(self._on_header_moved)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)
        self.main_layout.addWidget(self.table_frame, 1)

        self.status_layout = QHBoxLayout()
        self.main_layout.addLayout(self.status_layout)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._save_header_state)

    def add_search_field(self, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 13px; color: #6B7280; border: none; background: transparent;")
        self.search_layout.addWidget(lbl)
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
            QPushButton { background: #2B579A; color: white; border: none;
                          padding: 5px 14px; border-radius: 3px; font-size: 13px; }
            QPushButton:hover { background: #234881; }
        """)
        btn.clicked.connect(callback)
        self.search_layout.addWidget(btn)

    def add_header_button(self, text, callback, color="#2B579A"):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: white; border: none;
                          padding: 5px 14px; border-radius: 3px; font-size: 13px; }}
            QPushButton:hover {{ background: {self._darken(color)}; }}
        """)
        btn.clicked.connect(callback)
        self.header_buttons.addWidget(btn)

    def _darken(self, color):
        if color.startswith("#") and len(color) == 7:
            r = max(0, int(color[1:3], 16) - 20)
            g = max(0, int(color[3:5], 16) - 20)
            b = max(0, int(color[5:7], 16) - 20)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    def set_table_headers(self, headers):
        self._column_count = len(headers)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        saved_state = _prefs.load_header_state(self.page_key)
        if not saved_state.isEmpty():
            self._restoring = True
            self.table.horizontalHeader().restoreState(saved_state)
            self._restoring = False
            return
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._auto_fit_timer = QTimer(self)
        self._auto_fit_timer.setSingleShot(True)
        self._auto_fit_timer.timeout.connect(self._initial_auto_fit_done)
        self._auto_fit_timer.start(200)

    def _initial_auto_fit_done(self):
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._save_header_state()

    def _on_header_changed(self, column, old_width, new_width):
        if self._restoring:
            return
        self._save_timer.start()

    def _on_header_moved(self, logical_index, old_visual, new_visual):
        if self._restoring:
            return
        self._save_timer.start()

    def _save_header_state(self):
        if self._column_count <= 0:
            return
        state = self.table.horizontalHeader().saveState()
        _prefs.save_header_state(self.page_key, state)

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
